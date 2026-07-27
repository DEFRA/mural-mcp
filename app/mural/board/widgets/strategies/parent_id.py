import collections
from collections.abc import Sequence

from app.mural.board.widgets import nodes
from app.mural.board.widgets import schemas as widget_schemas
from app.mural.board.widgets.strategies import base


class ParentIdStrategy(base.BaseStrategy):
    """Builds the tree from parent_id relationships plus explicit table structure."""

    def group(self, widgets: Sequence[nodes.AnyWidget]) -> base.AdjacencyResult:
        row_nodes, col_nodes, table_adj = self._process_tables(widgets)
        cell_adj = self._process_cells(widgets)
        widget_adj = self._process_widgets(widgets)

        adjacency: dict[str | None, list[str]] = {}
        for partial in (table_adj, cell_adj, widget_adj):
            for parent, children in partial.items():
                adjacency.setdefault(parent, []).extend(children)

        return base.AdjacencyResult(
            row_nodes=row_nodes,
            col_nodes=col_nodes,
            adjacency=adjacency,
        )

    def _process_cells(
        self,
        widgets: Sequence[nodes.AnyWidget],
    ) -> dict[str, list[str]]:
        adjacency: dict[str, list[str]] = collections.defaultdict(list)
        for widget in widgets:
            if isinstance(widget, widget_schemas.TableCellWidget):
                adjacency[self._col_node_id(widget.row_id, widget.column_id)].append(
                    widget.id
                )
        return dict(adjacency)

    def _process_widgets(
        self,
        widgets: Sequence[nodes.AnyWidget],
    ) -> dict[str | None, list[str]]:
        adjacency: dict[str | None, list[str]] = collections.defaultdict(list)
        for widget in widgets:
            if not isinstance(
                widget, widget_schemas.TableWidget | widget_schemas.TableCellWidget
            ):
                adjacency[widget.parent_id].append(widget.id)
        return dict(adjacency)
