import collections
import dataclasses
import math
from collections.abc import Sequence

from app.integration.mural.board.widgets import nodes
from app.integration.mural.board.widgets import schemas as widget_schemas
from app.integration.mural.board.widgets.strategies import base


@dataclasses.dataclass
class SpatialGroupingStrategy(base.BaseStrategy):
    """Builds the tree by clustering widgets that are spatially proximate.

    Algorithm:
    1. Build a proximity graph: two widgets are connected when the minimum
       distance between their bounding boxes is <= cluster_gap.
    2. Find connected components (union-find) → each component is a cluster.
    3. Single-widget clusters → placed at root (None).
    4. Multi-widget clusters:
       - If the largest widget's area is >= anchor_ratio times the second-
         largest, it becomes the parent of all other cluster members.
       - Otherwise a SpatialGroupNode is created as a synthetic parent.
    5. Tables are expanded into Row/Column nodes only when TableWidget
       instances are present (same structure as ParentIdStrategy).
    """

    cluster_gap: float = 100.0
    anchor_ratio: float = 3.0

    def group(self, widgets: Sequence[nodes.AnyWidget]) -> base.AdjacencyResult:
        row_nodes, col_nodes, table_adj = self._process_tables(widgets)

        spatial_group_nodes: dict[str, nodes.SpatialGroupNode] = {}

        table_ids = {w.id for w in widgets if isinstance(w, widget_schemas.TableWidget)}

        cell_ids = {
            w.id for w in widgets if isinstance(w, widget_schemas.TableCellWidget)
        }

        non_table = [
            widget
            for widget in widgets
            if widget.id not in table_ids and widget.id not in cell_ids
        ]

        clusters = self._connected_components(non_table, self.cluster_gap)

        adjacency: dict[str | None, list[str]] = collections.defaultdict(list)

        for parent, children in table_adj.items():
            adjacency[parent].extend(children)

        for index, cluster in enumerate(clusters):
            if len(cluster) == 1:
                adjacency[None].append(cluster[0].id)
                continue

            by_area = sorted(cluster, key=lambda w: w.width * w.height, reverse=True)
            largest = by_area[0]
            second = by_area[1]
            largest_area = largest.width * largest.height
            second_area = second.width * second.height

            if second_area > 0 and largest_area / second_area >= self.anchor_ratio:
                parent_id = largest.id

                for widget in cluster:
                    if widget.id != parent_id:
                        adjacency[parent_id].append(widget.id)

                adjacency[None].append(parent_id)
            else:
                centroid_x = sum(w.x + w.width / 2 for w in cluster) / len(cluster)
                centroid_y = sum(w.y + w.height / 2 for w in cluster) / len(cluster)

                group_id = f"spatial_group_{index}"
                spatial_group_nodes[group_id] = nodes.SpatialGroupNode(
                    id=group_id, centroid_x=centroid_x, centroid_y=centroid_y
                )

                adjacency[None].append(group_id)
                for widget in cluster:
                    adjacency[group_id].append(widget.id)

        return base.AdjacencyResult(
            row_nodes=row_nodes,
            col_nodes=col_nodes,
            adjacency=dict(adjacency),
            spatial_group_nodes=spatial_group_nodes,
        )

    @staticmethod
    def _bbox_distance(a: nodes.AnyWidget, b: nodes.AnyWidget) -> float:
        """Minimum distance between two bounding boxes (0 when overlapping)."""
        dx = max(0.0, max(a.x, b.x) - min(a.x + a.width, b.x + b.width))
        dy = max(0.0, max(a.y, b.y) - min(a.y + a.height, b.y + b.height))

        return math.sqrt(dx * dx + dy * dy)

    @classmethod
    def _connected_components(
        cls,
        widgets: Sequence[nodes.AnyWidget],
        gap: float,
    ) -> list[list[nodes.AnyWidget]]:
        """Return spatially connected components using union-find."""
        n = len(widgets)
        parent = list(range(n))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i: int, j: int) -> None:
            parent[find(i)] = find(j)

        for i in range(n):
            for j in range(i + 1, n):
                if cls._bbox_distance(widgets[i], widgets[j]) <= gap:
                    union(i, j)

        groups: dict[int, list[nodes.AnyWidget]] = collections.defaultdict(list)

        for index, widget in enumerate(widgets):
            groups[find(index)].append(widget)

        return list(groups.values())
