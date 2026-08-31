import abc

from app.integration.mural import ports


class ForbiddenBoardError(Exception):
    """Raised by a BoardGuard to deny a user access to a board."""


class BoardGuard(abc.ABC):
    """Governance seam: decide whether a user may access a given board.

    BoardService._load calls this once, before every vendor call, so all
    four public methods (fetch_summary/fetch_region/fetch_connections/
    search_widgets) are gated from a single choke point.
    """

    @abc.abstractmethod
    async def check(self, user_id: str, board_id: str) -> None:
        """Return None to allow; raise ForbiddenBoardError to deny."""


class AllowAllBoardGuard(BoardGuard):
    """Permits access to every board. Default while RESOURCE_GUARD_MODE is
    unset — flip to AllowListBoardGuard once the admin review workflow has
    real approvals to check against."""

    async def check(self, user_id: str, board_id: str) -> None:  # noqa: ARG002
        return None


class AllowListBoardGuard(BoardGuard):
    """Permits access only where a BoardAccessRequest for the user/board pair
    has been approved (see BoardAccessRequestStore.is_approved)."""

    def __init__(self, store: ports.BoardAccessRequestStore) -> None:
        self._store = store

    async def check(self, user_id: str, board_id: str) -> None:
        if not await self._store.is_approved(user_id, board_id):
            msg = f"No approved access request for board {board_id}"
            raise ForbiddenBoardError(msg)
