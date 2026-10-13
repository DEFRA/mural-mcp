import datetime

import pytest

from app.integration.mural import guard as guard_module
from app.integration.mural import models
from tests.fakes import in_memory_board_access_request_store


class TestEnvAllowListBoardGuard:
    async def test_allows_a_listed_board_for_any_user(self) -> None:
        guard = guard_module.EnvAllowListBoardGuard(["board-1", "board-2"])

        await guard.check("a@example.com", "board-1")  # must not raise
        await guard.check("b@example.com", "board-2")

    async def test_denies_an_unlisted_board(self) -> None:
        guard = guard_module.EnvAllowListBoardGuard(["board-1"])

        with pytest.raises(guard_module.ForbiddenBoardError):
            await guard.check("a@example.com", "board-9")

    async def test_an_empty_list_denies_everything(self) -> None:
        guard = guard_module.EnvAllowListBoardGuard([])

        with pytest.raises(guard_module.ForbiddenBoardError):
            await guard.check("a@example.com", "board-1")

    async def test_a_wildcard_allows_every_board(self) -> None:
        guard = guard_module.EnvAllowListBoardGuard(["*"])

        await guard.check("a@example.com", "anything")  # must not raise


class TestAnyOfBoardGuard:
    async def test_allows_when_any_guard_allows(self) -> None:
        store = in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()
        guard = guard_module.AnyOfBoardGuard(
            guard_module.EnvAllowListBoardGuard(["board-1"]),
            guard_module.ApprovedRequestBoardGuard(store),
        )

        await guard.check("a@example.com", "board-1")  # via the env list

    async def test_an_approved_request_grants_an_unlisted_board(self) -> None:
        store = in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()
        await store.create(
            models.BoardAccessRequest(
                id="req-1",
                user_id="a@example.com",
                board_id="board-9",
                reason="why",
                iao="owner@x.com",
                status=models.AccessRequestStatus.APPROVED,
                created_at=datetime.datetime.now(datetime.UTC),
            )
        )
        guard = guard_module.AnyOfBoardGuard(
            guard_module.EnvAllowListBoardGuard(["board-1"]),
            guard_module.ApprovedRequestBoardGuard(store),
        )

        await guard.check("a@example.com", "board-9")  # via the approval

    async def test_denies_when_every_guard_denies(self) -> None:
        store = in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()
        guard = guard_module.AnyOfBoardGuard(
            guard_module.EnvAllowListBoardGuard(["board-1"]),
            guard_module.ApprovedRequestBoardGuard(store),
        )

        with pytest.raises(guard_module.ForbiddenBoardError):
            await guard.check("a@example.com", "board-9")


class TestApprovedRequestBoardGuard:
    async def test_denies_with_no_request(self) -> None:
        store = in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()
        guard = guard_module.ApprovedRequestBoardGuard(store)

        with pytest.raises(guard_module.ForbiddenBoardError):
            await guard.check("abc@example.com", "board-1")

    async def test_denies_a_pending_request(self) -> None:
        store = in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()
        await store.create(
            models.BoardAccessRequest(
                id="req-1",
                user_id="abc@example.com",
                board_id="board-1",
                reason="why",
                iao="owner@x.com",
                created_at=datetime.datetime.now(datetime.UTC),
            )
        )
        guard = guard_module.ApprovedRequestBoardGuard(store)

        with pytest.raises(guard_module.ForbiddenBoardError):
            await guard.check("abc@example.com", "board-1")

    async def test_allows_an_approved_request(self) -> None:
        store = in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()
        await store.create(
            models.BoardAccessRequest(
                id="req-1",
                user_id="abc@example.com",
                board_id="board-1",
                reason="why",
                iao="owner@x.com",
                status=models.AccessRequestStatus.APPROVED,
                created_at=datetime.datetime.now(datetime.UTC),
            )
        )
        guard = guard_module.ApprovedRequestBoardGuard(store)

        await guard.check("abc@example.com", "board-1")  # must not raise

    async def test_is_scoped_to_the_board(self) -> None:
        store = in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()
        await store.create(
            models.BoardAccessRequest(
                id="req-1",
                user_id="abc@example.com",
                board_id="board-1",
                reason="why",
                iao="owner@x.com",
                status=models.AccessRequestStatus.APPROVED,
                created_at=datetime.datetime.now(datetime.UTC),
            )
        )
        guard = guard_module.ApprovedRequestBoardGuard(store)

        with pytest.raises(guard_module.ForbiddenBoardError):
            await guard.check("abc@example.com", "some-other-board")

    async def test_is_scoped_to_the_user(self) -> None:
        store = in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()
        await store.create(
            models.BoardAccessRequest(
                id="req-1",
                user_id="abc@example.com",
                board_id="board-1",
                reason="why",
                iao="owner@x.com",
                status=models.AccessRequestStatus.APPROVED,
                created_at=datetime.datetime.now(datetime.UTC),
            )
        )
        guard = guard_module.ApprovedRequestBoardGuard(store)

        with pytest.raises(guard_module.ForbiddenBoardError):
            await guard.check("someone_else", "board-1")
