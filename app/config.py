import pydantic
import pydantic_settings


class MuralConfig(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict(env_file=".env", extra="ignore")
    api_base: str = pydantic.Field("https://app.mural.co/api", alias="MURAL_API_BASE")
    client_id: str = pydantic.Field(..., alias="MURAL_CLIENT_ID")
    client_secret: pydantic.SecretStr = pydantic.Field(..., alias="MURAL_CLIENT_SECRET")
    callback_path: str = pydantic.Field(..., alias="MURAL_CALLBACK_PATH")


class AppConfig(pydantic_settings.BaseSettings):
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

    mural_config: MuralConfig = pydantic.Field(default_factory=MuralConfig)  # type: ignore
