from app.mural.board.approval import models, ports


class InMemoryBoardApprovalStore(ports.BoardApprovalStore):
    def __init__(self) -> None:
        self._store: list[models.BoardApproval] = []

    async def create(self, approval: models.BoardApproval) -> None:
        self._store.append(approval)

    async def get_by_board_id(
        self, board_id: str, email: str
    ) -> models.BoardApproval | None:
        for approval in self._store:
            if approval.board_id == board_id and approval.email == email:
                return approval
        return None

    async def exists_open(self, board_id: str) -> bool:
        return any(
            a.board_id == board_id and a.status != "rejected" for a in self._store
        )
