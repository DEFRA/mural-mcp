import datetime

import pydantic


class PersonalAccessToken(pydantic.BaseModel):
    """A minted personal access token record.

    The plaintext secret is never stored — only its SHA-256 hash — so there
    is no code path that can return it after the mint response.
    """

    id: str
    user_id: str  # the owner's email, as asserted by the portal
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
