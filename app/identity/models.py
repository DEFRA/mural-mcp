import datetime

import pydantic


class User(pydantic.BaseModel):
    """A caller identity.

    Created the first time a portal asserts an external identity via the
    trusted-header mint route. ``user_id`` is the only identifier the rest of
    the domain (Mural tokens, board approvals) ever sees; ``external_id`` is
    what lets a repeat visit from the same portal-asserted identity resolve
    back to the same user rather than minting a duplicate.
    """

    user_id: str
    external_id: str
    email: str | None = None
    created_at: datetime.datetime


class PersonalAccessToken(pydantic.BaseModel):
    """A minted personal access token record.

    The plaintext secret is never stored — only its SHA-256 hash — so there
    is no code path that can return it after the mint response.
    """

    id: str
    user_id: str
    token_hash: str
    prefix: str
    label: str
    created_at: datetime.datetime
    expires_at: datetime.datetime
    last_used_at: datetime.datetime | None = None
    revoked_at: datetime.datetime | None = None

    @property
    def is_active(self) -> bool:
        now = datetime.datetime.now(datetime.UTC)
        return self.revoked_at is None and self.expires_at > now
