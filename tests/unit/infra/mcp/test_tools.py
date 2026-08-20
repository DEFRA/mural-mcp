"""Real coverage for the four MCP tools -- exercised through the actual
dishka_inject.inject wiring (a fake fastmcp.Context + a real Dishka
container), not just their internal logic in isolation. This is the surface
an MCP client actually calls.
"""

import unittest.mock

import dishka
import fastmcp
import httpx
import pytest
from fastmcp.exceptions import ToolError

from app.auth import principal as principal_module
from app.infra.mcp import dishka_inject, tools
from app.integration.mural import guard as guard_module
from app.integration.mural import service as board_service_module
from app.integration.mural.board import registry as widget_registry
from app.integration.mural.board.renderers import msx as widget_msx
from app.integration.mural.board.summary import renderer as summary_renderer
from tests.fakes import (
    fake_oauth_client,
    httpx_helpers,
    in_memory_board_access_request_store,
)

_PRINCIPAL = principal_module.Principal(user_id="usr_test", email="a@example.com")

_REG = widget_registry.build_default_registry()
_RENDERER = widget_msx.WidgetMsxRenderer(_REG)
_SUMMARY_RENDERER = summary_renderer.SummaryMsxRenderer(_REG)


def _make_ctx(container: dishka.AsyncContainer) -> fastmcp.Context:
    ctx = unittest.mock.MagicMock(spec=fastmcp.Context)
    ctx.lifespan_context = {"container": container}
    ctx.request_id = "trace-123"
    ctx.info = unittest.mock.AsyncMock()
    return ctx


class _Provider(dishka.Provider):
    """Everything the four tools need, wired to fakes/real-but-in-memory
    implementations -- only the httpx transport underneath BoardService is
    mocked.
    """

    def __init__(
        self,
        *,
        responses: list[httpx.Response],
        oauth_token: str | None = "valid-mural-token",
        guard: guard_module.BoardGuard | None = None,
    ) -> None:
        super().__init__()
        self._responses = responses
        self._oauth_token = oauth_token
        self._guard = guard or guard_module.AllowAllBoardGuard()

    @dishka.provide(scope=dishka.Scope.APP)
    def provide_principal(self) -> principal_module.Principal:
        return _PRINCIPAL

    @dishka.provide(scope=dishka.Scope.APP)
    def provide_board_service(self) -> board_service_module.BoardService:
        client, _transport = httpx_helpers.make_mock_client(self._responses)
        return board_service_module.BoardService(
            config=unittest.mock.MagicMock(
                mural_config=unittest.mock.MagicMock(
                    api_base="https://app.mural.co/api"
                )
            ),
            client=client,
            oauth=fake_oauth_client.FakeOAuthClient(self._oauth_token),  # type: ignore[arg-type]
            renderer=_RENDERER,
            summary_renderer=_SUMMARY_RENDERER,
            guard=self._guard,
        )


def _build_container(**kwargs: object) -> dishka.AsyncContainer:
    return dishka.make_async_container(
        _Provider(**kwargs),  # type: ignore[arg-type]
        dishka_inject.FastMCPProvider(),
    )


@pytest.mark.asyncio
async def test_get_board_summary_returns_msx() -> None:
    async with _build_container(
        responses=[httpx.Response(200, json={"value": []})]
    ) as c:
        result = await tools.get_board_summary("mural-abc", _make_ctx(c))

    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_get_board_summary_no_token_raises_tool_error() -> None:
    async with _build_container(responses=[], oauth_token=None) as c:
        with pytest.raises(ToolError, match="connect your Mural account"):
            await tools.get_board_summary("mural-abc", _make_ctx(c))


@pytest.mark.asyncio
async def test_get_board_summary_denied_raises_tool_error() -> None:
    # An empty store has no approved request for anyone, so AllowListBoardGuard
    # denies -- no need for a bespoke always-deny fake.
    empty_store = in_memory_board_access_request_store.InMemoryBoardAccessRequestStore()
    guard = guard_module.AllowListBoardGuard(empty_store)
    async with _build_container(responses=[], guard=guard) as c:
        with pytest.raises(ToolError):
            await tools.get_board_summary("mural-abc", _make_ctx(c))


@pytest.mark.asyncio
async def test_get_region_unknown_region_raises_tool_error() -> None:
    async with _build_container(
        responses=[httpx.Response(200, json={"value": []})]
    ) as c:
        with pytest.raises(ToolError, match="not found"):
            await tools.get_region("mural-abc", "no-such-region", _make_ctx(c))


@pytest.mark.asyncio
async def test_get_connections_returns_msx() -> None:
    async with _build_container(
        responses=[httpx.Response(200, json={"value": []})]
    ) as c:
        result = await tools.get_connections("mural-abc", "widget-1", _make_ctx(c))

    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_find_widgets_requires_query_or_type() -> None:
    async with _build_container(responses=[]) as c:
        result = await tools.find_widgets("mural-abc", _make_ctx(c))

    assert result == "Provide at least one of: query, widget_type."


@pytest.mark.asyncio
async def test_find_widgets_no_match_returns_message() -> None:
    async with _build_container(
        responses=[httpx.Response(200, json={"value": []})]
    ) as c:
        result = await tools.find_widgets(
            "mural-abc", _make_ctx(c), query="nonexistent"
        )

    assert result == "No widgets matched."


@pytest.mark.asyncio
async def test_mural_api_error_maps_to_tool_error() -> None:
    async with _build_container(responses=[httpx.Response(500)]) as c:
        with pytest.raises(ToolError, match="status 500"):
            await tools.get_board_summary("mural-abc", _make_ctx(c))
