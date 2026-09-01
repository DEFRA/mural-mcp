import httpx
import pytest

from app.integration.linking import exceptions
from app.integration.mural import connection_test_service
from tests.fakes import fake_oauth_client, httpx_helpers


@pytest.fixture
def make_service(fake_config):
    """Build a MuralConnectionTestService with fakes and a real httpx client over MockTransport."""

    def _factory(
        *,
        responses: list[httpx.Response | Exception],
        oauth_token: str | None = "valid-token",
    ) -> tuple[
        connection_test_service.MuralConnectionTestService, httpx_helpers.MockTransport
    ]:
        client, transport = httpx_helpers.make_mock_client(responses)
        oauth = fake_oauth_client.FakeOAuthClient(oauth_token)
        service = connection_test_service.MuralConnectionTestService(
            config=fake_config,
            client=client,
            oauth=oauth,
        )
        return service, transport

    return _factory


class TestTestConnection:
    async def test_succeeds_on_200_response(self, make_service):
        """A 200 response from Mural's /users/me endpoint means the token works."""
        service, transport = make_service(
            responses=[httpx.Response(200, json={"value": {"id": "u123"}})]
        )
        # Should not raise.
        await service.test_connection("user-123")

        assert len(transport.requests) == 1
        assert transport.requests[0].method == "GET"
        assert str(transport.requests[0].url).endswith("/public/v1/users/me")

    async def test_carries_bearer_token(self, make_service):
        """The access token must be sent in the Authorization header."""
        service, transport = make_service(
            responses=[httpx.Response(200)],
            oauth_token="test-token-xyz",
        )
        await service.test_connection("user-123")

        assert transport.requests[0].headers["Authorization"] == "Bearer test-token-xyz"

    async def test_wraps_non_2xx_response_in_mural_api_error(self, make_service):
        """A non-2xx from Mural's /users/me must be wrapped in MuralApiError."""
        service, _ = make_service(responses=[httpx.Response(401)])
        with pytest.raises(exceptions.MuralApiError) as exc_info:
            await service.test_connection("user-123")
        assert exc_info.value.status_code == 401

    async def test_wraps_500_error(self, make_service):
        """Server error from Mural should also be wrapped in MuralApiError."""
        service, _ = make_service(responses=[httpx.Response(500)])
        with pytest.raises(exceptions.MuralApiError) as exc_info:
            await service.test_connection("user-123")
        assert exc_info.value.status_code == 500

    async def test_raises_mural_unavailable_error_when_unreachable(self, make_service):
        """A connection failure (Mural down, DNS failure, timeout) must be
        wrapped in MuralUnavailableError, not left as a raw httpx error."""
        service, _ = make_service(responses=[httpx.ConnectError("Connection refused")])
        with pytest.raises(exceptions.MuralUnavailableError):
            await service.test_connection("user-123")

    async def test_raises_token_error_when_no_token(self, make_service):
        """If the user is not linked, get_valid_token raises MuralTokenError."""
        service, transport = make_service(responses=[], oauth_token=None)
        with pytest.raises(exceptions.MuralTokenError):
            await service.test_connection("user-123")

        # No HTTP request should be made if the token lookup fails.
        assert len(transport.requests) == 0

    async def test_no_response_body_required(self, make_service):
        """The test only cares that the call succeeds, not about the response body."""
        service, _ = make_service(responses=[httpx.Response(200, json=None)])
        # Should not raise, even though the body is empty/null.
        await service.test_connection("user-123")
