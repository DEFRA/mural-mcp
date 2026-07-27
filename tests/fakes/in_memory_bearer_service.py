from app.auth import service


class InMemoryBearerTokenService(service.BearerTokenService):
    """Dict-backed bearer token service. token→email and email→token."""

    def __init__(self, tokens: dict[str, str] | None = None) -> None:
        # maps token → email
        self._by_token: dict[str, str] = dict(tokens or {})
        # maps email → token (reverse index)
        self._by_email: dict[str, str] = {v: k for k, v in self._by_token.items()}

    async def resolve_email(self, token: str) -> str | None:
        return self._by_token.get(token)

    async def email_exists(self, email: str) -> bool:
        return email in self._by_email

    async def store_token(self, email: str, token: str) -> None:
        old_token = self._by_email.pop(email, None)
        if old_token is not None:
            self._by_token.pop(old_token, None)
        self._by_token[token] = email
        self._by_email[email] = token

    async def delete_token(self, email: str) -> None:
        token = self._by_email.pop(email, None)
        if token is not None:
            self._by_token.pop(token, None)
