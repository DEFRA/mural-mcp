import datetime

import httpx
import pytest

from app import config as app_config
from app.integration.linking import exceptions
from app.integration.linking import models as schemas
from app.integration.linking import oauth_client as oauth_client_module
from tests.fakes import httpx_helpers, in_memory_token_store


def _make_oauth(
    config: app_config.AppConfig,
    responses: list[httpx.Response | Exception],
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


class TestRedirectUri:
    def test_joins_base_url_and_callback_path(self, oauth):
        assert oauth.redirect_uri == "/callback"

    def test_strips_trailing_slash_from_base_url(self):
        config = app_config.AppConfig.model_construct(
            base_url="http://example.com/",
            mural_config=app_config.MuralConfig.model_construct(
                callback_path="/callback"
            ),
        )
        client, _ = httpx_helpers.make_mock_client([])
        client_obj = oauth_client_module.OAuthClient(
            config=config,
            client=client,
            tokens=in_memory_token_store.InMemoryTokenStore(),
        )
        assert client_obj.redirect_uri == "/callback"


class TestBuildAuthorizationUrl:
    def test_includes_state(self, oauth):
        url = oauth.build_authorization_url("my-state-token")

        assert "state=my-state-token" in url
        assert "client_id=test-client-id" in url
        assert "redirect_uri=%2Fcallback" in url
        assert url.startswith(
            "https://app.mural.co/api/public/v1/authorization/oauth2/"
        )


class TestGetValidToken:
    async def test_raises_when_user_has_no_tokens(self, oauth):
        with pytest.raises(exceptions.MuralTokenError):
            await oauth.get_valid_token("user-123")

    async def test_returns_access_token_when_not_expired(self, fake_config):
        future_exp = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)
        token = schemas.MuralToken(
            access_token="example-access-token",
            refresh_token="example-refresh-token",
            expires_at=future_exp,
        )
        store = in_memory_token_store.InMemoryTokenStore({"user-123": token})

        client_obj, _ = _make_oauth(fake_config, [], tokens=store)
        result = await client_obj.get_valid_token("user-123")

        assert result == "example-access-token"

    async def test_returns_access_token_when_expiry_unknown(self, fake_config):
        token = schemas.MuralToken(
            access_token="example-access-token",
            refresh_token="example-refresh-token",
            expires_at=None,
        )
        store = in_memory_token_store.InMemoryTokenStore({"user-123": token})

        client_obj, _ = _make_oauth(fake_config, [], tokens=store)
        result = await client_obj.get_valid_token("user-123")

        assert result == "example-access-token"

    async def test_refreshes_and_stores_when_expired(self, fake_config):
        past_exp = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
        new_token_data = {
            "access_token": "example-new-access-token",
            "refresh_token": "example-new-refresh-token",
        }

        old_token = schemas.MuralToken(
            access_token="example-access-token",
            refresh_token="example-refresh-token",
            expires_at=past_exp,
        )
        store = in_memory_token_store.InMemoryTokenStore({"user-123": old_token})

        client_obj, _ = _make_oauth(
            fake_config,
            [httpx.Response(200, json=new_token_data)],
            tokens=store,
        )

        result = await client_obj.get_valid_token("user-123")

        assert result == "example-new-access-token"

        stored = await store.get_tokens("user-123")

        assert stored is not None
        assert stored.access_token == "example-new-access-token"
        assert stored.refresh_token == "example-new-refresh-token"


class TestExchangeCode:
    async def test_raises_mural_api_error_on_http_error(self, fake_config):
        client_obj, _ = _make_oauth(fake_config, [httpx.Response(400)])

        with pytest.raises(exceptions.MuralApiError) as exc_info:
            await client_obj.exchange_code("bad-code")

        assert exc_info.value.status_code == 400

    async def test_raises_mural_unavailable_error_when_unreachable(self, fake_config):
        client_obj, _ = _make_oauth(
            fake_config, [httpx.ConnectError("Connection refused")]
        )

        with pytest.raises(exceptions.MuralUnavailableError):
            await client_obj.exchange_code("bad-code")


class TestRefresh:
    async def test_reuses_original_token_when_response_lacks_one(self, fake_config):
        client_obj, _ = _make_oauth(
            fake_config,
            [httpx.Response(200, json={"access_token": "new-access"})],
        )
        token = await client_obj.refresh("original-refresh")
        assert token.access_token == "new-access"
        assert token.refresh_token == "original-refresh"

    async def test_uses_new_refresh_token_when_response_provides_one(self, fake_config):
        client_obj, _ = _make_oauth(
            fake_config,
            [
                httpx.Response(
                    200,
                    json={"access_token": "new-access", "refresh_token": "new-refresh"},
                )
            ],
        )
        token = await client_obj.refresh("original-refresh")
        assert token.refresh_token == "new-refresh"

    async def test_raises_mural_api_error_on_http_error(self, fake_config):
        client_obj, _ = _make_oauth(fake_config, [httpx.Response(401)])
        with pytest.raises(exceptions.MuralApiError) as exc_info:
            await client_obj.refresh("original-refresh")
        assert exc_info.value.status_code == 401

    async def test_raises_mural_unavailable_error_when_unreachable(self, fake_config):
        client_obj, _ = _make_oauth(
            fake_config, [httpx.ConnectError("Connection refused")]
        )
        with pytest.raises(exceptions.MuralUnavailableError):
            await client_obj.refresh("original-refresh")
