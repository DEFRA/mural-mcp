"""REST-surface identity resolution strategies, selected by REST_AUTH_MODE.

- trusted (default): the portal asserts the caller's email via
  TRUSTED_USER_HEADER.
  Used by the token-management surface (POST/GET/DELETE /tokens), where a
  caller who hasn't minted a PAT yet has nothing else to present. Only safe
  when the surface it guards is reachable solely from the portal's network.
- token: the caller presents one of mural-mcp's own personal access tokens,
  the same way /mcp does.
"""

import abc

import fastapi

from app.auth import principal as principal_module
from app.auth import verifier as verifier_port


class UserResolver(abc.ABC):
    @abc.abstractmethod
    async def resolve(self, request: fastapi.Request) -> principal_module.Principal: ...


class TrustedHeaderUserResolver(UserResolver):
    def __init__(self, header_name: str) -> None:
        self._header_name = header_name

    async def resolve(self, request: fastapi.Request) -> principal_module.Principal:
        # The portal asserts the signed-in user's email, and that email is the
        # user id everywhere in this service -- there is no separate generated
        # id to look up. Normalised so the same person always maps to one id.
        email = (request.headers.get(self._header_name) or "").strip().lower()
        if not email:
            raise fastapi.HTTPException(
                status_code=400,
                detail=f"Missing required {self._header_name} header.",
            )

        return principal_module.Principal(user_id=email, email=email)


class PersonalTokenUserResolver(UserResolver):
    def __init__(self, verifier: verifier_port.TokenVerifier) -> None:
        self._verifier = verifier

    async def resolve(self, request: fastapi.Request) -> principal_module.Principal:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise fastapi.HTTPException(
                status_code=401,
                detail="Missing or invalid Authorization header.",
            )

        token = auth_header.removeprefix("Bearer ").strip()
        verified = await self._verifier.verify(token)
        if verified is None:
            raise fastapi.HTTPException(
                status_code=401, detail="Invalid, expired, or revoked token."
            )

        claims = verified.claims
        return principal_module.Principal(
            user_id=str(claims["sub"]),
            email=claims.get("email"),
            label=claims.get("label"),
            token_id=claims.get("token_id"),
        )
