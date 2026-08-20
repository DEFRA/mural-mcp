import datetime

import pydantic


class MuralToken(pydantic.BaseModel):
    access_token: str
    refresh_token: str
    expires_at: datetime.datetime | None = None


class OAuthState(pydantic.BaseModel):
    user_id: str
    expires_at: datetime.datetime


class MuralConnectionStatus(pydantic.BaseModel):
    linked: bool
    access_token_expires_at: datetime.datetime | None = None
