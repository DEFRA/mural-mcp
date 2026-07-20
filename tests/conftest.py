import os

import dishka
import pydantic
import pytest
import pytest_asyncio
import vcr as vcr_module

from app import config as app_config
from tests.fixtures import di as fixtures_di

# @pytest.fixture(autouse=True, scope="session")
# def _test_env() -> None:
#     """Bootstrap AppConfig for tests that access the singleton directly.

#     Unit tests use fake_config instead; this only matters for app-level and
#     integration tests that reach app_config.config at runtime.
#     """
#     import os

#     os.environ.setdefault("MURAL_CLIENT_ID", "test-client-id")
#     os.environ.setdefault("MURAL_CLIENT_SECRET", "test-secret")
#     os.environ.setdefault("MURAL_CALLBACK_PATH", "/connect/mural/callback")
#     os.environ.setdefault("BASE_URL", "http://localhost:8085")


vcr_instance = vcr_module.VCR(
    cassette_library_dir="tests/cassettes",
    record_mode=os.getenv("VCR_RECORD_MODE", "none"),
    filter_headers=["authorization", "Authorization"],
    match_on=["method", "uri"],
)


@pytest.fixture
def fake_config() -> app_config.AppConfig:
    """Real AppConfig built from fixed test values — no MagicMock, no env var coupling."""
    mural_cfg = app_config.MuralConfig.model_construct(
        api_base="https://app.mural.co/api",
        client_id="test-client-id",
        client_secret=pydantic.SecretStr("test-secret"),
        callback_path="/callback",
    )
    return app_config.AppConfig.model_construct(
        base_url="http://example.com",
        mural_config=mural_cfg,
    )


@pytest.fixture
def vcr() -> vcr_module.VCR:
    """Return the VCR instance for recording/replaying HTTP interactions."""
    return vcr_instance


@pytest_asyncio.fixture
async def test_container() -> dishka.AsyncContainer:
    async with fixtures_di.build_test_container() as container:
        yield container
