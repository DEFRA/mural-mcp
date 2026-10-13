"""Parse a Mural board's raw widgets into a WidgetTree."""

import logging
from typing import Any

import pydantic

from app.integration.mural.board.parsing import errors, grouping, models, parent_id
from app.integration.mural.board.parsing import schemas as widget_schemas

logger = logging.getLogger(__name__)

_widget_adapter: pydantic.TypeAdapter[Any] = pydantic.TypeAdapter(models.KnownWidget)


def _parse_widget(raw: dict[str, Any]) -> models.AnyWidget:
    try:
        widget: models.AnyWidget = _widget_adapter.validate_python(raw)
        return widget
    except pydantic.ValidationError as exc:
        # Log where it failed, never what the widget said: board content is user data.
        logger.warning(
            "Widget %r of type %r not readable; treating as unknown (fields: %s)",
            raw.get("id"),
            raw.get("type"),
            sorted({".".join(str(p) for p in e["loc"]) for e in exc.errors()}),
        )

    try:
        return widget_schemas.UnknownWidget.model_validate(raw)
    except pydantic.ValidationError:
        pass

    # Geometry itself is malformed: keep only the identity so the widget still
    # shows up in the tree.
    identity = {k: raw[k] for k in ("id", "type", "parentId") if k in raw}
    try:
        return widget_schemas.UnknownWidget.model_validate(identity)
    except pydantic.ValidationError as exc:
        msg = "A widget has no readable id or type."
        raise errors.BoardParseError(msg) from exc


def parse_widgets(raw_widgets: list[dict[str, Any]]) -> list[models.AnyWidget]:
    """Parse a list of raw widget dicts from the Mural API into typed widgets.

    A widget that doesn't match a known schema becomes an UnknownWidget rather
    than failing the board.

    Raises:
        BoardParseError: if a widget has no usable id and type.
    """
    return [_parse_widget(raw) for raw in raw_widgets]


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
