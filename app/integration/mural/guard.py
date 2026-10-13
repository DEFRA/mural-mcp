import abc
from collections.abc import Collection

from app.integration.mural import ports

ALLOW_ALL = "*"


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


class EnvAllowListBoardGuard(BoardGuard):
    """Permits only the boards named in ALLOWED_BOARD_IDS, for every user.
    "*" permits every board (local development only); an empty list denies
    all of them."""

    def __init__(self, allowed_board_ids: Collection[str]) -> None:
        self._allowed = frozenset(allowed_board_ids)

    async def check(self, user_id: str, board_id: str) -> None:  # noqa: ARG002
        if ALLOW_ALL in self._allowed or board_id in self._allowed:
            return
        msg = f"Board {board_id} is not on the allow list"
        raise ForbiddenBoardError(msg)


class ApprovedRequestBoardGuard(BoardGuard):
    """Permits access where a BoardAccessRequest for the user/board pair
    has been approved (see BoardAccessRequestStore.is_approved). Only wired
    when SELF_SERVICE_ACCESS_ENABLED."""

    def __init__(self, store: ports.BoardAccessRequestStore) -> None:
        self._store = store

    async def check(self, user_id: str, board_id: str) -> None:
        if not await self._store.is_approved(user_id, board_id):
            msg = f"No approved access request for board {board_id}"
            raise ForbiddenBoardError(msg)


class AnyOfBoardGuard(BoardGuard):
    """Permits access if any one of the wrapped guards does."""

    def __init__(self, *guards: BoardGuard) -> None:
        self._guards = guards

    async def check(self, user_id: str, board_id: str) -> None:
        denial: ForbiddenBoardError | None = None
        for guard in self._guards:
            try:
                await guard.check(user_id, board_id)
            except ForbiddenBoardError as exc:
                denial = denial or exc
            else:
                return
        if denial is None:
            msg = f"No guard permits board {board_id}"
            raise ForbiddenBoardError(msg)
        raise denial
