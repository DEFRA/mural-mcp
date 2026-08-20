import fastapi.testclient
import pytest

import app.entrypoints.http as main_mod
from app import config as app_config
from app.auth import principal as principal_module
from app.infra.rest.auth import dependencies as auth_deps
from app.integration.mural import access_request_service, ports
from tests.fakes import in_memory_board_access_request_store

_REVIEWER_TOKEN = "mmcp_reviewer-token"  # noqa: S105
_REVIEWER_ID = "usr_reviewer"


async def _override_get_principal(
    request: fastapi.Request,
) -> principal_module.Principal:
    if request.headers.get("Authorization") != f"Bearer {_REVIEWER_TOKEN}":
        raise fastapi.HTTPException(status_code=401, detail="Invalid or missing token.")
    return principal_module.Principal(user_id=_REVIEWER_ID)


@pytest.fixture
def store() -> in_memory_board_access_request_store.InMemoryBoardAccessRequestStore:
    return in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()


@pytest.fixture
def service(
    store: in_memory_board_access_request_store.InMemoryBoardAccessRequestStore,
) -> access_request_service.BoardAccessRequestService:
    return access_request_service.BoardAccessRequestService(store)


@pytest.fixture
def client(
    fake_config: app_config.AppConfig,
    store: in_memory_board_access_request_store.InMemoryBoardAccessRequestStore,
    service: access_request_service.BoardAccessRequestService,
) -> fastapi.testclient.TestClient:
    import collections.abc
    import contextlib

    import dishka
    from dishka.integrations import fastapi as dishka_fastapi

    from app.common import tracing

    class OverrideProvider(dishka.Provider):
        scope = dishka.Scope.APP

        @dishka.provide
        def provide_access_request_store(self) -> ports.BoardAccessRequestStore:
            return store

        @dishka.provide
        def provide_access_request_service(
            self,
        ) -> access_request_service.BoardAccessRequestService:
            return service

        @dishka.provide
        def provide_config(self) -> app_config.AppConfig:
            return fake_config

    container = dishka.make_async_container(
        OverrideProvider(), dishka_fastapi.FastapiProvider()
    )

    @contextlib.asynccontextmanager
    async def lifespan(_app: fastapi.FastAPI) -> collections.abc.AsyncGenerator[None]:
        async with container:
            _app.state.dishka_container = container
            yield

    app = fastapi.FastAPI(lifespan=lifespan)
    app.add_middleware(tracing.ContainerMiddleware)
    app.add_middleware(tracing.TraceIdMiddleware, cfg=fake_config)
    app.include_router(main_mod.admin_router.router, prefix="/admin")
    app.dependency_overrides[auth_deps.get_principal] = _override_get_principal

    with fastapi.testclient.TestClient(app) as c:
        yield c


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_REVIEWER_TOKEN}"}


@pytest.mark.asyncio
async def test_list_pending_access_requests(
    client: fastapi.testclient.TestClient,
    service: access_request_service.BoardAccessRequestService,
) -> None:
    await service.request_access("usr_a", "board-1", "owner@x.com", "why")

    response = client.get("/admin/access-requests", headers=_auth_headers())

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["boardId"] == "board-1"


def test_list_pending_access_requests_requires_auth(
    client: fastapi.testclient.TestClient,
) -> None:
    response = client.get("/admin/access-requests")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_approve_access_request(
    client: fastapi.testclient.TestClient,
    service: access_request_service.BoardAccessRequestService,
) -> None:
    request = await service.request_access("usr_a", "board-1", "owner@x.com", "why")

    response = client.post(
        f"/admin/access-requests/{request.id}/approve",
        json={
            "decisionReason": "looks good",
            "dataHandlingFormRef": "form-1",
            "riskAssessmentRef": "risk-1",
        },
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "approved"
    assert body["approved"] is True
    assert body["reviewerId"] == _REVIEWER_ID
    assert body["decisionReason"] == "looks good"


def test_approve_unknown_access_request_returns_404(
    client: fastapi.testclient.TestClient,
) -> None:
    response = client.post(
        "/admin/access-requests/nonexistent/approve",
        json={
            "decisionReason": "ok",
            "dataHandlingFormRef": "form-1",
            "riskAssessmentRef": "risk-1",
        },
        headers=_auth_headers(),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_approve_an_already_decided_request_returns_409(
    client: fastapi.testclient.TestClient,
    service: access_request_service.BoardAccessRequestService,
) -> None:
    request = await service.request_access("usr_a", "board-1", "owner@x.com", "why")
    await service.approve(request.id, _REVIEWER_ID, "ok", "form-1", "risk-1")

    response = client.post(
        f"/admin/access-requests/{request.id}/approve",
        json={
            "decisionReason": "ok again",
            "dataHandlingFormRef": "form-1",
            "riskAssessmentRef": "risk-1",
        },
        headers=_auth_headers(),
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_reject_access_request(
    client: fastapi.testclient.TestClient,
    service: access_request_service.BoardAccessRequestService,
) -> None:
    request = await service.request_access("usr_a", "board-1", "owner@x.com", "why")

    response = client.post(
        f"/admin/access-requests/{request.id}/reject",
        json={"decisionReason": "not justified"},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "rejected"
    assert body["approved"] is False
    assert body["decisionReason"] == "not justified"


def test_reject_unknown_access_request_returns_404(
    client: fastapi.testclient.TestClient,
) -> None:
    response = client.post(
        "/admin/access-requests/nonexistent/reject",
        json={"decisionReason": "no"},
        headers=_auth_headers(),
    )
    assert response.status_code == 404
