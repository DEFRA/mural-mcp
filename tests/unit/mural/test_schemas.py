import datetime

from app.mural.connectivity import models as schemas


def test_mural_token_creation() -> None:
    """Test MuralToken model creation and validation."""
    token = schemas.MuralToken(
        access_token="test-access",
        refresh_token="test-refresh",
    )
    assert token.access_token == "test-access"
    assert token.refresh_token == "test-refresh"


def test_oauth_state_creation() -> None:
    """Test OAuthState model creation with datetime."""
    now = datetime.datetime.now(datetime.UTC)
    state = schemas.OAuthState(user_id="user123", expires_at=now)
    assert state.user_id == "user123"
    assert state.expires_at == now
