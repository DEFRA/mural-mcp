import datetime
import urllib.parse

import httpx
import jwt

from app import config as app_config
from app.mural.connectivity import exceptions, models, ports


class OAuthClient:
    """Handles Mural's OAuth code-exchange and refresh flows."""

    _SCOPES = "murals:read identity:read"

    def __init__(
        self,
        config: app_config.AppConfig,
        client: httpx.AsyncClient,
        tokens: ports.TokenStore,
    ) -> None:
        self._config = config
        self._client = client
        self._tokens = tokens

    @property
    def redirect_uri(self) -> str:
        return (
            str(self._config.base_url).rstrip("/")
            + self._config.mural_config.callback_path
        )

    @property
    def _token_url(self) -> str:
        return (
            str(self._config.mural_config.api_base).rstrip("/")
            + "/public/v1/authorization/oauth2/token"
        )  # noqa: S105

    def build_authorization_url(self, state: str) -> str:
        base = str(self._config.mural_config.api_base).rstrip("/")
        auth_url = f"{base}/public/v1/authorization/oauth2/"
        params = urllib.parse.urlencode(
            {
                "client_id": self._config.mural_config.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "state": state,
                "scope": self._SCOPES,
            }
        )
        return f"{auth_url}?{params}"

    async def exchange_code(self, code: str) -> models.MuralToken:
        mural_config = self._config.mural_config

        response = await self._client.post(
            self._token_url,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri,
                "client_id": mural_config.client_id,
                "client_secret": mural_config.client_secret.get_secret_value(),
            },
        )
        response.raise_for_status()
        data = response.json()

        return models.MuralToken(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
        )

    async def refresh(self, refresh_token_value: str) -> models.MuralToken:
        mural_config = self._config.mural_config

        response = await self._client.post(
            self._token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token_value,
                "client_id": mural_config.client_id,
                "client_secret": mural_config.client_secret.get_secret_value(),
            },
        )
        response.raise_for_status()
        data = response.json()

        return models.MuralToken(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", refresh_token_value),
        )

    async def get_valid_token(self, user_id: str) -> str:
        token = await self._tokens.get_tokens(user_id)

        if token is None:
            msg = f"No Mural token for user {user_id}"
            raise exceptions.MuralTokenError(msg)

        try:
            jwt.decode(
                token.access_token,
                options={"verify_signature": False, "verify_exp": True},
                algorithms=["RS256"],
                leeway=datetime.timedelta(seconds=60),
            )
        except jwt.ExpiredSignatureError:
            token = await self.refresh(token.refresh_token)
            await self._tokens.store_tokens(user_id, token)

        return token.access_token
