import abc

from app.mural.board.approval import models


class BoardApprovalStore(abc.ABC):
    @abc.abstractmethod
    async def create(self, approval: models.BoardApproval) -> None: ...

    @abc.abstractmethod
    async def get_by_board_id(
        self, board_id: str, email: str
    ) -> models.BoardApproval | None: ...

    @abc.abstractmethod
    async def exists_open(self, board_id: str) -> bool: ...
