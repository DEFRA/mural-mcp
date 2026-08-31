import collections
import dataclasses
from collections.abc import Sequence
from typing import Protocol

from app.integration.mural.board.widgets import nodes
from app.integration.mural.board.widgets import schemas as widget_schemas


@dataclasses.dataclass
class AdjacencyResult:
    """Output produced by a GroupingStrategy."""

    row_nodes: dict[str, nodes.TableRowNode]
    col_nodes: dict[str, nodes.TableColumnNode]
    adjacency: dict[str | None, list[str]]
    spatial_group_nodes: dict[str, nodes.SpatialGroupNode] = dataclasses.field(
        default_factory=dict
    )


class GroupingStrategy(Protocol):
    """Converts a flat widget list into an adjacency structure."""

    def group(self, widgets: Sequence[nodes.AnyWidget]) -> AdjacencyResult: ...


class BaseStrategy:
    """Shared table-expansion logic for grouping strategies.

    Tables are expanded into synthetic Row and Column nodes so the tree
    reflects the logical grid structure rather than the flat widget list.
    """

    @staticmethod
    def _col_node_id(row_id: str, col_id: str) -> str:
        return f"{row_id}/{col_id}"

    def _process_tables(
        self,
        widgets: Sequence[nodes.AnyWidget],
    ) -> tuple[
        dict[str, nodes.TableRowNode],
        dict[str, nodes.TableColumnNode],
        dict[str | None, list[str]],
    ]:
        row_nodes: dict[str, nodes.TableRowNode] = {}
        col_nodes: dict[str, nodes.TableColumnNode] = {}
        adjacency: dict[str | None, list[str]] = collections.defaultdict(list)

        for widget in widgets:
            if not isinstance(widget, widget_schemas.TableWidget):
                continue

            adjacency[widget.parent_id].append(widget.id)
            adjacency[widget.id] = [row.row_id for row in widget.rows]

            for row in widget.rows:
                row_nodes[row.row_id] = nodes.TableRowNode(
                    id=row.row_id, table_id=widget.id, row=row
                )

                adjacency[row.row_id] = [
                    self._col_node_id(row.row_id, column.column_id)
                    for column in widget.columns
                ]

                for column in widget.columns:
                    column_node_id = self._col_node_id(row.row_id, column.column_id)

                    col_nodes[column_node_id] = nodes.TableColumnNode(
                        id=column_node_id,
                        row_id=row.row_id,
                        table_id=widget.id,
                        column=column,
                    )

        return row_nodes, col_nodes, dict(adjacency)
