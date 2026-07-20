from app.mural.connectivity import exceptions


class FakeOAuthClient:
    """Returns a fixed access token per user, bypassing JWT validation and HTTP."""

    def __init__(self, default_token: str | None = None) -> None:
        self._token = default_token

    async def get_valid_token(self, user_id: str) -> str:  # noqa: ARG002
        if self._token is None:
            raise exceptions.MuralTokenError(f"No Mural token for user {user_id}")
        return self._token
