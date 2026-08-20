import datetime
import uuid

from app.integration.linking import exceptions, models, ports


class InMemoryOAuthStateStore(ports.OAuthStateStore):
    def __init__(self) -> None:
        self._states: dict[str, models.OAuthState] = {}

    async def issue(self, user_id: str) -> str:
        state = str(uuid.uuid4())
        self._states[state] = models.OAuthState(
            user_id=user_id,
            expires_at=datetime.datetime.now(datetime.UTC)
            + datetime.timedelta(minutes=10),
        )
        return state

    async def consume(self, state: str) -> models.OAuthState:
        oauth_state = self._states.pop(state, None)

        if oauth_state is None:
            msg = "Invalid or unknown OAuth state"
            raise exceptions.OAuthStateError(msg)

        return oauth_state
