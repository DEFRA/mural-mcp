import abc

from app.mural.connectivity import models


class TokenStore(abc.ABC):
    @abc.abstractmethod
    async def store_tokens(self, user_id: str, token: models.MuralToken) -> None: ...

    @abc.abstractmethod
    async def get_tokens(self, user_id: str) -> models.MuralToken | None: ...

    @abc.abstractmethod
    async def delete_tokens(self, user_id: str) -> None: ...
