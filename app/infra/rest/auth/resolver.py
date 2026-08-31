"""REST-surface identity resolution strategies, selected by REST_AUTH_MODE.

- trusted (default): the portal asserts the caller via TRUSTED_USER_HEADER.
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
from app.identity import service as identity_service


class UserResolver(abc.ABC):
    @abc.abstractmethod
    async def resolve(self, request: fastapi.Request) -> principal_module.Principal: ...


class TrustedHeaderUserResolver(UserResolver):
    def __init__(
        self, header_name: str, identity: identity_service.IdentityService
    ) -> None:
        self._header_name = header_name
        self._identity = identity

    async def resolve(self, request: fastapi.Request) -> principal_module.Principal:
        # external_id is expected to be the portal-asserted user email — the
        # portal has no MCP-minted user_id to send at this point (that id is
        # only minted once a PAT exists), so it asserts the caller's email
        # instead. resolve_or_create mints the stable user_id the first time
        # this email is seen and looks it up on every call after that, so by
        # the time a router reads principal.user_id it is already resolved.
        external_id = request.headers.get(self._header_name)
        if not external_id:
            raise fastapi.HTTPException(
                status_code=400,
                detail=f"Missing required {self._header_name} header.",
            )

        user = await self._identity.resolve_or_create(external_id, email=external_id)
        return principal_module.Principal(user_id=user.user_id, email=user.email)


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
