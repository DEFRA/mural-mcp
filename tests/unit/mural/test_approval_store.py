import datetime
import unittest.mock

import pytest

from app.mural.board.approval import models
from app.mural.board.approval import mongo_store as approval_store

_NOW = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)


def _make_approval(**kwargs: object) -> models.BoardApproval:
    defaults: dict[str, object] = {
        "board_id": "board-123",
        "iao": "owner@defra.gov.uk",
        "email": "user@example.com",
        "status": "pending",
        "submitted_at": _NOW,
    }
    defaults.update(kwargs)
    return models.BoardApproval(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_create_inserts_document() -> None:
    mock_col = unittest.mock.AsyncMock()
    store = approval_store.MongoBoardApprovalStore(mock_col)
    approval = _make_approval()

    await store.create(approval)

    mock_col.insert_one.assert_awaited_once()
    doc = mock_col.insert_one.await_args[0][0]
    assert doc["boardId"] == "board-123"
    assert doc["iao"] == "owner@defra.gov.uk"
    assert doc["status"] == "pending"


@pytest.mark.asyncio
async def test_get_by_board_id_found() -> None:
    mock_col = unittest.mock.AsyncMock()
    mock_col.find_one.return_value = {
        "boardId": "board-123",
        "iao": "owner@defra.gov.uk",
        "email": "user@example.com",
        "status": "pending",
        "submittedAt": _NOW,
    }
    store = approval_store.MongoBoardApprovalStore(mock_col)

    result = await store.get_by_board_id("board-123", "user@example.com")

    assert result is not None
    assert result.board_id == "board-123"
    assert result.approved is False
    mock_col.find_one.assert_awaited_once_with(
        {"boardId": "board-123", "email": "user@example.com"}, {"_id": 0}
    )


@pytest.mark.asyncio
async def test_get_by_board_id_not_found() -> None:
    mock_col = unittest.mock.AsyncMock()
    mock_col.find_one.return_value = None
    store = approval_store.MongoBoardApprovalStore(mock_col)

    result = await store.get_by_board_id("board-123", "user@example.com")

    assert result is None


@pytest.mark.asyncio
async def test_get_by_board_id_approved_flag() -> None:
    mock_col = unittest.mock.AsyncMock()
    mock_col.find_one.return_value = {
        "boardId": "board-123",
        "iao": "owner@defra.gov.uk",
        "email": "user@example.com",
        "status": "approved",
        "submittedAt": _NOW,
    }
    store = approval_store.MongoBoardApprovalStore(mock_col)

    result = await store.get_by_board_id("board-123", "user@example.com")

    assert result is not None
    assert result.approved is True


@pytest.mark.asyncio
async def test_exists_open_true() -> None:
    mock_col = unittest.mock.AsyncMock()
    mock_col.find_one.return_value = {"boardId": "board-123"}
    store = approval_store.MongoBoardApprovalStore(mock_col)

    result = await store.exists_open("board-123")

    assert result is True
    mock_col.find_one.assert_awaited_once_with(
        {"boardId": "board-123", "status": {"$ne": "rejected"}}
    )


@pytest.mark.asyncio
async def test_exists_open_false() -> None:
    mock_col = unittest.mock.AsyncMock()
    mock_col.find_one.return_value = None
    store = approval_store.MongoBoardApprovalStore(mock_col)

    result = await store.exists_open("board-123")

    assert result is False
