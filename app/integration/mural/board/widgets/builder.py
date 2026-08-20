import dataclasses

from app.integration.mural.board.widgets import nodes as tree_nodes
from app.integration.mural.board.widgets.strategies import base, parent_id


@dataclasses.dataclass
class WidgetTree:
    """Mural widget tree backed by an adjacency list.

    adjacency maps each parent_id to the ordered list of its children's IDs.
    None is the sentinel key for top-level widgets (no parent_id).

    nodes               — widget id          → AnyWidget
    row_nodes           — row_id             → TableRowNode
    col_nodes           — "{row}/{col}"      → TableColumnNode
    spatial_group_nodes — "spatial_group_N"  → SpatialGroupNode
    """

    nodes: dict[str, tree_nodes.AnyWidget]
    row_nodes: dict[str, tree_nodes.TableRowNode]
    col_nodes: dict[str, tree_nodes.TableColumnNode]
    spatial_group_nodes: dict[str, tree_nodes.SpatialGroupNode]
    adjacency: dict[str | None, list[str]]

    @classmethod
    def build(
        cls,
        widgets: list[tree_nodes.AnyWidget],
        strategy: base.GroupingStrategy | None = None,
    ) -> "WidgetTree":
        """Build a tree from a flat widget list using the given grouping strategy.

        Defaults to ParentIdStrategy when no strategy is provided.
        """
        resolved_strategy: base.GroupingStrategy = (
            strategy if strategy is not None else parent_id.ParentIdStrategy()
        )

        result = resolved_strategy.group(widgets)

        return cls(
            nodes={w.id: w for w in widgets},
            row_nodes=result.row_nodes,
            col_nodes=result.col_nodes,
            spatial_group_nodes=result.spatial_group_nodes,
            adjacency=result.adjacency,
        )

    def resolve(self, node_id: str) -> tree_nodes.AnyNode:
        if node_id in self.nodes:
            return self.nodes[node_id]
        if node_id in self.row_nodes:
            return self.row_nodes[node_id]
        if node_id in self.col_nodes:
            return self.col_nodes[node_id]
        return self.spatial_group_nodes[node_id]

    def children(self, node_id: str | None) -> list[tree_nodes.AnyNode]:
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
        if isinstance(node, tree_nodes.TableRowNode):
            label = f"row     [{node.row.row_id}]"
        elif isinstance(node, tree_nodes.TableColumnNode):
            label = f"column  [{node.column.column_id}]"
        elif isinstance(node, tree_nodes.SpatialGroupNode):
            label = f"group   [{node_id}]"
        else:
            label = f"{node.type}  [{node_id}]"
        lines = [f"{prefix}{connector}{label}"]

        child_prefix = prefix + ("    " if is_last else "│   ")
        child_ids = self.adjacency.get(node_id, [])

        for i, cid in enumerate(child_ids):
            lines += self._fmt(cid, child_prefix, i == len(child_ids) - 1)

        return lines
