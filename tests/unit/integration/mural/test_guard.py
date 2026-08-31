import datetime

import pytest

from app.integration.mural import guard as guard_module
from app.integration.mural import models
from tests.fakes import in_memory_board_access_request_store


class TestAllowAllBoardGuard:
    async def test_never_denies(self) -> None:
        guard = guard_module.AllowAllBoardGuard()

        await guard.check("usr_abc", "board-1")  # must not raise


class TestAllowListBoardGuard:
    async def test_denies_with_no_request(self) -> None:
        store = in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()
        guard = guard_module.AllowListBoardGuard(store)

        with pytest.raises(guard_module.ForbiddenBoardError):
            await guard.check("usr_abc", "board-1")

    async def test_denies_a_pending_request(self) -> None:
        store = in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()
        await store.create(
            models.BoardAccessRequest(
                id="req-1",
                user_id="usr_abc",
                board_id="board-1",
                reason="why",
                iao="owner@x.com",
                created_at=datetime.datetime.now(datetime.UTC),
            )
        )
        guard = guard_module.AllowListBoardGuard(store)

        with pytest.raises(guard_module.ForbiddenBoardError):
            await guard.check("usr_abc", "board-1")

    async def test_allows_an_approved_request(self) -> None:
        store = in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()
        await store.create(
            models.BoardAccessRequest(
                id="req-1",
                user_id="usr_abc",
                board_id="board-1",
                reason="why",
                iao="owner@x.com",
                status=models.AccessRequestStatus.APPROVED,
                created_at=datetime.datetime.now(datetime.UTC),
            )
        )
        guard = guard_module.AllowListBoardGuard(store)

        await guard.check("usr_abc", "board-1")  # must not raise

    async def test_is_scoped_to_the_board(self) -> None:
        store = in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()
        await store.create(
            models.BoardAccessRequest(
                id="req-1",
                user_id="usr_abc",
                board_id="board-1",
                reason="why",
                iao="owner@x.com",
                status=models.AccessRequestStatus.APPROVED,
                created_at=datetime.datetime.now(datetime.UTC),
            )
        )
        guard = guard_module.AllowListBoardGuard(store)

        with pytest.raises(guard_module.ForbiddenBoardError):
            await guard.check("usr_abc", "some-other-board")

    async def test_is_scoped_to_the_user(self) -> None:
        store = in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()
        await store.create(
            models.BoardAccessRequest(
                id="req-1",
                user_id="usr_abc",
                board_id="board-1",
                reason="why",
                iao="owner@x.com",
                status=models.AccessRequestStatus.APPROVED,
                created_at=datetime.datetime.now(datetime.UTC),
            )
        )
        guard = guard_module.AllowListBoardGuard(store)

        with pytest.raises(guard_module.ForbiddenBoardError):
            await guard.check("someone_else", "board-1")
