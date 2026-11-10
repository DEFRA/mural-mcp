"""Splitting large tool output into parts an MCP client will accept.

Clients cut tool output off silently past a size limit (Claude Code at about
25k tokens), so a large region would lose widgets with no sign that it had.
Instead the output is cut at a whole widget, and a `Page` reported alongside
the MSX tells the agent what it got and where to continue.
"""

from collections.abc import Callable, Sequence

import pydantic

# About 15k tokens of MSX: well inside client limits, with room for the rest
# of the agent's context.
MSX_OUTPUT_BUDGET = 60_000


class ChildRegion(pydantic.BaseModel):
    id: str = pydantic.Field(description="Region id to pass to get_region.")
    title: str = pydantic.Field(description="The area's title on the board.")
    count: int = pydantic.Field(description="Widgets inside it, at any depth.")


class Page(pydantic.BaseModel):
    """What part of a result this response holds."""

    shown: int = pydantic.Field(
        description="Top-level items in this response: a region's direct "
        "children for get_region, matching widgets for find_widgets."
    )
    total: int = pydantic.Field(description="Top-level items in the whole result.")
    offset: int = pydantic.Field(description="Index of the first item shown.")
    next_offset: int | None = pydantic.Field(
        description="Call again with this offset to get the rest; null when "
        "the result is complete."
    )
    child_regions: list[ChildRegion] = pydantic.Field(
        default_factory=list,
        description="Areas directly inside the region, which can be opened "
        "with get_region instead of paging through everything.",
    )


PAGE_OUTPUT_SCHEMA = Page.model_json_schema()


def paginate(
    item_ids: Sequence[str],
    render_one: Callable[[str], str],
    *,
    offset: int,
    budget: int = MSX_OUTPUT_BUDGET,
) -> tuple[list[str], Page]:
    """Render items from `offset` until the next would go over `budget`.

    The first item is always rendered, even if it alone is over budget, so an
    agent following next_offset always makes progress.
    """
    start = max(0, offset)
    chunks: list[str] = []
    used = 0

    for item_id in item_ids[start:]:
        chunk = render_one(item_id)
        if chunks and used + len(chunk) > budget:
            break
        chunks.append(chunk)
        used += len(chunk) + 1

    end = start + len(chunks)
    page = Page(
        shown=len(chunks),
        total=len(item_ids),
        offset=start,
        next_offset=end if end < len(item_ids) else None,
    )
    return chunks, page
