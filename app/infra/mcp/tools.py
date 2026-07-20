import dishka
import fastmcp
from fastmcp.exceptions import ToolError
from fastmcp.server import dependencies as fastmcp_deps

from app.infra.mcp import dishka_inject
from app.mural.board import service as board_service_module
from app.mural.connectivity import (
    exceptions,
    oauth_client,
    state_store,
)
from app.mural.connectivity import (
    ports as token_store,
)


def _mural_token_error() -> ToolError:
    return ToolError("No Mural token found. Please connect your Mural account first.")


@dishka_inject.inject
async def get_mural_connection_url(
    ctx: fastmcp.Context,
    states: dishka.FromDishka[state_store.OAuthStateStore],
    oauth: dishka.FromDishka[oauth_client.OAuthClient],
    user_id: str = fastmcp_deps.TokenClaim("email"),
) -> str:
    """Return the URL the user must visit to connect their Mural account."""
    state = states.issue(user_id)
    url = oauth.build_authorization_url(state)

    await ctx.info(f"Mural connection URL: {url}")

    return url


@dishka_inject.inject
async def disconnect_mural(
    ctx: fastmcp.Context,
    store: dishka.FromDishka[token_store.TokenStore],
    user_id: str = fastmcp_deps.TokenClaim("email"),
) -> str:
    """Remove the current user's stored Mural credentials."""
    await store.delete_tokens(user_id)

    await ctx.info(f"Mural account disconnected for user {user_id}")

    return "Mural account disconnected."


@dishka_inject.inject
async def get_board_summary(
    mural_id: str,
    ctx: fastmcp.Context,
    board: dishka.FromDishka[board_service_module.BoardService],
    user_id: str = fastmcp_deps.TokenClaim("email"),
    use_spatial_grouping: bool = False,
) -> str:
    """Return a compact summary of the board's top-level regions with labels, widget counts, and bounds."""
    try:
        return await board.fetch_summary(user_id, mural_id, use_spatial_grouping)
    except exceptions.MuralTokenError:
        raise _mural_token_error()


@dishka_inject.inject
async def get_region(
    mural_id: str,
    region_id: str,
    ctx: fastmcp.Context,
    board: dishka.FromDishka[board_service_module.BoardService],
    user_id: str = fastmcp_deps.TokenClaim("email"),
    use_spatial_grouping: bool = False,
) -> str:
    """Return full MSX for all widgets within a board region (area or spatial group)."""
    try:
        return await board.fetch_region(
            user_id, mural_id, region_id, use_spatial_grouping
        )
    except exceptions.MuralTokenError:
        raise _mural_token_error()


@dishka_inject.inject
async def get_connections(
    mural_id: str,
    widget_id: str,
    ctx: fastmcp.Context,
    board: dishka.FromDishka[board_service_module.BoardService],
    user_id: str = fastmcp_deps.TokenClaim("email"),
) -> str:
    """Return all arrows connected to a widget and their resolved endpoints."""
    try:
        return await board.fetch_connections(user_id, mural_id, widget_id)
    except exceptions.MuralTokenError:
        raise _mural_token_error()


@dishka_inject.inject
async def find_widgets(
    mural_id: str,
    ctx: fastmcp.Context,
    board: dishka.FromDishka[board_service_module.BoardService],
    user_id: str = fastmcp_deps.TokenClaim("email"),
    query: str | None = None,
    widget_type: str | None = None,
) -> str:
    """Search board widgets by text content and/or widget type.

    At least one of query or widget_type must be provided.
    """
    if not query and not widget_type:
        return "Provide at least one of: query, widget_type."

    try:
        return await board.search_widgets(user_id, mural_id, query, widget_type)
    except exceptions.MuralTokenError:
        raise _mural_token_error()


def register_tools(mcp_app: fastmcp.FastMCP) -> None:
    mcp_app.tool()(get_mural_connection_url)
    mcp_app.tool()(disconnect_mural)
    mcp_app.tool()(get_board_summary)
    mcp_app.tool()(get_region)
    mcp_app.tool()(get_connections)
    mcp_app.tool()(find_widgets)
