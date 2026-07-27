import datetime
import uuid

import pytest

from app.mural.connectivity import state_store as state_store_module


def test_issue_returns_uuid_string():
    store = state_store_module.OAuthStateStore()
    state = store.issue("user-123")
    assert isinstance(state, str)
    uuid.UUID(state)


def test_issue_returns_unique_states_per_call():
    store = state_store_module.OAuthStateStore()
    assert store.issue("user-1") != store.issue("user-2")


def test_consume_returns_oauth_state_for_issued_token():
    now = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    store = state_store_module.OAuthStateStore(
        clock=lambda: now,
        ttl=datetime.timedelta(minutes=5),
    )
    state = store.issue("user-123")
    result = store.consume(state)
    assert result.user_id == "user-123"
    assert result.expires_at == now + datetime.timedelta(minutes=5)


def test_consume_rejects_unknown_state():
    store = state_store_module.OAuthStateStore()
    with pytest.raises(ValueError, match="Invalid or unknown OAuth state"):
        store.consume("not-a-real-state")


def test_consume_rejects_expired_state():
    issued_at = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    now = [issued_at]
    store = state_store_module.OAuthStateStore(
        clock=lambda: now[0],
        ttl=datetime.timedelta(minutes=5),
    )
    state = store.issue("user-123")
    now[0] = issued_at + datetime.timedelta(minutes=10)
    with pytest.raises(ValueError, match="OAuth state has expired"):
        store.consume(state)


def test_consume_removes_state_after_use():
    store = state_store_module.OAuthStateStore()
    state = store.issue("user-123")
    store.consume(state)
    with pytest.raises(ValueError, match="Invalid or unknown OAuth state"):
        store.consume(state)


def test_consume_sweeps_expired_entries():
    issued_at = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
    now = [issued_at]
    store = state_store_module.OAuthStateStore(
        clock=lambda: now[0],
        ttl=datetime.timedelta(minutes=5),
    )
    expired = store.issue("user-1")
    now[0] = issued_at + datetime.timedelta(minutes=10)
    fresh = store.issue("user-2")
    store.consume(fresh)
    assert expired not in store._states
