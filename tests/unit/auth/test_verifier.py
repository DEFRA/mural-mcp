import unittest.mock

import pytest

from app.auth import verifier as auth_verifier


def _make_verifier(
    resolve_email_return: str | None,
) -> auth_verifier.BearerTokenVerifier:
    mock_service = unittest.mock.AsyncMock()
    mock_service.resolve_email.return_value = resolve_email_return
    mock_container = unittest.mock.AsyncMock()
    mock_container.get.return_value = mock_service
    return auth_verifier.BearerTokenVerifier(mock_container)


@pytest.mark.asyncio
async def test_verify_token_valid() -> None:
    verifier = _make_verifier("user@example.com")
    result = await verifier.verify_token("valid-token")

    assert result is not None
    assert result.claims == {"email": "user@example.com"}
    assert result.client_id == "user@example.com"
    assert result.token == "valid-token"


@pytest.mark.asyncio
async def test_verify_token_unknown() -> None:
    verifier = _make_verifier(None)
    result = await verifier.verify_token("unknown-token")

    assert result is None


@pytest.mark.asyncio
async def test_verify_token_empty() -> None:
    mock_container = unittest.mock.MagicMock()
    verifier = auth_verifier.BearerTokenVerifier(mock_container)
    result = await verifier.verify_token("")

    assert result is None
    mock_container.get.assert_not_called()


@pytest.mark.asyncio
async def test_verify_token_whitespace_only() -> None:
    mock_container = unittest.mock.MagicMock()
    verifier = auth_verifier.BearerTokenVerifier(mock_container)
    result = await verifier.verify_token("   ")

    assert result is None
    mock_container.get.assert_not_called()
