import httpx
import pytest

from app.mural.board import registry as widget_registry
from app.mural.board import service as board_service
from app.mural.board.renderers import msx as widget_msx
from app.mural.board.summary import renderer as summary_renderer
from app.mural.connectivity import exceptions
from tests.fakes import fake_oauth_client, httpx_helpers

_REG = widget_registry.build_default_registry()
_RENDERER = widget_msx.WidgetMsxRenderer(_REG)
_SUMMARY_RENDERER = summary_renderer.SummaryMsxRenderer(_REG)


@pytest.fixture
def make_service(fake_config):
    """Build a BoardService with fakes and a real httpx client over MockTransport."""

    def _factory(
        *,
        responses: list[httpx.Response],
        oauth_token: str | None = "valid-token",
    ) -> tuple[board_service.BoardService, httpx_helpers.MockTransport]:
        client, transport = httpx_helpers.make_mock_client(responses)
        oauth = fake_oauth_client.FakeOAuthClient(oauth_token)
        service = board_service.BoardService(
            config=fake_config,
            client=client,
            oauth=oauth,
            renderer=_RENDERER,
            summary_renderer=_SUMMARY_RENDERER,
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


@pytest.mark.asyncio
async def test_load_raises_when_user_has_no_token(make_service):
    service, _ = make_service(responses=[], oauth_token=None)
    with pytest.raises(exceptions.MuralTokenError):
        await service._load("user-123", "mural-abc")


@pytest.mark.asyncio
async def test_load_stops_when_next_token_absent(make_service):
    service, transport = make_service(
        responses=[httpx.Response(200, json={"value": [], "next": None})]
    )
    await service._load("user-123", "mural-abc")
    assert len(transport.requests) == 1


@pytest.mark.asyncio
async def test_load_follows_absolute_next_url(make_service):
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
    await service._load("user-123", "mural-abc")
    assert len(transport.requests) == 2
    assert (
        str(transport.requests[1].url)
        == "https://api.example.com/public/v1/murals/mural-abc/widgets?page=2"
    )


@pytest.mark.asyncio
async def test_load_uses_next_token_as_query_param(make_service):
    service, transport = make_service(
        responses=[
            httpx.Response(200, json={"value": [], "next": "opaque-token-xyz"}),
            httpx.Response(200, json={"value": [], "next": None}),
        ]
    )
    await service._load("user-123", "mural-abc")
    assert len(transport.requests) == 2
    assert transport.requests[1].url.params["next"] == "opaque-token-xyz"
    assert (
        str(transport.requests[1].url).split("?")[0]
        == "https://app.mural.co/api/public/v1/murals/mural-abc/widgets"
    )


@pytest.mark.asyncio
async def test_load_raises_on_http_error(make_service):
    service, _ = make_service(responses=[httpx.Response(500)])
    with pytest.raises(httpx.HTTPStatusError):
        await service._load("user-123", "mural-abc")


def test_resolve_next_returns_none_when_no_next_token():
    result = board_service.BoardService._resolve_next(
        {"value": []}, "https://example.com/widgets"
    )
    assert result is None


def test_resolve_next_returns_url_for_absolute_next():
    result = board_service.BoardService._resolve_next(
        {"next": "https://example.com/page2"}, "https://example.com/widgets"
    )
    assert result == ("https://example.com/page2", None)


def test_resolve_next_returns_base_url_with_token_for_relative_next():
    result = board_service.BoardService._resolve_next(
        {"next": "page-2-token"}, "https://example.com/widgets"
    )
    assert result == ("https://example.com/widgets", {"next": "page-2-token"})


def test_resolve_next_returns_none_when_data_not_dict():
    result = board_service.BoardService._resolve_next(
        [{"id": "w1"}], "https://example.com/widgets"
    )
    assert result is None


@pytest.mark.asyncio
async def test_fetch_summary_raises_when_no_token(make_service):
    service, _ = make_service(responses=[], oauth_token=None)
    with pytest.raises(exceptions.MuralTokenError):
        await service.fetch_summary("user-123", "mural-abc")


@pytest.mark.asyncio
async def test_fetch_summary_returns_region_for_area_widget(make_service):
    area = _area("a1", "Sprint Review", x=10, y=20, w=600, h=400)
    note = _sticky("sn1", text="Note 1", parent_id="a1")
    service, _ = make_service(
        responses=[httpx.Response(200, json={"value": [area, note]})]
    )
    result = await service.fetch_summary("user-123", "mural-abc")
    assert result is not None
    assert '<Region id="a1"' in result
    assert 'label="Sprint Review"' in result
    assert 'count="1"' in result
    assert 'x="10' in result
    assert 'width="600' in result


@pytest.mark.asyncio
async def test_fetch_summary_omits_lone_root_widgets(make_service):
    note = _sticky("sn1", text="Lone note")
    service, _ = make_service(responses=[httpx.Response(200, json={"value": [note]})])
    result = await service.fetch_summary("user-123", "mural-abc")
    assert result is not None
    assert "<Region" not in result


@pytest.mark.asyncio
async def test_fetch_summary_empty_board(make_service):
    service, _ = make_service(responses=[httpx.Response(200, json={"value": []})])
    result = await service.fetch_summary("user-123", "mural-abc")
    assert result is not None
    assert "BoardSummary" in result
    assert "<Region" not in result


@pytest.mark.asyncio
async def test_fetch_region_raises_when_no_token(make_service):
    service, _ = make_service(responses=[], oauth_token=None)
    with pytest.raises(exceptions.MuralTokenError):
        await service.fetch_region("user-123", "mural-abc", "a1")


@pytest.mark.asyncio
async def test_fetch_region_unknown_id_returns_error_string(make_service):
    service, _ = make_service(responses=[httpx.Response(200, json={"value": []})])
    result = await service.fetch_region("user-123", "mural-abc", "no-such-id")
    assert result is not None
    assert "not found" in result.lower()


@pytest.mark.asyncio
async def test_fetch_region_renders_area_subtree(make_service):
    area = _area("a1", "Design Sprint")
    note = _sticky("sn1", text="Hello", parent_id="a1")
    service, _ = make_service(
        responses=[httpx.Response(200, json={"value": [area, note]})]
    )
    result = await service.fetch_region("user-123", "mural-abc", "a1")
    assert result is not None
    assert "<Area" in result
    assert "<StickyNote" in result
    assert "Hello" in result


@pytest.mark.asyncio
async def test_fetch_connections_raises_when_no_token(make_service):
    service, _ = make_service(responses=[], oauth_token=None)
    with pytest.raises(exceptions.MuralTokenError):
        await service.fetch_connections("user-123", "mural-abc", "w1")


@pytest.mark.asyncio
async def test_fetch_connections_no_arrows_returns_empty_tag(make_service):
    note = _sticky("sn1")
    service, _ = make_service(responses=[httpx.Response(200, json={"value": [note]})])
    result = await service.fetch_connections("user-123", "mural-abc", "sn1")
    assert result is not None
    assert result == '<Connections widget_id="sn1"/>'


@pytest.mark.asyncio
async def test_fetch_connections_outgoing(make_service):
    src = _sticky("src")
    dst = _sticky("dst")
    arrow = _arrow("arr1", start_ref="src", end_ref="dst")
    service, _ = make_service(
        responses=[httpx.Response(200, json={"value": [src, dst, arrow]})]
    )
    result = await service.fetch_connections("user-123", "mural-abc", "src")
    assert result is not None
    assert 'direction="outgoing"' in result
    assert 'target_id="dst"' in result
    assert 'arrow_id="arr1"' in result


@pytest.mark.asyncio
async def test_fetch_connections_incoming(make_service):
    src = _sticky("src")
    dst = _sticky("dst")
    arrow = _arrow("arr1", start_ref="src", end_ref="dst")
    service, _ = make_service(
        responses=[httpx.Response(200, json={"value": [src, dst, arrow]})]
    )
    result = await service.fetch_connections("user-123", "mural-abc", "dst")
    assert result is not None
    assert 'direction="incoming"' in result
    assert 'source_id="src"' in result


@pytest.mark.asyncio
async def test_search_widgets_raises_when_no_token(make_service):
    service, _ = make_service(responses=[], oauth_token=None)
    with pytest.raises(exceptions.MuralTokenError):
        await service.search_widgets("user-123", "mural-abc", "hello", None)


@pytest.mark.asyncio
async def test_search_widgets_by_text_returns_matching(make_service):
    note1 = _sticky("sn1", text="Hello World")
    note2 = _sticky("sn2", text="Something else")
    service, _ = make_service(
        responses=[httpx.Response(200, json={"value": [note1, note2]})]
    )
    result = await service.search_widgets("user-123", "mural-abc", "hello", None)
    assert result is not None
    assert "sn1" in result
    assert "sn2" not in result


@pytest.mark.asyncio
async def test_search_widgets_by_type(make_service):
    note = _sticky("sn1", text="A sticky")
    area = _area("a1", "An area")
    service, _ = make_service(
        responses=[httpx.Response(200, json={"value": [note, area]})]
    )
    result = await service.search_widgets("user-123", "mural-abc", None, "area")
    assert result is not None
    assert "a1" in result
    assert "sn1" not in result


@pytest.mark.asyncio
async def test_search_widgets_no_match_returns_message(make_service):
    note = _sticky("sn1", text="Nothing relevant")
    service, _ = make_service(responses=[httpx.Response(200, json={"value": [note]})])
    result = await service.search_widgets(
        "user-123", "mural-abc", "xyz-not-found", None
    )
    assert result == "No widgets matched."
