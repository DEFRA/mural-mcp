import datetime

import pydantic


class MuralToken(pydantic.BaseModel):
    access_token: str
    refresh_token: str


class OAuthState(pydantic.BaseModel):
    user_id: str
    expires_at: datetime.datetime
