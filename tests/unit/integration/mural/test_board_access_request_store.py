import datetime
import unittest.mock

import pytest
from pymongo import common as pymongo_common

from app.integration.mural import models
from app.integration.mural import mongo_store as approval_store

_NOW = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)


def _make_request(**kwargs: object) -> models.BoardAccessRequest:
    defaults: dict[str, object] = {
        "id": "req-123",
        "user_id": "usr_abc",
        "board_id": "board-123",
        "reason": "need it for a workshop",
        "iao": "owner@defra.gov.uk",
        "created_at": _NOW,
    }
    defaults.update(kwargs)
    return models.BoardAccessRequest(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_create_replacement_is_valid_for_real_pymongo() -> None:
    mock_col = unittest.mock.AsyncMock()
    store = approval_store.MongoBoardAccessRequestStore(mock_col)
    request = _make_request()

    await store.create(request)

    replacement = mock_col.replace_one.await_args[0][1]
    pymongo_common.validate_ok_for_replace(replacement)
    assert mock_col.replace_one.await_args[1]["upsert"] is True
    assert replacement["id"] == "req-123"
    assert replacement["board_id"] == "board-123"
    assert "approved" not in replacement


@pytest.mark.asyncio
async def test_get_found() -> None:
    mock_col = unittest.mock.AsyncMock()
    mock_col.find_one.return_value = _make_request().model_dump(exclude={"approved"})
    store = approval_store.MongoBoardAccessRequestStore(mock_col)

    result = await store.get("req-123")

    assert result is not None
    assert result.id == "req-123"
    mock_col.find_one.assert_awaited_once_with({"id": "req-123"}, {"_id": 0})


@pytest.mark.asyncio
async def test_get_not_found() -> None:
    mock_col = unittest.mock.AsyncMock()
    mock_col.find_one.return_value = None
    store = approval_store.MongoBoardAccessRequestStore(mock_col)

    assert await store.get("nonexistent") is None


@pytest.mark.asyncio
async def test_get_latest_for_user_and_board_sorts_by_created_at_desc() -> None:
    mock_col = unittest.mock.AsyncMock()
    mock_col.find_one.return_value = _make_request().model_dump(exclude={"approved"})
    store = approval_store.MongoBoardAccessRequestStore(mock_col)

    result = await store.get_latest_for_user_and_board("usr_abc", "board-123")

    assert result is not None
    mock_col.find_one.assert_awaited_once_with(
        {"user_id": "usr_abc", "board_id": "board-123"},
        {"_id": 0},
        sort=[("created_at", -1)],
    )


@pytest.mark.asyncio
async def test_list_pending_filters_by_status() -> None:
    mock_col = unittest.mock.AsyncMock()

    async def _cursor():
        yield _make_request().model_dump(exclude={"approved"})

    # pymongo's find() is sync, returning an async-iterable cursor -- not a
    # coroutine to await, so it must be a plain (non-async) mock attribute.
    mock_col.find = unittest.mock.MagicMock(return_value=_cursor())
    store = approval_store.MongoBoardAccessRequestStore(mock_col)

    result = await store.list_pending()

    assert len(result) == 1
    mock_col.find.assert_called_once_with({"status": "pending"}, {"_id": 0})


@pytest.mark.asyncio
async def test_is_approved_true() -> None:
    mock_col = unittest.mock.AsyncMock()
    mock_col.find_one.return_value = {"_id": "x"}
    store = approval_store.MongoBoardAccessRequestStore(mock_col)

    result = await store.is_approved("usr_abc", "board-123")

    assert result is True
    mock_col.find_one.assert_awaited_once_with(
        {"user_id": "usr_abc", "board_id": "board-123", "status": "approved"},
        {"_id": 1},
    )


@pytest.mark.asyncio
async def test_is_approved_false() -> None:
    mock_col = unittest.mock.AsyncMock()
    mock_col.find_one.return_value = None
    store = approval_store.MongoBoardAccessRequestStore(mock_col)

    assert await store.is_approved("usr_abc", "board-123") is False
