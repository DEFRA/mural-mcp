from app.mural.connectivity import models as schemas
from app.mural.connectivity import ports as token_store


class InMemoryTokenStore(token_store.TokenStore):
    def __init__(self, initial: dict[str, schemas.MuralToken] | None = None) -> None:
        self._store: dict[str, schemas.MuralToken] = dict(initial or {})

    async def store_tokens(self, user_id: str, token: schemas.MuralToken) -> None:
        self._store[user_id] = token

    async def get_tokens(self, user_id: str) -> schemas.MuralToken | None:
        return self._store.get(user_id)

    async def delete_tokens(self, user_id: str) -> None:
        self._store.pop(user_id, None)
