import pydantic

from app.config import AppConfig, IdentityConfig, MuralConfig


def _mural_config() -> MuralConfig:
    """Built via model_construct so this test never reads real env/.env values."""
    return MuralConfig.model_construct(
        api_base="https://app.mural.co/api",
        client_id="test-client-id",
        client_secret=pydantic.SecretStr("test-secret"),
        callback_path="/callback",
    )


def _make_config(**overrides: object) -> AppConfig:
    kwargs: dict[str, object] = {
        "BASE_URL": "http://localhost:8085",
        "mural_config": _mural_config(),
        **overrides,
    }
    return AppConfig(**kwargs)  # type: ignore[arg-type]


def test_no_dev_auth_bypass_fields_remain_on_app_config() -> None:
    """Regression guard: the old DEV_AUTH_ENABLED/DEV_AUTH_JWT_SECRET bypass
    mechanism must not come back. See tests/unit/auth/test_no_bypass.py for
    the repo-wide version of this check.
    """
    assert "dev_auth_enabled" not in AppConfig.model_fields
    assert "dev_auth_jwt_secret" not in AppConfig.model_fields


def test_identity_config_defaults() -> None:
    cfg = _make_config()

    assert cfg.identity_config.rest_auth_mode == "trusted"
    assert cfg.identity_config.trusted_user_header == "X-User-Id"
    assert cfg.identity_config.token_prefix == "mmcp_"
    assert cfg.identity_config.default_ttl_days == 90
    assert cfg.identity_config.max_ttl_days == 365


def test_identity_config_overridable() -> None:
    cfg = _make_config(
        identity_config=IdentityConfig.model_construct(rest_auth_mode="token")
    )

    assert cfg.identity_config.rest_auth_mode == "token"


def test_server_name_defaults_to_mural_mcp() -> None:
    cfg = _make_config()

    assert cfg.server_name == "mural-mcp"
