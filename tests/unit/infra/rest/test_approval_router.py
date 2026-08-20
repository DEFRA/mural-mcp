import asyncio
import datetime

import fastapi.testclient
import pytest

import app.entrypoints.http as main_mod
from app import config as app_config
from app.auth import principal as principal_module
from app.infra.rest.auth import dependencies as auth_deps
from app.integration.mural import access_request_service, models, ports
from tests.fakes import in_memory_board_access_request_store

_TOKEN = "mmcp_test-token"  # noqa: S105 -- test fixture, not a real secret
_USER_ID = "usr_test"


async def _override_get_principal(
    request: fastapi.Request,
) -> principal_module.Principal:
    """Stands in for the real get_principal: same pass/fail behaviour on the
    Authorization header, without wiring a full UserResolver/TokenVerifier
    chain through Dishka for a test that isn't about auth resolution itself.
    """
    if request.headers.get("Authorization") != f"Bearer {_TOKEN}":
        raise fastapi.HTTPException(status_code=401, detail="Invalid or missing token.")
    return principal_module.Principal(user_id=_USER_ID)


@pytest.fixture
def store() -> in_memory_board_access_request_store.InMemoryBoardAccessRequestStore:
    return in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()


@pytest.fixture
def client(
    fake_config: app_config.AppConfig,
    store: in_memory_board_access_request_store.InMemoryBoardAccessRequestStore,
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
            self, s: ports.BoardAccessRequestStore
        ) -> access_request_service.BoardAccessRequestService:
            return access_request_service.BoardAccessRequestService(s)

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
    app.include_router(main_mod.mural_approval_router.router, prefix="/approvals")
    app.dependency_overrides[auth_deps.get_principal] = _override_get_principal

    with fastapi.testclient.TestClient(app) as c:
        yield c


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_TOKEN}"}


def test_request_board_access_returns_201(
    client: fastapi.testclient.TestClient,
) -> None:
    response = client.post(
        "/approvals/boards",
        json={"boardId": "board-abc", "iao": "owner@defra.gov.uk", "reason": "need it"},
        headers=_auth_headers(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["boardId"] == "board-abc"
    assert body["iao"] == "owner@defra.gov.uk"
    assert body["reason"] == "need it"
    assert body["userId"] == _USER_ID
    assert body["status"] == "pending"
    assert body["approved"] is False


def test_request_board_access_conflict_when_already_open(
    client: fastapi.testclient.TestClient,
) -> None:
    payload = {"boardId": "board-abc", "iao": "owner@defra.gov.uk", "reason": "need it"}
    client.post("/approvals/boards", json=payload, headers=_auth_headers())
    response = client.post("/approvals/boards", json=payload, headers=_auth_headers())
    assert response.status_code == 409


def test_request_board_access_requires_auth(
    client: fastapi.testclient.TestClient,
) -> None:
    response = client.post(
        "/approvals/boards",
        json={"boardId": "board-abc", "iao": "owner@defra.gov.uk", "reason": "need it"},
    )
    assert response.status_code == 401


def test_get_board_access_request_found(client: fastapi.testclient.TestClient) -> None:
    client.post(
        "/approvals/boards",
        json={"boardId": "board-abc", "iao": "owner@defra.gov.uk", "reason": "need it"},
        headers=_auth_headers(),
    )
    response = client.get("/approvals/boards/board-abc", headers=_auth_headers())
    assert response.status_code == 200
    assert response.json()["boardId"] == "board-abc"


def test_get_board_access_request_not_found(
    client: fastapi.testclient.TestClient,
) -> None:
    response = client.get("/approvals/boards/nonexistent", headers=_auth_headers())
    assert response.status_code == 404


def test_get_board_access_request_scoped_to_user(
    client: fastapi.testclient.TestClient,
    store: in_memory_board_access_request_store.InMemoryBoardAccessRequestStore,
) -> None:
    other_request = models.BoardAccessRequest(
        id="req-other",
        user_id="usr_other",
        board_id="board-abc",
        reason="need it",
        iao="owner@defra.gov.uk",
        created_at=datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC),
    )
    asyncio.run(store.create(other_request))

    response = client.get("/approvals/boards/board-abc", headers=_auth_headers())
    assert response.status_code == 404
