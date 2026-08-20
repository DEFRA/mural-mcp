import datetime
import unittest.mock
import uuid

import pytest

from app.integration.linking import exceptions
from app.integration.linking import mongo_store as state_store


@pytest.mark.asyncio
async def test_issue_inserts_a_document_and_returns_a_uuid_string() -> None:
    mock_collection = unittest.mock.AsyncMock()
    store = state_store.MongoOAuthStateStore(mock_collection)

    state = await store.issue("user-123")

    uuid.UUID(state)
    mock_collection.insert_one.assert_awaited_once()
    doc = mock_collection.insert_one.await_args[0][0]
    assert doc["_id"] == state
    assert doc["user_id"] == "user-123"


@pytest.mark.asyncio
async def test_issue_sets_expires_at_from_clock_and_ttl() -> None:
    now = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    mock_collection = unittest.mock.AsyncMock()
    store = state_store.MongoOAuthStateStore(
        mock_collection, clock=lambda: now, ttl=datetime.timedelta(minutes=5)
    )

    await store.issue("user-123")

    doc = mock_collection.insert_one.await_args[0][0]
    assert doc["expires_at"] == now + datetime.timedelta(minutes=5)


@pytest.mark.asyncio
async def test_consume_returns_oauth_state_for_issued_token() -> None:
    now = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    mock_collection = unittest.mock.AsyncMock()
    mock_collection.find_one_and_delete.return_value = {
        "_id": "state-123",
        "user_id": "user-123",
        "expires_at": now + datetime.timedelta(minutes=5),
    }
    store = state_store.MongoOAuthStateStore(mock_collection, clock=lambda: now)

    result = await store.consume("state-123")

    assert result.user_id == "user-123"
    mock_collection.find_one_and_delete.assert_awaited_once_with({"_id": "state-123"})


@pytest.mark.asyncio
async def test_consume_rejects_unknown_state() -> None:
    mock_collection = unittest.mock.AsyncMock()
    mock_collection.find_one_and_delete.return_value = None
    store = state_store.MongoOAuthStateStore(mock_collection)

    with pytest.raises(exceptions.OAuthStateError, match="Invalid or unknown"):
        await store.consume("not-a-real-state")


@pytest.mark.asyncio
async def test_consume_rejects_expired_state() -> None:
    issued_at = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    now = issued_at + datetime.timedelta(minutes=10)
    mock_collection = unittest.mock.AsyncMock()
    mock_collection.find_one_and_delete.return_value = {
        "_id": "state-123",
        "user_id": "user-123",
        "expires_at": issued_at + datetime.timedelta(minutes=5),
    }
    store = state_store.MongoOAuthStateStore(mock_collection, clock=lambda: now)

    with pytest.raises(exceptions.OAuthStateError, match="expired"):
        await store.consume("state-123")


@pytest.mark.asyncio
async def test_ensure_indexes_creates_ttl_index_on_expires_at() -> None:
    mock_collection = unittest.mock.AsyncMock()
    store = state_store.MongoOAuthStateStore(mock_collection)

    await store.ensure_indexes()

    mock_collection.create_index.assert_awaited_once_with(
        "expires_at", expireAfterSeconds=0
    )
