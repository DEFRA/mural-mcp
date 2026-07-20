import dishka
from fastmcp.server import auth as fastmcp_auth

from app.auth import service


class BearerTokenVerifier(fastmcp_auth.TokenVerifier):
    def __init__(self, container: dishka.AsyncContainer) -> None:
        super().__init__()
        self._container = container

    async def verify_token(self, token: str) -> fastmcp_auth.AccessToken | None:
        if not token or not token.strip():
            return None

        bearer_svc = await self._container.get(service.BearerTokenService)

        email = await bearer_svc.resolve_email(token)

        if email is None:
            return None

        return fastmcp_auth.AccessToken(
            token=token,
            client_id=email,
            scopes=[],
            claims={"email": email},
        )
