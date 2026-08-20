import dataclasses
from typing import Annotated, Any

import pydantic

from app.integration.mural.board.widgets import schemas as widgets

AnyWidget = Annotated[
    widgets.StickyNoteWidget
    | widgets.ShapeWidget
    | widgets.TextWidget
    | widgets.IconWidget
    | widgets.AreaWidget
    | widgets.ImageWidget
    | widgets.TableWidget
    | widgets.TableCellWidget
    | widgets.ArrowWidget
    | widgets.CommentWidget
    | widgets.FileWidget,
    pydantic.Field(discriminator="type"),
]

_widget_adapter: pydantic.TypeAdapter[Any] = pydantic.TypeAdapter(AnyWidget)


@dataclasses.dataclass
class TableRowNode:
    """Synthetic node representing a table row."""

    id: str
    table_id: str
    row: widgets.TableRow


@dataclasses.dataclass
class TableColumnNode:
    """Synthetic node representing a (row, column) slot within a table.

    The id is a composite "{row_id}/{col_id}" because column_id appears in
    every row — each slot needs a unique key in the adjacency list.
    """

    id: str
    row_id: str
    table_id: str
    column: widgets.TableColumn


@dataclasses.dataclass
class SpatialGroupNode:
    """Synthetic node grouping spatially proximate widgets that share no explicit parent.

    Created by SpatialGroupingStrategy when a cluster has no dominant anchor widget.
    """

    id: str
    centroid_x: float
    centroid_y: float


AnyNode = AnyWidget | TableRowNode | TableColumnNode | SpatialGroupNode


def parse_widgets(raw_widgets: list[dict[str, Any]]) -> list[AnyWidget]:
    """Parse a list of raw widget dicts from the Mural API into typed widgets."""
    return [_widget_adapter.validate_python(raw) for raw in raw_widgets]
