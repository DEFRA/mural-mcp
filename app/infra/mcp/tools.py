import dishka
import fastmcp
from fastmcp.exceptions import ToolError

from app.auth import principal as principal_module
from app.infra.mcp import dishka_inject
from app.integration.linking import exceptions
from app.integration.mural import guard as guard_module
from app.integration.mural import service as board_service_module
from app.integration.mural.board import exceptions as board_exceptions


def _mural_token_error() -> ToolError:
    return ToolError("No Mural token found. Please connect your Mural account first.")


def _mural_api_error(err: exceptions.MuralApiError) -> ToolError:
    return ToolError(f"Mural API request failed with status {err.status_code}.")


def _mural_unavailable_error() -> ToolError:
    return ToolError("Mural API is unreachable. Please try again later.")


def _forbidden_board_error(err: guard_module.ForbiddenBoardError) -> ToolError:
    return ToolError(str(err))


def _region_not_found_error(
    err: board_exceptions.BoardRegionNotFoundError,
) -> ToolError:
    return ToolError(str(err))


@dishka_inject.inject
async def get_board_summary(
    mural_id: str,
    _ctx: fastmcp.Context,
    board: dishka.FromDishka[board_service_module.BoardService],
    principal: dishka.FromDishka[principal_module.Principal],
    use_spatial_grouping: bool = False,
) -> str:
    """Return a compact summary of the board's top-level regions with labels, widget counts, and bounds."""
    try:
        return await board.fetch_summary(
            principal.user_id, mural_id, use_spatial_grouping
        )
    except exceptions.MuralTokenError as err:
        raise _mural_token_error() from err
    except exceptions.MuralUnavailableError as err:
        raise _mural_unavailable_error() from err
    except exceptions.MuralApiError as err:
        raise _mural_api_error(err) from err
    except guard_module.ForbiddenBoardError as err:
        raise _forbidden_board_error(err) from err


@dishka_inject.inject
async def get_region(
    mural_id: str,
    region_id: str,
    _ctx: fastmcp.Context,
    board: dishka.FromDishka[board_service_module.BoardService],
    principal: dishka.FromDishka[principal_module.Principal],
    use_spatial_grouping: bool = False,
) -> str:
    """Return full MSX for all widgets within a board region (area or spatial group)."""
    try:
        return await board.fetch_region(
            principal.user_id, mural_id, region_id, use_spatial_grouping
        )
    except exceptions.MuralTokenError as err:
        raise _mural_token_error() from err
    except exceptions.MuralUnavailableError as err:
        raise _mural_unavailable_error() from err
    except exceptions.MuralApiError as err:
        raise _mural_api_error(err) from err
    except guard_module.ForbiddenBoardError as err:
        raise _forbidden_board_error(err) from err
    except board_exceptions.BoardRegionNotFoundError as err:
        raise _region_not_found_error(err) from err


@dishka_inject.inject
async def get_connections(
    mural_id: str,
    widget_id: str,
    _ctx: fastmcp.Context,
    board: dishka.FromDishka[board_service_module.BoardService],
    principal: dishka.FromDishka[principal_module.Principal],
) -> str:
    """Return all arrows connected to a widget and their resolved endpoints."""
    try:
        return await board.fetch_connections(principal.user_id, mural_id, widget_id)
    except exceptions.MuralTokenError as err:
        raise _mural_token_error() from err
    except exceptions.MuralUnavailableError as err:
        raise _mural_unavailable_error() from err
    except exceptions.MuralApiError as err:
        raise _mural_api_error(err) from err
    except guard_module.ForbiddenBoardError as err:
        raise _forbidden_board_error(err) from err


@dishka_inject.inject
async def find_widgets(
    mural_id: str,
    _ctx: fastmcp.Context,
    board: dishka.FromDishka[board_service_module.BoardService],
    principal: dishka.FromDishka[principal_module.Principal],
    query: str | None = None,
    widget_type: str | None = None,
) -> str:
    """Search board widgets by text content and/or widget type.

    At least one of query or widget_type must be provided.
    """
    if not query and not widget_type:
        return "Provide at least one of: query, widget_type."

    try:
        return await board.search_widgets(
            principal.user_id, mural_id, query, widget_type
        )
    except exceptions.MuralTokenError as err:
        raise _mural_token_error() from err
    except exceptions.MuralUnavailableError as err:
        raise _mural_unavailable_error() from err
    except exceptions.MuralApiError as err:
        raise _mural_api_error(err) from err
    except guard_module.ForbiddenBoardError as err:
        raise _forbidden_board_error(err) from err


def register_tools(mcp_app: fastmcp.FastMCP) -> None:
    mcp_app.tool()(get_board_summary)
    mcp_app.tool()(get_region)
    mcp_app.tool()(get_connections)
    mcp_app.tool()(find_widgets)
