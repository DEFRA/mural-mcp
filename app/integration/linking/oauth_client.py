import datetime
import urllib.parse

import httpx

from app import config as app_config
from app.integration.linking import exceptions, models, ports

_LEEWAY = datetime.timedelta(seconds=60)


class OAuthClient:
    """Handles Mural's OAuth code-exchange and refresh flows.

    Access tokens are treated as opaque bearer strings and never decoded or
    signature-checked here. That's deliberate, not a gap: Mural publishes no
    JWKS, introspection, or revocation endpoint, so a client has no way to
    verify a token's signature even if it wanted to. Trust instead comes from
    how the token was obtained -- TLS to ``mural_config.api_base`` plus
    ``client_secret`` authentication at the token endpoint -- and Mural's API
    is the only authority on a token's continued validity, surfaced as a 401
    on the next real call (see ``exceptions.MuralApiError``). Expiry is read
    from the token response's ``expires_in`` field, not from the token itself.
    """

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
            self._config.mural_config.callback_path
        )

    @property
    def _token_url(self) -> str:
        base = str(self._config.mural_config.api_base).rstrip("/")
        return base + self._config.mural_config.token_path  # noqa: S105

    def build_authorization_url(self, state: str) -> str:
        base = str(self._config.mural_config.api_base).rstrip("/")
        auth_url = base + self._config.mural_config.authorize_path
        params = urllib.parse.urlencode(
            {
                "client_id": self._config.mural_config.client_id,
                "redirect_uri": self.redirect_uri,
                "response_type": "code",
                "state": state,
                "scope": self._config.mural_config.scopes,
            }
        )
        return f"{auth_url}?{params}"

    def _to_token(self, data: dict, fallback_refresh_token: str) -> models.MuralToken:  # type: ignore[type-arg]
        expires_in = data.get("expires_in")
        expires_at = (
            datetime.datetime.now(datetime.UTC) + datetime.timedelta(seconds=expires_in)
            if expires_in is not None
            else None
        )
        return models.MuralToken(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", fallback_refresh_token),
            expires_at=expires_at,
        )

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

        return self._to_token(response.json(), fallback_refresh_token="")

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

        return self._to_token(
            response.json(), fallback_refresh_token=refresh_token_value
        )

    async def get_valid_token(self, user_id: str) -> str:
        token = await self._tokens.get_tokens(user_id)

        if token is None:
            msg = f"No Mural token for user {user_id}"
            raise exceptions.MuralTokenError(msg)

        is_expired = (
            token.expires_at is not None
            and token.expires_at <= datetime.datetime.now(datetime.UTC) + _LEEWAY
        )
        if is_expired:
            token = await self.refresh(token.refresh_token)
            await self._tokens.store_tokens(user_id, token)

        return token.access_token
