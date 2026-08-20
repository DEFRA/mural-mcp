import unittest.mock

import fastapi.testclient
import pytest

import app.entrypoints.http as main_mod
from app import config as app_config
from app.auth import principal as principal_module
from app.infra.rest.auth import dependencies as auth_deps
from app.integration.linking import models as linking_models
from app.integration.linking import service as linking_service_module
from tests.fakes import in_memory_oauth_state_store, in_memory_token_store

_USER_TOKEN = "mmcp_user-token"  # noqa: S105
_USER_ID = "usr_test"


async def _override_get_principal(
    request: fastapi.Request,
) -> principal_module.Principal:
    if request.headers.get("Authorization") != f"Bearer {_USER_TOKEN}":
        raise fastapi.HTTPException(status_code=401, detail="Invalid or missing token.")
    return principal_module.Principal(user_id=_USER_ID)


@pytest.fixture
def tokens() -> in_memory_token_store.InMemoryTokenStore:
    return in_memory_token_store.InMemoryTokenStore()


@pytest.fixture
def states() -> in_memory_oauth_state_store.InMemoryOAuthStateStore:
    return in_memory_oauth_state_store.InMemoryOAuthStateStore()


@pytest.fixture
def oauth() -> unittest.mock.AsyncMock:
    import datetime

    mock = unittest.mock.AsyncMock()
    mock.exchange_code.return_value = linking_models.MuralToken(
        access_token="a",
        refresh_token="b",
        expires_at=datetime.datetime(2025, 12, 31, 23, 59, 59, tzinfo=datetime.UTC),
    )
    return mock


@pytest.fixture
def linking(
    oauth: unittest.mock.AsyncMock,
    tokens: in_memory_token_store.InMemoryTokenStore,
    states: in_memory_oauth_state_store.InMemoryOAuthStateStore,
) -> linking_service_module.LinkingService:
    return linking_service_module.LinkingService(
        oauth=oauth, tokens=tokens, states=states
    )


@pytest.fixture
def client(
    fake_config: app_config.AppConfig,
    linking: linking_service_module.LinkingService,
) -> fastapi.testclient.TestClient:
    import collections.abc
    import contextlib

    import dishka
    from dishka.integrations import fastapi as dishka_fastapi

    from app.common import tracing

    class OverrideProvider(dishka.Provider):
        scope = dishka.Scope.APP

        @dishka.provide
        def provide_linking_service(self) -> linking_service_module.LinkingService:
            return linking

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
    app.include_router(main_mod.mural_connect_router.router, prefix="/connect")
    app.dependency_overrides[auth_deps.get_principal] = _override_get_principal

    with fastapi.testclient.TestClient(app) as c:
        yield c


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_USER_TOKEN}"}


@pytest.mark.asyncio
async def test_mural_callback_success(
    client: fastapi.testclient.TestClient,
    states: in_memory_oauth_state_store.InMemoryOAuthStateStore,
    tokens: in_memory_token_store.InMemoryTokenStore,
) -> None:
    state = await states.issue(_USER_ID)

    response = client.get(
        "/connect/mural/callback",
        params={"code": "auth-code", "state": state},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {"status": "connected"}
    assert await tokens.get_tokens(_USER_ID) is not None


def test_mural_callback_unknown_state_returns_400(
    client: fastapi.testclient.TestClient,
) -> None:
    response = client.get(
        "/connect/mural/callback",
        params={"code": "auth-code", "state": "not-a-real-state"},
        headers=_auth_headers(),
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_mural_callback_state_for_different_user_returns_403(
    client: fastapi.testclient.TestClient,
    states: in_memory_oauth_state_store.InMemoryOAuthStateStore,
) -> None:
    state = await states.issue("someone-else")

    response = client.get(
        "/connect/mural/callback",
        params={"code": "auth-code", "state": state},
        headers=_auth_headers(),
    )

    assert response.status_code == 403


def test_mural_status_not_connected(
    client: fastapi.testclient.TestClient,
) -> None:
    response = client.get(
        "/connect/mural/status",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    assert response.json() == {"connected": False, "access_token_expires_at": None}


@pytest.mark.asyncio
async def test_mural_status_connected(
    client: fastapi.testclient.TestClient,
    states: in_memory_oauth_state_store.InMemoryOAuthStateStore,
) -> None:
    state = await states.issue(_USER_ID)

    # Connect the user first
    response = client.get(
        "/connect/mural/callback",
        params={"code": "auth-code", "state": state},
        headers=_auth_headers(),
    )
    assert response.status_code == 200

    # Check the status
    response = client.get(
        "/connect/mural/status",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is True
    assert data["access_token_expires_at"] is not None
