import os

import dishka
import pydantic
import pytest
import vcr as vcr_module

from app import config as app_config
from tests.fixtures import di as fixtures_di
from tests.support import vcr_config

pytest_plugins = ["tests.support.mongo"]

vcr_instance = vcr_module.VCR(
    cassette_library_dir="tests/cassettes",
    record_mode=os.getenv("VCR_RECORD_MODE", "none"),
    filter_headers=vcr_config.SENSITIVE_HEADERS,
    filter_post_data_parameters=[
        (p, vcr_config.PLACEHOLDER) for p in vcr_config.SENSITIVE_POST_PARAMS
    ],
    filter_query_parameters=[
        (p, vcr_config.PLACEHOLDER) for p in vcr_config.SENSITIVE_QUERY_PARAMS
    ],
    before_record_response=vcr_config.before_record_response,
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


@pytest.fixture(autouse=True)
def _bind_vcr_cassette(request: pytest.FixtureRequest):
    """Binds a cassette to every @pytest.mark.vcr test, so the marker does
    the work instead of sitting beside a manual `with vcr.use_cassette(...)`
    that can drift from it. `@pytest.mark.vcr("name")` replays
    tests/cassettes/name.yaml; with no argument it defaults to
    `<module>.<test>.yaml` for a test that owns its own recording.
    """
    marker = request.node.get_closest_marker("vcr")
    if marker is None:
        yield
        return

    if marker.args:
        cassette_name = f"{marker.args[0]}.yaml"
    else:
        module_name = request.node.module.__name__.rsplit(".", 1)[-1]
        cassette_name = f"{module_name}.{request.node.name}.yaml"

    with vcr_instance.use_cassette(cassette_name):
        yield


@pytest.fixture
async def test_container() -> dishka.AsyncContainer:
    async with fixtures_di.build_test_container() as container:
        yield container
