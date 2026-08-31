"""Drives the real production BoardService against a real recorded Mural
response (see docs/python-testing-standard.md §4.1). An earlier version of
this test reimplemented pagination in the test body -- it asserted its own
loop, not BoardService's, and would have passed with
BoardService._fetch_widgets deleted. The vendor's actual JSON shape only
meets the Pydantic schemas here; everywhere else in the suite runs on the
faster tests/fixtures/mural.py factories.
"""

import pytest

from app.common import http_client
from app.integration.mural import guard as guard_module
from app.integration.mural import service as board_service
from app.integration.mural.board import registry
from app.integration.mural.board.renderers import msx as widget_msx
from app.integration.mural.board.summary import renderer as summary_renderer
from tests.fakes import fake_oauth_client


class TestSearchWidgets:
    @pytest.mark.vcr("mural_get_widgets")
    async def test_pagination_is_followed_so_page_two_widgets_are_included(
        self, fake_config
    ):
        """The cassette's first page carries an absolute `next` URL. If
        BoardService stopped following it, the page-two comment widget would
        silently vanish."""
        reg = registry.build_default_registry()

        async with http_client.create_async_client(
            tracing_header=fake_config.tracing_header,
            trace_id="test-trace",
        ) as client:
            service = board_service.BoardService(
                config=fake_config,
                client=client,
                oauth=fake_oauth_client.FakeOAuthClient("test-token"),
                renderer=widget_msx.WidgetMsxRenderer(reg),
                summary_renderer=summary_renderer.SummaryMsxRenderer(reg),
                guard=guard_module.AllowAllBoardGuard(),
            )

            msx_output = await service.search_widgets(
                "user-123", "test-mural-id", None, None
            )

        assert "5-1775856415592" in msx_output
