import httpx
import pytest

from app.integration.linking import exceptions
from app.integration.mural import guard as guard_module
from app.integration.mural import service as board_service
from app.integration.mural.board import exceptions as board_exceptions
from app.integration.mural.board import registry as widget_registry
from app.integration.mural.board.renderers import msx as widget_msx
from app.integration.mural.board.summary import renderer as summary_renderer
from tests.fakes import (
    fake_oauth_client,
    httpx_helpers,
    in_memory_board_access_request_store,
)

_REG = widget_registry.build_default_registry()
_RENDERER = widget_msx.WidgetMsxRenderer(_REG)
_SUMMARY_RENDERER = summary_renderer.SummaryMsxRenderer(_REG)


@pytest.fixture
def make_service(fake_config):
    """Build a BoardService with fakes and a real httpx client over MockTransport."""

    def _factory(
        *,
        responses: list[httpx.Response | Exception],
        oauth_token: str | None = "valid-token",
        guard: guard_module.BoardGuard | None = None,
    ) -> tuple[board_service.BoardService, httpx_helpers.MockTransport]:
        client, transport = httpx_helpers.make_mock_client(responses)
        oauth = fake_oauth_client.FakeOAuthClient(oauth_token)
        service = board_service.BoardService(
            config=fake_config,
            client=client,
            oauth=oauth,
            renderer=_RENDERER,
            summary_renderer=_SUMMARY_RENDERER,
            guard=guard or guard_module.AllowAllBoardGuard(),
        )
        return service, transport

    return _factory


def _user_ref(uid: str = "u1") -> dict:
    return {"id": uid}


def _base_widget(widget_id: str, widget_type: str, **extra) -> dict:
    return {
        "id": widget_id,
        "type": widget_type,
        "x": 0.0,
        "y": 0.0,
        "width": 100.0,
        "height": 100.0,
        "rotation": 0.0,
        "stackingOrder": 0,
        "presentationIndex": -1,
        "instruction": "",
        "hidden": False,
        "hideEditor": False,
        "hideOwner": False,
        "invisible": False,
        "locked": False,
        "lockedByFacilitator": False,
        "createdBy": _user_ref(),
        "createdOn": 0,
        "updatedBy": _user_ref(),
        "updatedOn": 0,
        "contentEditedBy": _user_ref(),
        "contentEditedOn": 0,
        **extra,
    }


def _sticky(
    widget_id: str, text: str = "", font_size: float = 14, parent_id=None
) -> dict:
    return _base_widget(
        widget_id,
        "sticky note",
        title=text or widget_id,
        shape="rectangle",
        parentId=parent_id,
        style={
            "backgroundColor": "#FFFF00FF",
            "bold": False,
            "border": False,
            "italic": False,
            "underline": False,
            "strike": False,
            "font": "proxima-nova",
            "fontSize": font_size,
            "textAlign": "left",
        },
        text=text,
    )


def _area(
    widget_id: str,
    title: str,
    x: float = 0,
    y: float = 0,
    w: float = 500,
    h: float = 400,
) -> dict:
    return _base_widget(
        widget_id,
        "area",
        x=x,
        y=y,
        width=w,
        height=h,
        title=title,
        layout="free",
        showTitle=True,
        style={
            "backgroundColor": "#FFFFFF33",
            "borderColor": "#000000FF",
            "borderStyle": "dashed",
            "borderWidth": 1,
            "titleFontSize": 24.0,
        },
    )


def _arrow(
    widget_id: str, start_ref: str | None = None, end_ref: str | None = None
) -> dict:
    d = _base_widget(
        widget_id,
        "arrow",
        title="",
        arrowType="straight",
        tip="single",
        stackable=False,
        points=[{"x": 0, "y": 0}, {"x": 10, "y": 10}],
        style={"strokeColor": "#000000FF", "strokeStyle": "solid", "strokeWidth": 2},
    )
    if start_ref:
        d["startRefId"] = start_ref
    if end_ref:
        d["endRefId"] = end_ref
    return d


class TestFetchSummary:
    async def test_stops_paginating_when_next_token_absent(self, make_service):
        service, transport = make_service(
            responses=[httpx.Response(200, json={"value": [], "next": None})]
        )
        await service.fetch_summary("user-123", "mural-abc")
        assert len(transport.requests) == 1

    async def test_every_mural_request_carries_the_users_access_token(
        self, make_service
    ):
        service, transport = make_service(
            responses=[
                httpx.Response(200, json={"value": [], "next": "opaque-token-xyz"}),
                httpx.Response(200, json={"value": [], "next": None}),
            ],
            oauth_token="mural-token-abc",
        )
        await service.fetch_summary("user-123", "mural-abc")

        assert len(transport.requests) == 2
        assert (
            transport.requests[0].headers["Authorization"] == "Bearer mural-token-abc"
        )
        assert (
            transport.requests[1].headers["Authorization"] == "Bearer mural-token-abc"
        )

    async def test_follows_an_absolute_next_url(self, make_service):
        service, transport = make_service(
            responses=[
                httpx.Response(
                    200,
                    json={
                        "value": [],
                        "next": "https://api.example.com/public/v1/murals/mural-abc/widgets?page=2",
                    },
                ),
                httpx.Response(200, json={"value": [], "next": None}),
            ]
        )
        await service.fetch_summary("user-123", "mural-abc")
        assert len(transport.requests) == 2
        assert (
            str(transport.requests[1].url)
            == "https://api.example.com/public/v1/murals/mural-abc/widgets?page=2"
        )

    async def test_uses_an_opaque_next_token_as_a_query_param(self, make_service):
        service, transport = make_service(
            responses=[
                httpx.Response(200, json={"value": [], "next": "opaque-token-xyz"}),
                httpx.Response(200, json={"value": [], "next": None}),
            ]
        )
        await service.fetch_summary("user-123", "mural-abc")
        assert len(transport.requests) == 2
        assert transport.requests[1].url.params["next"] == "opaque-token-xyz"
        assert (
            str(transport.requests[1].url).split("?")[0]
            == "https://app.mural.co/api/public/v1/murals/mural-abc/widgets"
        )

    async def test_wraps_a_mural_http_error(self, make_service):
        """A non-2xx from the Mural API must be wrapped in MuralApiError,
        not leak the raw httpx.HTTPStatusError (which would expose vendor
        URLs/response bodies to REST clients and LLM tool callers).
        """
        service, _ = make_service(responses=[httpx.Response(500)])
        with pytest.raises(exceptions.MuralApiError) as exc_info:
            await service.fetch_summary("user-123", "mural-abc")
        assert exc_info.value.status_code == 500

    async def test_raises_when_no_token(self, make_service):
        service, _ = make_service(responses=[], oauth_token=None)
        with pytest.raises(exceptions.MuralTokenError):
            await service.fetch_summary("user-123", "mural-abc")

    async def test_wraps_an_unreachable_mural(self, make_service):
        """A connection failure (Mural down, DNS failure, timeout) must be
        wrapped in MuralUnavailableError, not left as a raw httpx error."""
        service, _ = make_service(responses=[httpx.ConnectError("Connection refused")])
        with pytest.raises(exceptions.MuralUnavailableError):
            await service.fetch_summary("user-123", "mural-abc")

    async def test_returns_region_for_area_widget(self, make_service):
        area = _area("a1", "Sprint Review", x=10, y=20, w=600, h=400)
        note = _sticky("sn1", text="Note 1", parent_id="a1")
        service, _ = make_service(
            responses=[httpx.Response(200, json={"value": [area, note]})]
        )
        result = await service.fetch_summary("user-123", "mural-abc")
        assert '<Region id="a1"' in result
        assert 'label="Sprint Review"' in result
        assert 'count="1"' in result
        assert 'x="10' in result
        assert 'width="600' in result

    async def test_omits_lone_root_widgets(self, make_service):
        note = _sticky("sn1", text="Lone note")
        service, _ = make_service(
            responses=[httpx.Response(200, json={"value": [note]})]
        )
        result = await service.fetch_summary("user-123", "mural-abc")
        assert "<Region" not in result

    async def test_empty_board(self, make_service):
        service, _ = make_service(responses=[httpx.Response(200, json={"value": []})])
        result = await service.fetch_summary("user-123", "mural-abc")
        assert "BoardSummary" in result
        assert "<Region" not in result


class TestResolveNext:
    def test_returns_none_when_no_next_token(self):
        result = board_service.BoardService._resolve_next(
            {"value": []}, "https://example.com/widgets"
        )
        assert result is None

    def test_returns_url_for_absolute_next(self):
        result = board_service.BoardService._resolve_next(
            {"next": "https://example.com/page2"}, "https://example.com/widgets"
        )
        assert result == ("https://example.com/page2", None)

    def test_returns_base_url_with_token_for_relative_next(self):
        result = board_service.BoardService._resolve_next(
            {"next": "page-2-token"}, "https://example.com/widgets"
        )
        assert result == ("https://example.com/widgets", {"next": "page-2-token"})

    def test_returns_none_when_data_not_dict(self):
        result = board_service.BoardService._resolve_next(
            [{"id": "w1"}], "https://example.com/widgets"
        )
        assert result is None


class TestFetchRegion:
    async def test_raises_when_no_token(self, make_service):
        service, _ = make_service(responses=[], oauth_token=None)
        with pytest.raises(exceptions.MuralTokenError):
            await service.fetch_region("user-123", "mural-abc", "a1")

    async def test_unknown_id_raises(self, make_service):
        service, _ = make_service(responses=[httpx.Response(200, json={"value": []})])
        with pytest.raises(
            board_exceptions.BoardRegionNotFoundError, match="no-such-id"
        ):
            await service.fetch_region("user-123", "mural-abc", "no-such-id")

    async def test_renders_area_subtree(self, make_service):
        area = _area("a1", "Design Sprint")
        note = _sticky("sn1", text="Hello", parent_id="a1")
        service, _ = make_service(
            responses=[httpx.Response(200, json={"value": [area, note]})]
        )
        result = await service.fetch_region("user-123", "mural-abc", "a1")
        assert "<Area" in result
        assert "<StickyNote" in result
        assert "Hello" in result


class TestFetchConnections:
    async def test_raises_when_no_token(self, make_service):
        service, _ = make_service(responses=[], oauth_token=None)
        with pytest.raises(exceptions.MuralTokenError):
            await service.fetch_connections("user-123", "mural-abc", "w1")

    async def test_no_arrows_returns_empty_tag(self, make_service):
        note = _sticky("sn1")
        service, _ = make_service(
            responses=[httpx.Response(200, json={"value": [note]})]
        )
        result = await service.fetch_connections("user-123", "mural-abc", "sn1")
        assert result == '<Connections widget_id="sn1"/>'

    async def test_outgoing(self, make_service):
        src = _sticky("src")
        dst = _sticky("dst")
        arrow = _arrow("arr1", start_ref="src", end_ref="dst")
        service, _ = make_service(
            responses=[httpx.Response(200, json={"value": [src, dst, arrow]})]
        )
        result = await service.fetch_connections("user-123", "mural-abc", "src")
        assert 'direction="outgoing"' in result
        assert 'target_id="dst"' in result
        assert 'arrow_id="arr1"' in result

    async def test_incoming(self, make_service):
        src = _sticky("src")
        dst = _sticky("dst")
        arrow = _arrow("arr1", start_ref="src", end_ref="dst")
        service, _ = make_service(
            responses=[httpx.Response(200, json={"value": [src, dst, arrow]})]
        )
        result = await service.fetch_connections("user-123", "mural-abc", "dst")
        assert 'direction="incoming"' in result
        assert 'source_id="src"' in result


class TestSearchWidgets:
    async def test_raises_when_no_token(self, make_service):
        service, _ = make_service(responses=[], oauth_token=None)
        with pytest.raises(exceptions.MuralTokenError):
            await service.search_widgets("user-123", "mural-abc", "hello", None)

    async def test_by_text_returns_matching(self, make_service):
        note1 = _sticky("sn1", text="Hello World")
        note2 = _sticky("sn2", text="Something else")
        service, _ = make_service(
            responses=[httpx.Response(200, json={"value": [note1, note2]})]
        )
        result = await service.search_widgets("user-123", "mural-abc", "hello", None)
        assert "sn1" in result
        assert "sn2" not in result

    async def test_by_type(self, make_service):
        note = _sticky("sn1", text="A sticky")
        area = _area("a1", "An area")
        service, _ = make_service(
            responses=[httpx.Response(200, json={"value": [note, area]})]
        )
        result = await service.search_widgets("user-123", "mural-abc", None, "area")
        assert "a1" in result
        assert "sn1" not in result

    async def test_no_match_returns_message(self, make_service):
        note = _sticky("sn1", text="Nothing relevant")
        service, _ = make_service(
            responses=[httpx.Response(200, json={"value": [note]})]
        )
        result = await service.search_widgets(
            "user-123", "mural-abc", "xyz-not-found", None
        )
        assert result == "No widgets matched."


class TestGuardEnforcement:
    @pytest.mark.parametrize(
        "call",
        [
            lambda service: service.fetch_summary("user-123", "mural-abc"),
            lambda service: service.fetch_region("user-123", "mural-abc", "region-1"),
            lambda service: service.fetch_connections(
                "user-123", "mural-abc", "widget-1"
            ),
            lambda service: service.search_widgets("user-123", "mural-abc", "q", None),
        ],
        ids=["fetch_summary", "fetch_region", "fetch_connections", "search_widgets"],
    )
    async def test_a_denied_guard_blocks_every_public_method_before_any_vendor_call(
        self, make_service, call
    ):
        """The guard runs before BoardService talks to Mural at all -- not
        just before it returns data. A denied user's call must not reach
        the vendor, not even for a token refresh (FakeOAuthClient never
        touches the transport either, so any request recorded here would be
        a real bug).
        """
        store = in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()
        guard = guard_module.AllowListBoardGuard(store)
        service, transport = make_service(responses=[], guard=guard)

        with pytest.raises(guard_module.ForbiddenBoardError):
            await call(service)

        assert transport.requests == []
