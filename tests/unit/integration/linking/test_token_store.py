import unittest.mock

import pytest
from pymongo import common as pymongo_common

from app.integration.linking import models as schemas
from app.integration.linking import mongo_store as token_store


@pytest.mark.asyncio
async def test_store_tokens() -> None:
    """Test storing tokens in MongoTokenStore."""
    mock_collection = unittest.mock.AsyncMock()
    store = token_store.MongoTokenStore(mock_collection)
    token = schemas.MuralToken(access_token="test", refresh_token="test")
    await store.store_tokens("user-123", token)
    mock_collection.replace_one.assert_awaited_once()
    args = mock_collection.replace_one.await_args
    assert args[0][0] == {"user_id": "user-123"}
    assert args[0][1] == {
        "user_id": "user-123",
        "access_token": "test",
        "refresh_token": "test",
        "expires_at": None,
    }
    assert args[1]["upsert"] is True


@pytest.mark.asyncio
async def test_store_tokens_replacement_is_valid_for_real_pymongo() -> None:
    """Regression guard: a mocked collection accepts any arguments, so a call
    like ``replace_one(filter, {"$set": doc}, upsert=True)`` looks correct here
    even though real pymongo rejects a replacement document containing $
    operators. Validate the second positional argument the same way pymongo's
    AsyncCollection.replace_one does, to catch that class of bug without a live
    MongoDB.
    """
    mock_collection = unittest.mock.AsyncMock()
    store = token_store.MongoTokenStore(mock_collection)
    token = schemas.MuralToken(access_token="test", refresh_token="test")
    await store.store_tokens("user-123", token)
    replacement = mock_collection.replace_one.await_args[0][1]
    pymongo_common.validate_ok_for_replace(replacement)


@pytest.mark.asyncio
async def test_get_tokens_found() -> None:
    """Test retrieving tokens when they exist."""
    mock_collection = unittest.mock.AsyncMock()
    mock_collection.find_one.return_value = {
        "user_id": "user-123",
        "access_token": "test",
        "refresh_token": "test",
    }
    store = token_store.MongoTokenStore(mock_collection)
    result = await store.get_tokens("user-123")
    assert result is not None
    assert result.access_token == "test"
    assert result.refresh_token == "test"


@pytest.mark.asyncio
async def test_get_tokens_not_found() -> None:
    """Test retrieving tokens when none exist."""
    mock_collection = unittest.mock.AsyncMock()
    mock_collection.find_one.return_value = None
    store = token_store.MongoTokenStore(mock_collection)
    result = await store.get_tokens("user-123")
    assert result is None


@pytest.mark.asyncio
async def test_delete_tokens() -> None:
    """Test deleting tokens."""
    mock_collection = unittest.mock.AsyncMock()
    store = token_store.MongoTokenStore(mock_collection)
    await store.delete_tokens("user-123")
    mock_collection.delete_one.assert_awaited_once_with({"user_id": "user-123"})
