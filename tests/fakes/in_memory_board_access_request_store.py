from app.integration.mural import models, ports


class InMemoryBoardAccessRequestStore(ports.BoardAccessRequestStore):
    def __init__(self) -> None:
        self._store: dict[str, models.BoardAccessRequest] = {}

    async def create(self, request: models.BoardAccessRequest) -> None:
        self._store[request.id] = request

    async def get(self, request_id: str) -> models.BoardAccessRequest | None:
        return self._store.get(request_id)

    async def get_latest_for_user_and_board(
        self, user_id: str, board_id: str
    ) -> models.BoardAccessRequest | None:
        matches = [
            r
            for r in self._store.values()
            if r.user_id == user_id and r.board_id == board_id
        ]
        if not matches:
            return None
        return max(matches, key=lambda r: r.created_at)

    async def list_pending(self) -> list[models.BoardAccessRequest]:
        return [
            r
            for r in self._store.values()
            if r.status == models.AccessRequestStatus.PENDING
        ]

    async def update(self, request: models.BoardAccessRequest) -> None:
        self._store[request.id] = request

    async def is_approved(self, user_id: str, board_id: str) -> bool:
        return any(
            r.user_id == user_id
            and r.board_id == board_id
            and r.status == models.AccessRequestStatus.APPROVED
            for r in self._store.values()
        )
