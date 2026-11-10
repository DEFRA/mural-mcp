from collections.abc import Awaitable
from typing import Annotated, Literal

import dishka
import fastmcp
import pydantic
from fastmcp.exceptions import ToolError
from fastmcp.tools import ToolResult
from fastmcp.utilities import types as mcp_types
from mcp_types import TextContent

from app.auth import principal as principal_module
from app.infra.mcp import dishka_inject
from app.integration.linking import exceptions
from app.integration.mural import guard as guard_module
from app.integration.mural import service as board_service_module
from app.integration.mural.board import errors as board_exceptions
from app.integration.mural.board.parsing import errors as parse_exceptions
from app.integration.mural.board.rendering import paging


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


def _board_parse_error() -> ToolError:
    return ToolError("Board could not be read.")


async def _call[T](work: Awaitable[T]) -> T:
    """Await a board operation, mapping its failures to MCP tool errors."""
    try:
        return await work
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
    except parse_exceptions.BoardParseError as err:
        raise _board_parse_error() from err
    except (
        board_exceptions.WidgetNotFoundError,
        board_exceptions.BoardImageError,
    ) as err:
        raise ToolError(str(err)) from err


type WidgetType = Literal[
    "area",
    "arrow",
    "comment",
    "file",
    "icon",
    "image",
    "shape",
    "sticky note",
    "table",
    "table cell",
    "text",
]

type Offset = Annotated[
    int,
    pydantic.Field(
        ge=0, description="Where to continue from: the next_offset of a previous call."
    ),
]


def _paged_result(msx: str, page: paging.Page) -> ToolResult:
    """MSX first, then the paging object as its own block.

    The paging object goes in structured_content for clients that read it, and
    as text too, because not every client shows structured content to the model.
    """
    return ToolResult(
        content=[
            TextContent(type="text", text=msx),
            TextContent(type="text", text=page.model_dump_json()),
        ],
        structured_content=page.model_dump(),
    )


@dishka_inject.inject
async def get_board_summary(
    mural_id: str,
    _ctx: fastmcp.Context,
    board: dishka.FromDishka[board_service_module.BoardService],
    principal: dishka.FromDishka[principal_module.Principal],
    use_spatial_grouping: bool = False,
) -> str:
    """Return a compact summary of the board's top-level regions with labels, widget counts, and bounds."""
    return await _call(
        board.fetch_summary(principal.user_id, mural_id, use_spatial_grouping)
    )


@dishka_inject.inject
async def get_region(
    mural_id: str,
    region_id: str,
    _ctx: fastmcp.Context,
    board: dishka.FromDishka[board_service_module.BoardService],
    principal: dishka.FromDishka[principal_module.Principal],
    use_spatial_grouping: bool = False,
    offset: Offset = 0,
) -> ToolResult:
    """Return MSX for the widgets within a board region (area or spatial group).

    The second block of the result says which part of the region this is. If
    its next_offset is not null, the region was too large for one response:
    call again with offset=next_offset, or open one of its child_regions.
    Image widgets can be viewed with get_image.
    """
    msx, page = await _call(
        board.fetch_region(
            principal.user_id, mural_id, region_id, use_spatial_grouping, offset
        )
    )
    return _paged_result(msx, page)


@dishka_inject.inject
async def get_connections(
    mural_id: str,
    widget_id: str,
    _ctx: fastmcp.Context,
    board: dishka.FromDishka[board_service_module.BoardService],
    principal: dishka.FromDishka[principal_module.Principal],
) -> str:
    """Return all arrows connected to a widget and their resolved endpoints."""
    return await _call(board.fetch_connections(principal.user_id, mural_id, widget_id))


@dishka_inject.inject
async def find_widgets(
    mural_id: str,
    _ctx: fastmcp.Context,
    board: dishka.FromDishka[board_service_module.BoardService],
    principal: dishka.FromDishka[principal_module.Principal],
    query: str | None = None,
    widget_type: WidgetType | None = None,
    region_id: str | None = None,
    offset: Offset = 0,
) -> ToolResult:
    """Search board widgets by text content and/or widget type.

    At least one of query or widget_type must be provided. Pass region_id (an
    id from get_board_summary or child_regions) to search only inside that
    region. The second block of
    the result says which matches this is; if its next_offset is not null, call
    again with offset=next_offset for the rest. Image widgets can be viewed with
    get_image.
    """
    if not query and not widget_type:
        empty = paging.Page(shown=0, total=0, offset=0, next_offset=None)
        return _paged_result("Provide at least one of: query, widget_type.", empty)

    msx, page = await _call(
        board.search_widgets(
            principal.user_id, mural_id, query, widget_type, offset, region_id
        )
    )
    return _paged_result(msx, page)


@dishka_inject.inject
async def get_image(
    mural_id: str,
    widget_id: str,
    _ctx: fastmcp.Context,
    board: dishka.FromDishka[board_service_module.BoardService],
    principal: dishka.FromDishka[principal_module.Principal],
    size: Literal["preview", "full"] = "preview",
) -> list[str | mcp_types.Image]:
    """Return one image (or file preview) from the board so you can look at it.

    Use the id of an Image widget, or of a File widget with has_preview="true".
    The image is cropped as shown on the board. size="preview" is about 1024px
    on the long edge; use "full" (up to 1568px) only when you need fine detail.
    """
    label, image = await _call(
        board.fetch_image(principal.user_id, mural_id, widget_id, size)
    )
    return [label, mcp_types.Image(data=image.data, format=image.format)]


# Every tool only reads the board. Telling the client lets it skip the
# confirmation prompt it would show for a tool that could change something.
_READ_ONLY = {"readOnlyHint": True, "openWorldHint": True}


def register_tools(mcp_app: fastmcp.FastMCP) -> None:
    mcp_app.tool(title="Board summary", annotations=_READ_ONLY)(get_board_summary)
    mcp_app.tool(
        title="Board region",
        annotations=_READ_ONLY,
        output_schema=paging.PAGE_OUTPUT_SCHEMA,
    )(get_region)
    mcp_app.tool(title="Widget connections", annotations=_READ_ONLY)(get_connections)
    mcp_app.tool(
        title="Find widgets",
        annotations=_READ_ONLY,
        output_schema=paging.PAGE_OUTPUT_SCHEMA,
    )(find_widgets)
    mcp_app.tool(title="Board image", annotations=_READ_ONLY)(get_image)
