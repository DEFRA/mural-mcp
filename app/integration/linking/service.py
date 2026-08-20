from app.integration.linking import exceptions, models, oauth_client, ports


class LinkingService:
    """Coordinates the Mural OAuth account-linking flow: issuing/validating
    state, exchanging codes for tokens, and removing stored credentials."""

    def __init__(
        self,
        oauth: oauth_client.OAuthClient,
        tokens: ports.TokenStore,
        states: ports.OAuthStateStore,
    ) -> None:
        self._oauth = oauth
        self._tokens = tokens
        self._states = states

    async def get_authorization_url(self, user_id: str) -> str:
        """Issue an OAuth state for user_id and return the Mural
        authorization URL."""
        state = await self._states.issue(user_id)
        return self._oauth.build_authorization_url(state)

    async def complete_connection(self, user_id: str, code: str, state: str) -> None:
        """Validate state belongs to user_id, exchange code for a token, and
        persist it.

        Raises exceptions.OAuthStateError if state is unknown, already
        consumed, or expired, and exceptions.LinkMismatchError if state was
        issued for a different user.
        """
        oauth_state = await self._states.consume(state)

        if oauth_state.user_id != user_id:
            msg = "OAuth state was issued for a different user."
            raise exceptions.LinkMismatchError(msg)

        token = await self._oauth.exchange_code(code)

        await self._tokens.store_tokens(oauth_state.user_id, token)

    async def disconnect(self, user_id: str) -> None:
        """Remove the user's stored Mural credentials."""
        await self._tokens.delete_tokens(user_id)

    async def get_connection_status(
        self, user_id: str
    ) -> models.MuralConnectionStatus:
        """Get the user's Mural connection status, including token expiry.
        """
        token = await self._tokens.get_tokens(user_id)

        if token is None:
            return models.MuralConnectionStatus(
                linked=False,
                access_token_expires_at=None,
            )

        return models.MuralConnectionStatus(
            linked=True,
            access_token_expires_at=token.expires_at,
        )
