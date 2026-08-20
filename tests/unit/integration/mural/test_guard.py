import datetime

import pytest

from app.integration.mural import guard as guard_module
from app.integration.mural import models
from tests.fakes import in_memory_board_access_request_store


@pytest.mark.asyncio
async def test_allow_all_guard_never_denies() -> None:
    guard = guard_module.AllowAllBoardGuard()

    await guard.check("usr_abc", "board-1")  # must not raise


@pytest.mark.asyncio
async def test_allow_list_guard_denies_with_no_request() -> None:
    store = in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()
    guard = guard_module.AllowListBoardGuard(store)

    with pytest.raises(guard_module.ForbiddenBoardError):
        await guard.check("usr_abc", "board-1")


@pytest.mark.asyncio
async def test_allow_list_guard_denies_a_pending_request() -> None:
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


@pytest.mark.asyncio
async def test_allow_list_guard_allows_an_approved_request() -> None:
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


@pytest.mark.asyncio
async def test_allow_list_guard_is_scoped_to_the_board() -> None:
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


@pytest.mark.asyncio
async def test_allow_list_guard_is_scoped_to_the_user() -> None:
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
