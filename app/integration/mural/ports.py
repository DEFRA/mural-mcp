import abc

from app.integration.mural import models


class BoardAccessRequestStore(abc.ABC):
    @abc.abstractmethod
    async def create(self, request: models.BoardAccessRequest) -> None: ...

    @abc.abstractmethod
    async def get(self, request_id: str) -> models.BoardAccessRequest | None: ...

    @abc.abstractmethod
    async def get_latest_for_user_and_board(
        self, user_id: str, board_id: str
    ) -> models.BoardAccessRequest | None: ...

    @abc.abstractmethod
    async def list_pending(self) -> list[models.BoardAccessRequest]: ...

    @abc.abstractmethod
    async def update(self, request: models.BoardAccessRequest) -> None: ...

    @abc.abstractmethod
    async def is_approved(self, user_id: str, board_id: str) -> bool: ...
