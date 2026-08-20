from pymongo.asynchronous import collection

from app.integration.mural import models, ports


class MongoBoardAccessRequestStore(ports.BoardAccessRequestStore):
    def __init__(self, col: collection.AsyncCollection) -> None:  # type: ignore[type-arg]
        self._collection = col

    async def create(self, request: models.BoardAccessRequest) -> None:
        await self._collection.replace_one(
            {"id": request.id},
            request.model_dump(exclude={"approved"}),
            upsert=True,
        )

    async def get(self, request_id: str) -> models.BoardAccessRequest | None:
        doc = await self._collection.find_one({"id": request_id}, {"_id": 0})
        if doc is None:
            return None
        return models.BoardAccessRequest.model_validate(doc)

    async def get_latest_for_user_and_board(
        self, user_id: str, board_id: str
    ) -> models.BoardAccessRequest | None:
        doc = await self._collection.find_one(
            {"user_id": user_id, "board_id": board_id},
            {"_id": 0},
            sort=[("created_at", -1)],
        )
        if doc is None:
            return None
        return models.BoardAccessRequest.model_validate(doc)

    async def list_pending(self) -> list[models.BoardAccessRequest]:
        cursor = self._collection.find(
            {"status": models.AccessRequestStatus.PENDING.value}, {"_id": 0}
        )
        return [models.BoardAccessRequest.model_validate(doc) async for doc in cursor]

    async def update(self, request: models.BoardAccessRequest) -> None:
        await self._collection.replace_one(
            {"id": request.id},
            request.model_dump(exclude={"approved"}),
            upsert=True,
        )

    async def is_approved(self, user_id: str, board_id: str) -> bool:
        doc = await self._collection.find_one(
            {
                "user_id": user_id,
                "board_id": board_id,
                "status": models.AccessRequestStatus.APPROVED.value,
            },
            {"_id": 1},
        )
        return doc is not None
