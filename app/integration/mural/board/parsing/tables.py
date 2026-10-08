"""Table expansion shared by the grouping strategies."""

import collections
from collections.abc import Sequence

from app.integration.mural.board.parsing import models
from app.integration.mural.board.parsing import schemas as widget_schemas


def col_node_id(row_id: str, col_id: str) -> str:
    """Id of a column slot; column ids repeat on every row, so the row is part of it."""
    return f"{row_id}/{col_id}"


def expand(
    widgets: Sequence[models.AnyWidget],
) -> tuple[
    dict[str, models.TableRowNode],
    dict[str, models.TableColumnNode],
    dict[str | None, list[str]],
]:
    """Expand tables into synthetic Row and Column nodes.

    The tree then reflects the logical grid structure rather than the flat
    widget list.
    """
    row_nodes: dict[str, models.TableRowNode] = {}
    col_nodes: dict[str, models.TableColumnNode] = {}
    adjacency: dict[str | None, list[str]] = collections.defaultdict(list)

    for widget in widgets:
        if not isinstance(widget, widget_schemas.TableWidget):
            continue

        adjacency[widget.parent_id].append(widget.id)
        adjacency[widget.id] = [row.row_id for row in widget.rows]

        for row in widget.rows:
            row_nodes[row.row_id] = models.TableRowNode(
                id=row.row_id, table_id=widget.id, row=row
            )
            adjacency[row.row_id] = [
                col_node_id(row.row_id, column.column_id) for column in widget.columns
            ]

            for column in widget.columns:
                node_id = col_node_id(row.row_id, column.column_id)
                col_nodes[node_id] = models.TableColumnNode(
                    id=node_id, row_id=row.row_id, table_id=widget.id, column=column
                )

    return row_nodes, col_nodes, dict(adjacency)
