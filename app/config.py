from typing import Annotated

import pydantic
import pydantic_settings
from pydantic_settings import NoDecode


class MuralConfig(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(env_file=".env", extra="ignore")
    api_base: str = pydantic.Field("https://app.mural.co/api", alias="MURAL_API_BASE")
    client_id: str = pydantic.Field(..., alias="MURAL_CLIENT_ID")
    client_secret: pydantic.SecretStr = pydantic.Field(..., alias="MURAL_CLIENT_SECRET")
    callback_path: str = pydantic.Field(..., alias="MURAL_CALLBACK_PATH")


class IdentityConfig(pydantic_settings.BaseSettings):
    """Personal-access-token identity: how this server verifies its own
    minted tokens and mints new ones. See app/identity/ and
    app/infra/rest/token_router.py.
    """

    model_config = pydantic_settings.SettingsConfigDict(env_file=".env", extra="ignore")

    rest_auth_mode: str = pydantic.Field("trusted", alias="REST_AUTH_MODE")
    trusted_user_header: str = pydantic.Field("X-User-Id", alias="TRUSTED_USER_HEADER")


class AppConfig(pydantic_settings.BaseSettings):
    # extra="ignore" (not "forbid"): pydantic-settings' env source scans the whole
    # process environment, not just this model's declared fields, so "forbid" would
    # hard-fail on any unrelated var a real deployment sets (AWS_*, OTEL_*, ...).
    model_config = pydantic_settings.SettingsConfigDict(env_file=".env", extra="ignore")
    python_env: str | None = None
    host: str = "127.0.0.1"
    port: int = 8086
    log_config: str | None = None
    mongo_uri: str | None = None
    mongo_database: str = "mural-mcp"
    mongo_truststore: str = "TRUSTSTORE_CDP_ROOT_CA"
    aws_endpoint_url: str | None = None
    http_proxy: pydantic.HttpUrl | None = None
    tracing_header: str = "x-cdp-request-id"
    base_url: pydantic.HttpUrl = pydantic.Field(..., alias="BASE_URL")
    server_name: str = pydantic.Field("mural-mcp", alias="SERVER_NAME")

    # Comma-separated Mural board (mural) ids any authenticated user may read.
    # This is the baseline access policy: a board not listed here is denied
    # (unless SELF_SERVICE_ACCESS_ENABLED and the user holds an approved
    # request for it). "*" allows every board -- local development only.
    allowed_board_ids: Annotated[list[str], NoDecode] = pydantic.Field(
        default_factory=list, alias="ALLOWED_BOARD_IDS"
    )

    # Feature flags, both off by default. Self-service access mounts the
    # /approvals (request access) and /admin (IAO review) routes and lets an
    # approved request grant board access on top of ALLOWED_BOARD_IDS.
    # Data-handling upload additionally requires the approver to record the
    # data-handling form and risk-assessment references; it has no effect
    # unless self-service access is on.
    self_service_access_enabled: bool = pydantic.Field(
        False, alias="SELF_SERVICE_ACCESS_ENABLED"
    )
    data_handling_upload_enabled: bool = pydantic.Field(
        False, alias="DATA_HANDLING_UPLOAD_ENABLED"
    )

    @pydantic.field_validator("allowed_board_ids", mode="before")
    @classmethod
    def _split_board_ids(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    mural_config: MuralConfig = pydantic.Field(default_factory=MuralConfig)  # type: ignore
    identity_config: IdentityConfig = pydantic.Field(default_factory=IdentityConfig)  # type: ignore
