import pydantic
import pydantic_settings


class MuralConfig(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(env_file=".env", extra="ignore")
    api_base: str = pydantic.Field("https://app.mural.co/api", alias="MURAL_API_BASE")
    authorize_path: str = pydantic.Field(
        "/public/v1/authorization/oauth2/", alias="MURAL_AUTHORIZE_PATH"
    )
    token_path: str = pydantic.Field(
        "/public/v1/authorization/oauth2/token", alias="MURAL_TOKEN_PATH"
    )
    scopes: str = pydantic.Field("murals:read identity:read", alias="MURAL_SCOPES")
    client_id: str = pydantic.Field(..., alias="MURAL_CLIENT_ID")
    client_secret: pydantic.SecretStr = pydantic.Field(..., alias="MURAL_CLIENT_SECRET")
    callback_path: str = pydantic.Field(..., alias="MURAL_CALLBACK_PATH")
    token_collection: str = pydantic.Field(
        "mural_tokens", alias="MURAL_TOKEN_COLLECTION"
    )
    oauth_state_collection: str = pydantic.Field(
        "oauth_states", alias="MURAL_OAUTH_STATE_COLLECTION"
    )


class IdentityConfig(pydantic_settings.BaseSettings):
    """Personal-access-token identity: how this server verifies its own
    minted tokens and mints new ones. See app/identity/ and
    app/infra/rest/token_router.py.
    """

    model_config = pydantic_settings.SettingsConfigDict(env_file=".env", extra="ignore")

    rest_auth_mode: str = pydantic.Field("trusted", alias="REST_AUTH_MODE")
    trusted_user_header: str = pydantic.Field("X-User-Id", alias="TRUSTED_USER_HEADER")

    token_prefix: str = pydantic.Field("mmcp_", alias="IDENTITY_TOKEN_PREFIX")
    default_ttl_days: int = pydantic.Field(90, alias="IDENTITY_DEFAULT_TTL_DAYS")
    max_ttl_days: int = pydantic.Field(365, alias="IDENTITY_MAX_TTL_DAYS")
    last_used_throttle_seconds: int = pydantic.Field(
        300, alias="IDENTITY_LAST_USED_THROTTLE_SECONDS"
    )


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

    # "allow_all" (default) — every board request succeeds; the governance
    # workflow (app/integration/resource/) records requests/decisions but
    # nothing is enforced yet. "allow_list" — BoardService denies access
    # unless an approved BoardAccessRequest exists for the (user, board)
    # pair. Flip only once the admin review workflow has real approvals to
    # check against — flipping first denies all traffic.
    resource_guard_mode: str = pydantic.Field("allow_all", alias="RESOURCE_GUARD_MODE")

    mural_config: MuralConfig = pydantic.Field(default_factory=MuralConfig)  # type: ignore
    identity_config: IdentityConfig = pydantic.Field(default_factory=IdentityConfig)  # type: ignore
