"""Behavioural tests for the MCP tool surface (app/infra/mcp/tools.py),
driven through mcp_client -- real transport auth, real dishka-built
Principal, real BoardService. One happy path per tool asserting real MSX
content (not `isinstance(result, str)`), plus the error envelopes as an
MCP client actually sees them: `result.is_error` and the message in
`result.content[0].text`, not just an exception type on a direct call.
"""

import datetime

import httpx

from app.integration.mural import models
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
