import unittest.mock

import fastapi
import pytest

from app.auth import dependencies
from app.auth import service as auth_service


def _make_request(
    auth_header: str | None = None,
    bearer_service: auth_service.BearerTokenService | None = None,
) -> fastapi.Request:
    headers = {}
    if auth_header is not None:
        headers["authorization"] = auth_header
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
    }
    request = fastapi.Request(scope)
    mock_container = unittest.mock.AsyncMock()
    mock_container.get.return_value = (
        bearer_service
        if bearer_service is not None
        else unittest.mock.AsyncMock(spec=auth_service.BearerTokenService)
    )
    request.state.dishka_container = mock_container
    return request


@pytest.mark.asyncio
async def test_get_current_user_valid_token() -> None:
    mock_service = unittest.mock.AsyncMock()
    mock_service.resolve_email.return_value = "user@example.com"
    request = _make_request("Bearer my-token", bearer_service=mock_service)

    result = await dependencies.get_current_user(request=request)

    assert result == "user@example.com"
    mock_service.resolve_email.assert_awaited_once_with("my-token")


@pytest.mark.asyncio
async def test_get_current_user_missing_header() -> None:
    request = _make_request()
    with pytest.raises(fastapi.HTTPException) as exc_info:
        await dependencies.get_current_user(request=request)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_scheme() -> None:
    request = _make_request("Basic test")
    with pytest.raises(fastapi.HTTPException) as exc_info:
        await dependencies.get_current_user(request=request)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_token() -> None:
    mock_service = unittest.mock.AsyncMock()
    mock_service.resolve_email.return_value = None
    request = _make_request("Bearer bad-token", bearer_service=mock_service)
    with pytest.raises(fastapi.HTTPException) as exc_info:
        await dependencies.get_current_user(request=request)
    assert exc_info.value.status_code == 401
