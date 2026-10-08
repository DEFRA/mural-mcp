"""Output model of board parsing.

A Mural board arrives as a flat list of widgets. The tree built from it is an
adjacency list over the widgets plus *synthetic* nodes (table rows, table columns,
spatial groups) that exist only to give the structure somewhere to hang.
"""

import dataclasses
from typing import Annotated

import pydantic

from app.integration.mural.board.parsing import schemas as widgets

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


@dataclasses.dataclass(frozen=True)
class TableRowNode:
    """Synthetic node representing a table row."""

    id: str
    table_id: str
    row: widgets.TableRow


@dataclasses.dataclass(frozen=True)
class TableColumnNode:
    """Synthetic node representing a (row, column) slot within a table.

    The id is a composite "{row_id}/{col_id}" because column_id appears in
    every row — each slot needs a unique key in the adjacency list.
    """

    id: str
    row_id: str
    table_id: str
    column: widgets.TableColumn


@dataclasses.dataclass(frozen=True)
class SpatialGroupNode:
    """Synthetic node grouping spatially proximate widgets that share no explicit parent.

    Created by SpatialGroupingStrategy when a cluster has no dominant anchor widget.
    """

    id: str
    centroid_x: float
    centroid_y: float


AnyNode = AnyWidget | TableRowNode | TableColumnNode | SpatialGroupNode


@dataclasses.dataclass(frozen=True)
class WidgetTree:
    """Mural widget tree backed by an adjacency list.

    adjacency maps each parent_id to the ordered list of its children's IDs.
    None is the sentinel key for top-level widgets (no parent_id).

    nodes               — widget id          → AnyWidget
    row_nodes           — row_id             → TableRowNode
    col_nodes           — "{row}/{col}"      → TableColumnNode
    spatial_group_nodes — "spatial_group_N"  → SpatialGroupNode
    """

    nodes: dict[str, AnyWidget]
    row_nodes: dict[str, TableRowNode]
    col_nodes: dict[str, TableColumnNode]
    spatial_group_nodes: dict[str, SpatialGroupNode]
    adjacency: dict[str | None, list[str]]

    def resolve(self, node_id: str) -> AnyNode:
        if node_id in self.nodes:
            return self.nodes[node_id]
        if node_id in self.row_nodes:
            return self.row_nodes[node_id]
        if node_id in self.col_nodes:
            return self.col_nodes[node_id]
        return self.spatial_group_nodes[node_id]

    def children(self, node_id: str | None) -> list[AnyNode]:
        return [self.resolve(cid) for cid in self.adjacency.get(node_id, [])]

    def __str__(self) -> str:
        lines: list[str] = ["<root>"]

        root_ids = self.adjacency.get(None, [])

        for i, rid in enumerate(root_ids):
            lines += self._fmt(rid, "", i == len(root_ids) - 1)

        return "\n".join(lines)

    def _fmt(self, node_id: str, prefix: str, is_last: bool) -> list[str]:
        connector = "└── " if is_last else "├── "

        node = self.resolve(node_id)
        if isinstance(node, TableRowNode):
            label = f"row     [{node.row.row_id}]"
        elif isinstance(node, TableColumnNode):
            label = f"column  [{node.column.column_id}]"
        elif isinstance(node, SpatialGroupNode):
            label = f"group   [{node_id}]"
        else:
            label = f"{node.type}  [{node_id}]"
        lines = [f"{prefix}{connector}{label}"]

        child_prefix = prefix + ("    " if is_last else "│   ")
        child_ids = self.adjacency.get(node_id, [])

        for i, cid in enumerate(child_ids):
            lines += self._fmt(cid, child_prefix, i == len(child_ids) - 1)

        return lines


@dataclasses.dataclass(frozen=True)
class RegionNode:
    """A top-level region in the board summary view.

    Produced from an AreaWidget or SpatialGroupNode; never stored in WidgetTree.
    """

    id: str
    label: str
    count: int
    x: float
    y: float
    width: float
    height: float


@dataclasses.dataclass(frozen=True)
class BoardSummaryNode:
    """Root of the board summary tree.

    Never stored in WidgetTree.
    """

    id: str  # mural_id
