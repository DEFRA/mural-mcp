"""Parse a Mural board's raw widgets into a WidgetTree."""

from typing import Any

import pydantic

from app.integration.mural.board.parsing import errors, grouping, models, parent_id

_widget_adapter: pydantic.TypeAdapter[Any] = pydantic.TypeAdapter(models.AnyWidget)


def parse_widgets(raw_widgets: list[dict[str, Any]]) -> list[models.AnyWidget]:
    """Parse a list of raw widget dicts from the Mural API into typed widgets.

    Raises:
        BoardParseError: if a widget does not match any known widget schema.
    """
    try:
        return [_widget_adapter.validate_python(raw) for raw in raw_widgets]
    except pydantic.ValidationError as exc:
        raise errors.BoardParseError(str(exc)) from exc


def build_tree(
    widgets: list[models.AnyWidget],
    strategy: grouping.GroupingStrategy | None = None,
) -> models.WidgetTree:
    """Build a tree from a flat widget list using the given grouping strategy.

    Defaults to ParentIdStrategy when no strategy is provided.
    """
    resolved: grouping.GroupingStrategy = (
        strategy if strategy is not None else parent_id.ParentIdStrategy()
    )
    result = resolved.group(widgets)

    return models.WidgetTree(
        nodes={w.id: w for w in widgets},
        row_nodes=result.row_nodes,
        col_nodes=result.col_nodes,
        spatial_group_nodes=result.spatial_group_nodes,
        adjacency=result.adjacency,
    )


def parse_board(
    raw_widgets: list[dict[str, Any]],
    strategy: grouping.GroupingStrategy | None = None,
) -> tuple[list[models.AnyWidget], models.WidgetTree]:
    """Parse raw Mural widgets into typed widgets and their tree."""
    widgets = parse_widgets(raw_widgets)
    return widgets, build_tree(widgets, strategy)
