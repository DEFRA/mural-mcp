import pytest

from app.common import http_client
from app.integration.mural.board import registry
from app.integration.mural.board.renderers import msx
from app.integration.mural.board.widgets import builder, nodes


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_widgets_and_render_msx(vcr, fake_config) -> None:
    """Test fetching widgets from Mural API and rendering to MSX, following pagination."""
    with vcr.use_cassette("mural_get_widgets.yaml"):
        api_base = fake_config.mural_config.api_base.rstrip("/")
        url: str | None = f"{api_base}/public/v1/murals/test-mural-id/widgets"
        all_widgets: list = []
        async with http_client.create_async_client(
            tracing_header=fake_config.tracing_header,
            trace_id="test-trace",
        ) as client:
            while url:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                page = data.get("value", data) if isinstance(data, dict) else data
                all_widgets.extend(page)
                url = data.get("next") if isinstance(data, dict) else None

    # Page 1 has 5 widgets, page 2 has 1 — assert all 6 are collected.
    assert len(all_widgets) == 6
    widget_ids = {w["id"] for w in all_widgets}
    assert "5-1775856415592" in widget_ids  # comment widget from page 2

    parsed = nodes.parse_widgets(all_widgets)
    assert len(parsed) == 6

    tree = builder.WidgetTree.build(parsed)
    assert tree.nodes
    assert tree.adjacency

    msx_output = msx.render_msx(tree, registry.build_default_registry())
    assert isinstance(msx_output, str)
    assert "5-1775856415592" in msx_output  # page-2 widget appears in output
