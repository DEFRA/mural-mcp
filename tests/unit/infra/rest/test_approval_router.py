import asyncio
import datetime

import fastapi.testclient
import pytest

import app.entrypoints.http as main_mod
from app import config as app_config
from app.mural.board.approval import models, ports
from tests.fakes import in_memory_approval_store, in_memory_bearer_service

_KEY = "test-key-abc"
_EMAIL = "user@example.com"
_NOW = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)


@pytest.fixture
def approval_store() -> in_memory_approval_store.InMemoryBoardApprovalStore:
    return in_memory_approval_store.InMemoryBoardApprovalStore()


@pytest.fixture
def bearer_svc() -> in_memory_bearer_service.InMemoryBearerTokenService:
    return in_memory_bearer_service.InMemoryBearerTokenService(tokens={_KEY: _EMAIL})


@pytest.fixture
def client(
    fake_config: app_config.AppConfig,
    approval_store: in_memory_approval_store.InMemoryBoardApprovalStore,
    bearer_svc: in_memory_bearer_service.InMemoryBearerTokenService,
) -> fastapi.testclient.TestClient:
    import collections.abc
    import contextlib

    import dishka
    from dishka.integrations import fastapi as dishka_fastapi

    from app.auth import service as auth_service
    from app.common import tracing

    class OverrideProvider(dishka.Provider):
        scope = dishka.Scope.APP

        @dishka.provide
        def provide_approval_store(self) -> ports.BoardApprovalStore:
            return approval_store

        @dishka.provide
        def provide_bearer_service(self) -> auth_service.BearerTokenService:
            return bearer_svc

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

    with fastapi.testclient.TestClient(app) as c:
        yield c


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_KEY}"}


def test_create_board_approval_returns_201(
    client: fastapi.testclient.TestClient,
) -> None:
    response = client.post(
        "/approvals/boards",
        json={"boardId": "board-abc", "iao": "owner@defra.gov.uk"},
        headers=_auth_headers(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["boardId"] == "board-abc"
    assert body["iao"] == "owner@defra.gov.uk"
    assert body["email"] == _EMAIL
    assert body["status"] == "pending"
    assert body["approved"] is False


def test_create_board_approval_conflict(client: fastapi.testclient.TestClient) -> None:
    client.post(
        "/approvals/boards",
        json={"boardId": "board-abc", "iao": "owner@defra.gov.uk"},
        headers=_auth_headers(),
    )
    response = client.post(
        "/approvals/boards",
        json={"boardId": "board-abc", "iao": "owner@defra.gov.uk"},
        headers=_auth_headers(),
    )
    assert response.status_code == 409


def test_create_board_approval_requires_auth(
    client: fastapi.testclient.TestClient,
) -> None:
    response = client.post(
        "/approvals/boards",
        json={"boardId": "board-abc", "iao": "owner@defra.gov.uk"},
    )
    assert response.status_code == 401


def test_get_board_approval_found(client: fastapi.testclient.TestClient) -> None:
    client.post(
        "/approvals/boards",
        json={"boardId": "board-abc", "iao": "owner@defra.gov.uk"},
        headers=_auth_headers(),
    )
    response = client.get("/approvals/boards/board-abc", headers=_auth_headers())
    assert response.status_code == 200
    assert response.json()["boardId"] == "board-abc"


def test_get_board_approval_not_found(client: fastapi.testclient.TestClient) -> None:
    response = client.get("/approvals/boards/nonexistent", headers=_auth_headers())
    assert response.status_code == 404


def test_get_board_approval_scoped_to_user(
    client: fastapi.testclient.TestClient,
    approval_store: in_memory_approval_store.InMemoryBoardApprovalStore,
) -> None:
    other_approval = models.BoardApproval(
        board_id="board-abc",
        iao="owner@defra.gov.uk",
        email="other@example.com",
        status="pending",
        submitted_at=_NOW,
    )
    asyncio.run(approval_store.create(other_approval))

    response = client.get("/approvals/boards/board-abc", headers=_auth_headers())
    assert response.status_code == 404
