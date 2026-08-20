import unittest.mock

import pytest

from app.integration.linking import exceptions, models, oauth_client, service
from tests.fakes import in_memory_oauth_state_store, in_memory_token_store


def _make_oauth_mock() -> unittest.mock.NonCallableMock:
    """Autospec'd against OAuthClient so sync methods (build_authorization_url)
    and async methods (exchange_code) are mocked correctly -- a plain
    AsyncMock() would wrap every attribute as async, including sync ones."""
    return unittest.mock.create_autospec(oauth_client.OAuthClient, instance=True)


def _make_service(
    oauth: unittest.mock.NonCallableMock,
) -> tuple[
    service.LinkingService,
    in_memory_token_store.InMemoryTokenStore,
    in_memory_oauth_state_store.InMemoryOAuthStateStore,
]:
    tokens = in_memory_token_store.InMemoryTokenStore()
    states = in_memory_oauth_state_store.InMemoryOAuthStateStore()
    return (
        service.LinkingService(oauth=oauth, tokens=tokens, states=states),
        tokens,
        states,
    )


@pytest.mark.asyncio
async def test_get_authorization_url_issues_state_and_returns_authorization_url() -> (
    None
):
    oauth = _make_oauth_mock()
    oauth.build_authorization_url.side_effect = (
        lambda state: f"https://app.mural.co/authorize?state={state}"
    )
    linking, _tokens, states = _make_service(oauth)

    url = await linking.get_authorization_url("user-123")

    assert url.startswith("https://app.mural.co/authorize?state=")
    issued_state = url.rsplit("=", 1)[1]
    # The state was consumed by build_authorization_url's caller only in
    # spirit -- issue() doesn't consume, so it should still resolve here.
    oauth_state = await states.consume(issued_state)
    assert oauth_state.user_id == "user-123"


@pytest.mark.asyncio
async def test_complete_connection_exchanges_code_and_stores_token() -> None:
    oauth = _make_oauth_mock()
    token = models.MuralToken(access_token="a", refresh_token="b")
    oauth.exchange_code.return_value = token
    linking, tokens, states = _make_service(oauth)
    state = await states.issue("user-123")

    await linking.complete_connection("user-123", "auth-code", state)

    oauth.exchange_code.assert_awaited_once_with("auth-code")
    assert await tokens.get_tokens("user-123") == token


@pytest.mark.asyncio
async def test_complete_connection_raises_on_user_mismatch() -> None:
    oauth = _make_oauth_mock()
    linking, tokens, states = _make_service(oauth)
    state = await states.issue("user-123")

    with pytest.raises(exceptions.LinkMismatchError):
        await linking.complete_connection("someone-else", "auth-code", state)

    oauth.exchange_code.assert_not_called()
    assert await tokens.get_tokens("user-123") is None


@pytest.mark.asyncio
async def test_complete_connection_propagates_unknown_state_error() -> None:
    oauth = _make_oauth_mock()
    linking, _tokens, _states = _make_service(oauth)

    with pytest.raises(exceptions.OAuthStateError):
        await linking.complete_connection("user-123", "auth-code", "not-a-real-state")

    oauth.exchange_code.assert_not_called()


@pytest.mark.asyncio
async def test_disconnect_removes_stored_token() -> None:
    oauth = _make_oauth_mock()
    linking, tokens, _states = _make_service(oauth)
    await tokens.store_tokens(
        "user-123", models.MuralToken(access_token="a", refresh_token="b")
    )

    await linking.disconnect("user-123")

    assert await tokens.get_tokens("user-123") is None
