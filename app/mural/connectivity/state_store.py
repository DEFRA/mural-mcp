import datetime
import uuid
from collections.abc import Callable

from app.mural.connectivity import models


def _utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class OAuthStateStore:
    """In-memory store of OAuth state tokens with TTL-based expiry.

    Sweeps expired entries on every consume() call so the dict stays bounded
    under sustained traffic. State is process-local — for multi-worker
    deployments, this needs to move to a shared store.
    """

    def __init__(
        self,
        clock: Callable[[], datetime.datetime] = _utc_now,
        ttl: datetime.timedelta = datetime.timedelta(minutes=10),
    ) -> None:
        self._clock = clock
        self._ttl = ttl
        self._states: dict[str, models.OAuthState] = {}

    def issue(self, user_id: str) -> str:
        state = str(uuid.uuid4())

        self._states[state] = models.OAuthState(
            user_id=user_id,
            expires_at=self._clock() + self._ttl,
        )

        return state

    def consume(self, state: str) -> models.OAuthState:
        oauth_state = self._states.pop(state, None)

        if oauth_state is None:
            msg = "Invalid or unknown OAuth state"
            raise ValueError(msg)

        if oauth_state.expires_at < self._clock():
            msg = "OAuth state has expired"
            raise ValueError(msg)

        self._sweep()

        return oauth_state

    def _sweep(self) -> None:
        now = self._clock()

        for state, entry in list(self._states.items()):
            if entry.expires_at < now:
                del self._states[state]
