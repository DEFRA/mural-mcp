import collections
from collections.abc import Sequence

from app.integration.mural.board.parsing import grouping, models, tables
from app.integration.mural.board.parsing import schemas as widget_schemas


class ParentIdStrategy:
    """Builds the tree from parent_id relationships plus explicit table structure."""

    def group(self, widgets: Sequence[models.AnyWidget]) -> grouping.AdjacencyResult:
        row_nodes, col_nodes, table_adj = tables.expand(widgets)
        cell_adj = self._process_cells(widgets)
        widget_adj = self._process_widgets(widgets)

        adjacency: dict[str | None, list[str]] = {}
        for partial in (table_adj, cell_adj, widget_adj):
            for parent, children in partial.items():
                adjacency.setdefault(parent, []).extend(children)

        return grouping.AdjacencyResult(
            row_nodes=row_nodes,
            col_nodes=col_nodes,
            adjacency=adjacency,
        )

    @staticmethod
    def _process_cells(
        widgets: Sequence[models.AnyWidget],
    ) -> dict[str, list[str]]:
        adjacency: dict[str, list[str]] = collections.defaultdict(list)
        for widget in widgets:
            if isinstance(widget, widget_schemas.TableCellWidget):
                adjacency[tables.col_node_id(widget.row_id, widget.column_id)].append(
                    widget.id
                )
        return dict(adjacency)

    @staticmethod
    def _process_widgets(
        widgets: Sequence[models.AnyWidget],
    ) -> dict[str | None, list[str]]:
        adjacency: dict[str | None, list[str]] = collections.defaultdict(list)
        for widget in widgets:
            if not isinstance(
                widget, widget_schemas.TableWidget | widget_schemas.TableCellWidget
            ):
                adjacency[widget.parent_id].append(widget.id)
        return dict(adjacency)
