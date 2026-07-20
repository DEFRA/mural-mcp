import pytest

from app.common import http_client
from app.mural.connectivity import oauth_client
from tests.fakes import in_memory_token_store


def _make_client(config) -> oauth_client.OAuthClient:
    return oauth_client.OAuthClient(
        config=config,
        client=http_client.create_async_client(
            tracing_header=config.tracing_header,
            trace_id="test-trace",
        ),
        tokens=in_memory_token_store.InMemoryTokenStore(),
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_exchange_code_via_cassette(vcr, fake_config) -> None:
    """Test exchanging an OAuth code for a token using recorded cassette."""
    client = _make_client(fake_config)
    with vcr.use_cassette("mural_exchange_code.yaml"):
        token = await client.exchange_code("auth_code_123")
        assert (
            token.access_token
            == "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsImlhdCI6MTc3NTk1MDAwMCwiZXhwIjoxNzc1OTUzNjAwfQ.fake_signature"
        )
        assert token.refresh_token == "refresh_token_123"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_refresh_access_token_via_cassette(vcr, fake_config) -> None:
    """Test refreshing an access token using recorded cassette."""
    client = _make_client(fake_config)
    with vcr.use_cassette("mural_refresh_token.yaml"):
        token = await client.refresh("refresh_token_123")
        assert token.access_token.startswith("eyJhbGc")
        assert token.refresh_token == "refresh_token_123"
