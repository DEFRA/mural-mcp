"""The concrete TokenVerifier: mural-mcp mints its own personal access
tokens, so verification is a lookup against PersonalTokenService rather than
a signature check against an external IdP's key. This is the only
implementation of app.auth.verifier.TokenVerifier in the app — both /mcp
(app.infra.mcp.auth) and REST (app.infra.rest.auth.resolver) bind to it.
"""

from app.auth import verifier
from app.identity import exceptions
from app.identity import service as identity_service


class PersonalTokenVerifier:
    def __init__(self, tokens: identity_service.PersonalTokenService) -> None:
        self._tokens = tokens

    async def verify(self, token: str) -> verifier.VerifiedToken | None:
        try:
            record = await self._tokens.verify(token)
        except (
            exceptions.UnknownTokenError,
            exceptions.TokenExpiredError,
            exceptions.TokenRevokedError,
        ):
            return None

        return verifier.VerifiedToken(
            claims={
                "sub": record.user_id,
                "email": record.user_id,
                "label": record.label,
                "token_id": record.id,
            }
        )
