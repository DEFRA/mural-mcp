import pydantic
import pytest

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


class TestAppConfig:
    def test_no_dev_auth_bypass_fields_remain(self) -> None:
        """Regression guard: the old DEV_AUTH_ENABLED/DEV_AUTH_JWT_SECRET
        bypass mechanism must not come back. See
        tests/unit/auth/test_no_bypass.py for the repo-wide version of this
        check.
        """
        assert "dev_auth_enabled" not in AppConfig.model_fields
        assert "dev_auth_jwt_secret" not in AppConfig.model_fields

    def test_server_name_defaults_to_mural_mcp(self) -> None:
        cfg = _make_config()

        assert cfg.server_name == "mural-mcp"


class TestAccessPolicyConfig:
    def test_defaults_are_deny_by_default_with_flags_off(self) -> None:
        cfg = _make_config()

        assert cfg.allowed_board_ids == []
        assert cfg.self_service_access_enabled is False
        assert cfg.data_handling_upload_enabled is False

    def test_allowed_board_ids_come_from_a_comma_separated_env_var(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ALLOWED_BOARD_IDS", "board-1, board-2 ,,board-3")

        cfg = _make_config()

        assert cfg.allowed_board_ids == ["board-1", "board-2", "board-3"]

    def test_flags_come_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SELF_SERVICE_ACCESS_ENABLED", "true")
        monkeypatch.setenv("DATA_HANDLING_UPLOAD_ENABLED", "true")

        cfg = _make_config()

        assert cfg.self_service_access_enabled is True
        assert cfg.data_handling_upload_enabled is True

    def test_the_old_resource_guard_mode_setting_is_gone(self) -> None:
        assert "resource_guard_mode" not in AppConfig.model_fields


class TestIdentityConfig:
    def test_defaults(self) -> None:
        cfg = _make_config()

        assert cfg.identity_config.rest_auth_mode == "trusted"
        assert cfg.identity_config.trusted_user_header == "X-User-Id"

    def test_is_overridable(self) -> None:
        cfg = _make_config(
            identity_config=IdentityConfig.model_construct(rest_auth_mode="token")
        )

        assert cfg.identity_config.rest_auth_mode == "token"
