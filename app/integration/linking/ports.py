import abc

from app.integration.linking import models


class TokenStore(abc.ABC):
    @abc.abstractmethod
    async def store_tokens(self, user_id: str, token: models.MuralToken) -> None: ...

    @abc.abstractmethod
    async def get_tokens(self, user_id: str) -> models.MuralToken | None: ...

    @abc.abstractmethod
    async def delete_tokens(self, user_id: str) -> None: ...


class OAuthStateStore(abc.ABC):
    @abc.abstractmethod
    async def issue(self, user_id: str) -> str: ...

    @abc.abstractmethod
    async def consume(self, state: str) -> models.OAuthState: ...
