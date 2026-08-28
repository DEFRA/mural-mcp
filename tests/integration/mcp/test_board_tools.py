"""Behavioural tests for the MCP tool surface (app/infra/mcp/tools.py),
driven through mcp_client -- real transport auth, real dishka-built
Principal, real BoardService. One happy path per tool asserting real MSX
content (not `isinstance(result, str)`), plus the error envelopes as an
MCP client actually sees them: `result.is_error` and the message in
`result.content[0].text`, not just an exception type on a direct call.
"""

import httpx

from tests.support.app import mcp_client

_EMPTY_WIDGETS = httpx.Response(200, json={"value": []})


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
        async with mcp_client(mural_token="mural-tok", responses=[_EMPTY_WIDGETS]) as (
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

    async def test_a_mural_api_failure_surfaces_the_status_code(self):
        async with mcp_client(
            mural_token="mural-tok", responses=[httpx.Response(500)]
        ) as (client, _overrides, _user_id):
            result = await client.call_tool(
                "get_board_summary", {"mural_id": "mural-abc"}, raise_on_error=False
            )

        assert result.is_error
        assert "500" in result.content[0].text

    async def test_a_board_the_reviewer_has_not_approved_is_forbidden(self):
        """AllowListBoardGuard denies when there is no approved request for
        this user and board -- an empty access-requests store already
        proves that, with no need for a bespoke always-deny fake."""
        async with mcp_client(
            mural_token="mural-tok", responses=[], resource_guard_mode="allow_list"
        ) as (client, _overrides, _user_id):
            result = await client.call_tool(
                "get_board_summary", {"mural_id": "mural-abc"}, raise_on_error=False
            )

        assert result.is_error
