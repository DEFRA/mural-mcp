import unittest.mock

import pytest

from app.auth import service as bearer_service


@pytest.mark.asyncio
async def test_resolve_email_found() -> None:
    mock_collection = unittest.mock.AsyncMock()
    mock_collection.find_one.return_value = {"email": "user@example.com"}
    svc = bearer_service.MongoBearerTokenService(mock_collection)
    result = await svc.resolve_email("my-token")
    assert result == "user@example.com"
    mock_collection.find_one.assert_awaited_once_with(
        {"token": "my-token"}, {"_id": 0, "email": 1}
    )


@pytest.mark.asyncio
async def test_resolve_email_not_found() -> None:
    mock_collection = unittest.mock.AsyncMock()
    mock_collection.find_one.return_value = None
    svc = bearer_service.MongoBearerTokenService(mock_collection)
    result = await svc.resolve_email("unknown-token")
    assert result is None


@pytest.mark.asyncio
async def test_email_exists_true() -> None:
    mock_collection = unittest.mock.AsyncMock()
    mock_collection.find_one.return_value = {"_id": "some-id"}
    svc = bearer_service.MongoBearerTokenService(mock_collection)
    result = await svc.email_exists("user@example.com")
    assert result is True
    mock_collection.find_one.assert_awaited_once_with(
        {"email": "user@example.com"}, {"_id": 1}
    )


@pytest.mark.asyncio
async def test_email_exists_false() -> None:
    mock_collection = unittest.mock.AsyncMock()
    mock_collection.find_one.return_value = None
    svc = bearer_service.MongoBearerTokenService(mock_collection)
    result = await svc.email_exists("unknown@example.com")
    assert result is False


@pytest.mark.asyncio
async def test_store_token() -> None:
    mock_collection = unittest.mock.AsyncMock()
    svc = bearer_service.MongoBearerTokenService(mock_collection)
    await svc.store_token("user@example.com", "my-token")
    mock_collection.replace_one.assert_awaited_once()
    args = mock_collection.replace_one.await_args
    assert args[0][0] == {"email": "user@example.com"}
    assert args[0][1] == {"email": "user@example.com", "token": "my-token"}
    assert args[1]["upsert"] is True


@pytest.mark.asyncio
async def test_delete_token() -> None:
    mock_collection = unittest.mock.AsyncMock()
    svc = bearer_service.MongoBearerTokenService(mock_collection)
    await svc.delete_token("user@example.com")
    mock_collection.delete_one.assert_awaited_once_with({"email": "user@example.com"})
