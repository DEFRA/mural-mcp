from pymongo.asynchronous import collection

from app.mural.board.approval import models, ports


class MongoBoardApprovalStore(ports.BoardApprovalStore):
    def __init__(self, col: collection.AsyncCollection) -> None:  # type: ignore[type-arg]
        self._collection = col

    async def create(self, approval: models.BoardApproval) -> None:
        await self._collection.insert_one(
            {
                "boardId": approval.board_id,
                "iao": approval.iao,
                "email": approval.email,
                "status": approval.status,
                "submittedAt": approval.submitted_at,
            }
        )

    async def get_by_board_id(
        self, board_id: str, email: str
    ) -> models.BoardApproval | None:
        doc = await self._collection.find_one(
            {"boardId": board_id, "email": email}, {"_id": 0}
        )

        if doc is None:
            return None

        return models.BoardApproval(
            board_id=doc["boardId"],
            iao=doc["iao"],
            email=doc["email"],
            status=doc["status"],
            submitted_at=doc["submittedAt"],
        )

    async def exists_open(self, board_id: str) -> bool:
        doc = await self._collection.find_one(
            {"boardId": board_id, "status": {"$ne": "rejected"}}
        )

        return doc is not None
