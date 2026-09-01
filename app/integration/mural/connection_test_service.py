import httpx

from app import config as app_config
from app.integration.linking import exceptions, oauth_client


class MuralConnectionTestService:
    def __init__(
        self,
        config: app_config.AppConfig,
        client: httpx.AsyncClient,
        oauth: oauth_client.OAuthClient,
    ) -> None:
        self._config = config
        self._client = client
        self._oauth = oauth

    async def test_connection(self, user_id: str) -> None:
        """Test the user's Mural connection by calling GET /users/me.

        Raises exceptions.MuralTokenError if the user is not linked or the
        stored token cannot be refreshed.

        Raises exceptions.MuralApiError if Mural returns a non-2xx response
        (e.g. the token is revoked or expired).

        Raises exceptions.MuralUnavailableError if no response is received at
        all (e.g. Mural is unreachable or the request times out).
        """
        access_token = await self._oauth.get_valid_token(user_id)

        api_base = self._config.mural_config.api_base.rstrip("/")

        try:
            response = await self._client.get(
                f"{api_base}/public/v1/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        except httpx.RequestError as exc:
            raise exceptions.MuralUnavailableError(str(exc)) from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise exceptions.MuralApiError(response.status_code) from exc
