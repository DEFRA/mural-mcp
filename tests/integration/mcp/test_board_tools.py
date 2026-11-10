"""Behavioural tests for the MCP tool surface (app/infra/mcp/tools.py),
driven through mcp_client -- real transport auth, real dishka-built
Principal, real BoardService. One happy path per tool asserting real MSX
content (not `isinstance(result, str)`), plus the error envelopes as an
MCP client actually sees them: `result.is_error` and the message in
`result.content[0].text`, not just an exception type on a direct call.
"""

import base64
import datetime
import io
import json
import re

import httpx2
import pytest
from PIL import Image

from app.integration.mural import models
from tests.fixtures import mural
from tests.support.app import mcp_client

_EMPTY_WIDGETS = httpx2.Response(200, json={"value": []})


class TestHappyPaths:
    async def test_get_board_summary_returns_the_rendered_summary(self):
        async with mcp_client(mural_token="mural-tok", responses=[_EMPTY_WIDGETS]) as (
            client,
            _overrides,
            _user_id,
        ):
            result = await client.call_tool(
                "get_board_summary", {"mural_id": "mural-abc"}
            )

        assert (
            result.content[0].text
            == '<BoardSummary mural_id="mural-abc">\n\n</BoardSummary>'
        )

    async def test_get_connections_returns_the_rendered_connections(self):
        async with mcp_client(mural_token="mural-tok", responses=[_EMPTY_WIDGETS]) as (
            client,
            _overrides,
            _user_id,
        ):
            result = await client.call_tool(
                "get_connections", {"mural_id": "mural-abc", "widget_id": "widget-1"}
            )

        assert result.content[0].text == '<Connections widget_id="widget-1"/>'

    async def test_find_widgets_with_no_match_returns_a_message(self):
        async with mcp_client(mural_token="mural-tok", responses=[_EMPTY_WIDGETS]) as (
            client,
            _overrides,
            _user_id,
        ):
            result = await client.call_tool(
                "find_widgets", {"mural_id": "mural-abc", "query": "nonexistent"}
            )

        assert result.content[0].text == "No widgets matched."

    async def test_find_widgets_with_no_query_or_type_asks_for_one(self):
        """Not a ToolError -- the tool returns guidance as its result,
        since this is a caller mistake the model can self-correct from."""
        async with mcp_client(mural_token="mural-tok", responses=[]) as (
            client,
            _overrides,
            _user_id,
        ):
            result = await client.call_tool("find_widgets", {"mural_id": "mural-abc"})

        assert result.content[0].text == "Provide at least one of: query, widget_type."


class TestErrorEnvelopes:
    async def test_asking_for_a_board_without_a_mural_token_explains_how_to_connect(
        self,
    ):
        async with mcp_client(responses=[]) as (client, _overrides, _user_id):
            result = await client.call_tool(
                "get_board_summary", {"mural_id": "mural-abc"}, raise_on_error=False
            )

        assert result.is_error
        assert "connect your Mural account" in result.content[0].text

    async def test_asking_for_an_unknown_region_explains_it_was_not_found(self):
        """Not an area (404 on the single-widget lookup), so the whole board is
        searched before giving up."""
        async with mcp_client(
            mural_token="mural-tok", responses=[httpx2.Response(404), _EMPTY_WIDGETS]
        ) as (
            client,
            _overrides,
            _user_id,
        ):
            result = await client.call_tool(
                "get_region",
                {"mural_id": "mural-abc", "region_id": "no-such-region"},
                raise_on_error=False,
            )

        assert result.is_error
        assert "not found" in result.content[0].text.lower()

    async def test_a_board_that_cannot_be_read_gives_a_plain_error(self):
        unreadable = httpx2.Response(200, json={"value": [{"type": "sticky note"}]})
        async with mcp_client(mural_token="mural-tok", responses=[unreadable]) as (
            client,
            _overrides,
            _user_id,
        ):
            result = await client.call_tool(
                "get_board_summary", {"mural_id": "mural-abc"}, raise_on_error=False
            )

        assert result.is_error
        assert result.content[0].text == "Board could not be read."

    async def test_a_mural_api_failure_surfaces_the_status_code(self):
        async with mcp_client(
            mural_token="mural-tok", responses=[httpx2.Response(500)]
        ) as (client, _overrides, _user_id):
            result = await client.call_tool(
                "get_board_summary", {"mural_id": "mural-abc"}, raise_on_error=False
            )

        assert result.is_error
        assert "500" in result.content[0].text

    async def test_a_board_the_reviewer_has_not_approved_is_forbidden(self):
        """The env allow list denies a board it does not name -- and with
        self-service access off there is no request store to fall back on."""
        async with mcp_client(
            mural_token="mural-tok", responses=[], allowed_board_ids=["other-board"]
        ) as (client, _overrides, _user_id):
            result = await client.call_tool(
                "get_board_summary", {"mural_id": "mural-abc"}, raise_on_error=False
            )

        assert result.is_error

    async def test_an_approved_request_grants_a_board_when_self_service_is_on(self):
        async with mcp_client(
            mural_token="mural-tok",
            responses=[_EMPTY_WIDGETS],
            allowed_board_ids=["other-board"],
            self_service_access_enabled=True,
        ) as (client, overrides, user_id):
            await overrides.access_requests.create(
                models.BoardAccessRequest(
                    id="req-1",
                    user_id=user_id,
                    board_id="mural-abc",
                    reason="why",
                    iao="owner@x.com",
                    status=models.AccessRequestStatus.APPROVED,
                    created_at=datetime.datetime.now(datetime.UTC),
                )
            )

            result = await client.call_tool(
                "get_board_summary", {"mural_id": "mural-abc"}
            )

        assert "BoardSummary" in result.content[0].text


def _png_response() -> httpx2.Response:
    out = io.BytesIO()
    Image.new("RGB", (400, 200), (1, 2, 3)).save(out, format="PNG")
    return httpx2.Response(
        200, content=out.getvalue(), headers={"content-type": "image/png"}
    )


def _widget_response(widget: dict) -> httpx2.Response:
    return httpx2.Response(200, json={"value": widget})


class TestGetImage:
    async def test_returns_a_label_then_the_image(self):
        async with mcp_client(
            mural_token="mural-tok",
            responses=[
                _widget_response(mural.image("img-1", caption="Draft")),
                _png_response(),
            ],
        ) as (client, _overrides, _user_id):
            result = await client.call_tool(
                "get_image", {"mural_id": "mural-abc", "widget_id": "img-1"}
            )

        label, picture = result.content
        assert label.type == "text"
        assert label.text.startswith('<Image id="img-1"')
        assert "Draft" in label.text
        assert "sig=" not in label.text
        assert picture.type == "image"
        assert picture.mime_type == "image/png"
        assert Image.open(io.BytesIO(base64.b64decode(picture.data))).size == (400, 200)

    async def test_full_size_is_accepted(self):
        async with mcp_client(
            mural_token="mural-tok",
            responses=[_widget_response(mural.image("img-1")), _png_response()],
        ) as (client, _overrides, _user_id):
            result = await client.call_tool(
                "get_image",
                {"mural_id": "mural-abc", "widget_id": "img-1", "size": "full"},
            )

        assert not result.is_error

    @pytest.mark.parametrize(
        ("responses", "expected"),
        [
            ([httpx2.Response(404)], "not found"),
            ([_widget_response(mural.sticky("img-1"))], "not an image"),
            (
                [_widget_response(mural.image("img-1", url=None))],
                "restricted on this board",
            ),
            (
                [_widget_response(mural.image("img-1", url="https://evil.test/x"))],
                "evil.test",
            ),
            (
                [_widget_response(mural.image("img-1")), httpx2.Response(403)],
                "may have expired",
            ),
        ],
        ids=["missing", "not-an-image", "restricted", "other-host", "expired"],
    )
    async def test_failures_are_plain_errors(self, responses, expected):
        async with mcp_client(mural_token="mural-tok", responses=responses) as (
            client,
            _overrides,
            _user_id,
        ):
            result = await client.call_tool(
                "get_image",
                {"mural_id": "mural-abc", "widget_id": "img-1"},
                raise_on_error=False,
            )

        assert result.is_error
        assert expected in result.content[0].text
        assert "sig=" not in result.content[0].text

    async def test_a_board_the_user_may_not_read_is_forbidden(self):
        async with mcp_client(
            mural_token="mural-tok", responses=[], allowed_board_ids=["other-board"]
        ) as (client, _overrides, _user_id):
            result = await client.call_tool(
                "get_image",
                {"mural_id": "mural-abc", "widget_id": "img-1"},
                raise_on_error=False,
            )

        assert result.is_error


def _area_with_notes(count: int, text_size: int) -> list[httpx2.Response]:
    area = mural.area("a1", "Big area")
    notes = [
        mural.sticky(f"s{i}", text="x" * text_size, parent_id="a1")
        for i in range(count)
    ]
    return [
        httpx2.Response(200, json={"value": area}),
        httpx2.Response(200, json={"value": notes}),
    ]


class TestPagedOutput:
    async def test_get_region_returns_msx_then_paging_with_structured_content(self):
        async with mcp_client(
            mural_token="mural-tok", responses=_area_with_notes(3, 10)
        ) as (client, _overrides, _user_id):
            result = await client.call_tool(
                "get_region", {"mural_id": "mural-abc", "region_id": "a1"}
            )

        msx_block, page_block = result.content
        assert msx_block.text.startswith('<Area id="a1"')
        assert "next_offset" not in msx_block.text
        assert json.loads(page_block.text) == result.structured_content
        assert result.structured_content == {
            "shown": 3,
            "total": 3,
            "offset": 0,
            "next_offset": None,
            "child_regions": [],
        }

    async def test_an_agent_following_next_offset_gets_every_widget_once(self):
        responses: list[httpx2.Response] = []
        for _ in range(10):
            responses += _area_with_notes(60, 3_000)

        seen: list[str] = []
        calls = 0
        async with mcp_client(mural_token="mural-tok", responses=responses) as (
            client,
            _overrides,
            _user_id,
        ):
            offset = 0
            while offset is not None:
                result = await client.call_tool(
                    "get_region",
                    {"mural_id": "mural-abc", "region_id": "a1", "offset": offset},
                )
                seen += re.findall(r'<StickyNote id="(s\d+)"', result.content[0].text)
                offset = result.structured_content["next_offset"]
                calls += 1

        assert calls > 1
        assert seen == [f"s{i}" for i in range(60)]

    async def test_find_widgets_reports_paging_even_with_no_matches(self):
        async with mcp_client(mural_token="mural-tok", responses=[_EMPTY_WIDGETS]) as (
            client,
            _overrides,
            _user_id,
        ):
            result = await client.call_tool(
                "find_widgets", {"mural_id": "mural-abc", "query": "nothing"}
            )

        assert result.content[0].text == "No widgets matched."
        assert result.structured_content["total"] == 0
        assert result.structured_content["next_offset"] is None

    async def test_a_negative_offset_is_rejected(self):
        async with mcp_client(mural_token="mural-tok", responses=[]) as (
            client,
            _overrides,
            _user_id,
        ):
            result = await client.call_tool(
                "get_region",
                {"mural_id": "mural-abc", "region_id": "a1", "offset": -1},
                raise_on_error=False,
            )

        assert result.is_error


class TestFindWidgetsArguments:
    async def test_an_unknown_widget_type_is_rejected_before_any_fetch(self):
        async with mcp_client(mural_token="mural-tok", responses=[]) as (
            client,
            overrides,
            _user_id,
        ):
            result = await client.call_tool(
                "find_widgets",
                {"mural_id": "mural-abc", "widget_type": "sticky"},
                raise_on_error=False,
            )

        assert result.is_error
        assert overrides.transport.requests == []
