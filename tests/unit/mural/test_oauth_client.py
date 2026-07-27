import time

import httpx
import jwt
import pytest

from app import config as app_config
from app.mural.connectivity import exceptions
from app.mural.connectivity import models as schemas
from app.mural.connectivity import oauth_client as oauth_client_module
from tests.fakes import httpx_helpers, in_memory_token_store


def _make_oauth(
    config: app_config.AppConfig,
    responses: list[httpx.Response],
    tokens: in_memory_token_store.InMemoryTokenStore | None = None,
) -> tuple[oauth_client_module.OAuthClient, httpx_helpers.MockTransport]:
    client, transport = httpx_helpers.make_mock_client(responses)
    return (
        oauth_client_module.OAuthClient(
            config=config,
            client=client,
            tokens=tokens or in_memory_token_store.InMemoryTokenStore(),
        ),
        transport,
    )


@pytest.fixture
def oauth(fake_config):
    client, _ = httpx_helpers.make_mock_client([])
    return oauth_client_module.OAuthClient(
        config=fake_config,
        client=client,
        tokens=in_memory_token_store.InMemoryTokenStore(),
    )


def test_redirect_uri_joins_base_url_and_callback_path(oauth):
    assert oauth.redirect_uri == "http://example.com/callback"


def test_redirect_uri_strips_trailing_slash_from_base_url():
    config = app_config.AppConfig.model_construct(
        base_url="http://example.com/",
        mural_config=app_config.MuralConfig.model_construct(callback_path="/callback"),
    )
    client, _ = httpx_helpers.make_mock_client([])
    client_obj = oauth_client_module.OAuthClient(
        config=config,
        client=client,
        tokens=in_memory_token_store.InMemoryTokenStore(),
    )
    assert client_obj.redirect_uri == "http://example.com/callback"


def test_build_authorization_url_includes_state(oauth):
    url = oauth.build_authorization_url("my-state-token")
    assert "state=my-state-token" in url
    assert "client_id=test-client-id" in url
    assert "redirect_uri=http%3A%2F%2Fexample.com%2Fcallback" in url
    assert url.startswith("https://app.mural.co/api/public/v1/authorization/oauth2/")


@pytest.mark.asyncio
async def test_get_valid_token_raises_when_user_has_no_tokens(oauth):
    with pytest.raises(exceptions.MuralTokenError):
        await oauth.get_valid_token("user-123")


@pytest.mark.asyncio
async def test_get_valid_token_returns_access_token_when_jwt_valid(fake_config):
    future_exp = int(time.time()) + 3600
    access_token = jwt.encode(
        {"exp": future_exp}, "test-secret-key-32bytes-padding!", algorithm="HS256"
    )
    token = schemas.MuralToken(access_token=access_token, refresh_token="refresh")
    store = in_memory_token_store.InMemoryTokenStore({"user-123": token})

    client_obj, _ = _make_oauth(fake_config, [], tokens=store)
    result = await client_obj.get_valid_token("user-123")

    assert result == access_token


@pytest.mark.asyncio
async def test_get_valid_token_refreshes_and_stores_when_jwt_expired(fake_config):
    past_exp = int(time.time()) - 3600
    expired_token = jwt.encode(
        {"exp": past_exp}, "test-secret-key-32bytes-padding!", algorithm="HS256"
    )
    new_token_data = {"access_token": "new-jwt", "refresh_token": "refresh-456"}

    old_token = schemas.MuralToken(
        access_token=expired_token, refresh_token="refresh-123"
    )
    store = in_memory_token_store.InMemoryTokenStore({"user-123": old_token})

    client_obj, _ = _make_oauth(
        fake_config,
        [httpx.Response(200, json=new_token_data)],
        tokens=store,
    )

    result = await client_obj.get_valid_token("user-123")

    assert result == "new-jwt"
    stored = await store.get_tokens("user-123")
    assert stored is not None
    assert stored.access_token == "new-jwt"
    assert stored.refresh_token == "refresh-456"


@pytest.mark.asyncio
async def test_exchange_code_raises_on_http_error(fake_config):
    client_obj, _ = _make_oauth(fake_config, [httpx.Response(400)])
    with pytest.raises(httpx.HTTPStatusError):
        await client_obj.exchange_code("bad-code")


@pytest.mark.asyncio
async def test_refresh_reuses_original_token_when_response_lacks_one(fake_config):
    client_obj, _ = _make_oauth(
        fake_config,
        [httpx.Response(200, json={"access_token": "new-access"})],
    )
    token = await client_obj.refresh("original-refresh")
    assert token.access_token == "new-access"
    assert token.refresh_token == "original-refresh"


@pytest.mark.asyncio
async def test_refresh_uses_new_refresh_token_when_response_provides_one(fake_config):
    client_obj, _ = _make_oauth(
        fake_config,
        [
            httpx.Response(
                200, json={"access_token": "new-access", "refresh_token": "new-refresh"}
            )
        ],
    )
    token = await client_obj.refresh("original-refresh")
    assert token.refresh_token == "new-refresh"
