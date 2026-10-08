import collections
import dataclasses
import math
from collections.abc import Sequence

from app.integration.mural.board.parsing import grouping, models, tables
from app.integration.mural.board.parsing import schemas as widget_schemas

# Prefix of the synthetic ids given to clusters with no dominant anchor widget.
_GROUP_ID_PREFIX = "spatial_group_"


@dataclasses.dataclass
class SpatialGroupingStrategy:
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

    def group(self, widgets: Sequence[models.AnyWidget]) -> grouping.AdjacencyResult:
        row_nodes, col_nodes, table_adj = tables.expand(widgets)

        # Tables and their cells are placed by tables.expand, not clustered.
        table_part_ids = {
            w.id
            for w in widgets
            if isinstance(
                w, widget_schemas.TableWidget | widget_schemas.TableCellWidget
            )
        }
        clusters = self._connected_components(
            [w for w in widgets if w.id not in table_part_ids], self.cluster_gap
        )

        adjacency: dict[str | None, list[str]] = collections.defaultdict(list)
        for parent, children in table_adj.items():
            adjacency[parent].extend(children)

        spatial_group_nodes: dict[str, models.SpatialGroupNode] = {}
        for index, cluster in enumerate(clusters):
            if len(cluster) == 1:
                adjacency[None].append(cluster[0].id)
                continue

            anchor = self._anchor(cluster)
            if anchor is not None:
                adjacency[None].append(anchor.id)
                adjacency[anchor.id].extend(w.id for w in cluster if w is not anchor)
                continue

            group = self._group_node(index, cluster)
            spatial_group_nodes[group.id] = group
            adjacency[None].append(group.id)
            adjacency[group.id].extend(w.id for w in cluster)

        return grouping.AdjacencyResult(
            row_nodes=row_nodes,
            col_nodes=col_nodes,
            adjacency=dict(adjacency),
            spatial_group_nodes=spatial_group_nodes,
        )

    def _anchor(self, cluster: Sequence[models.AnyWidget]) -> models.AnyWidget | None:
        """The widget dominating the cluster, if one is anchor_ratio times the next."""
        largest, second = sorted(cluster, key=self._area, reverse=True)[:2]
        second_area = self._area(second)
        if second_area > 0 and self._area(largest) / second_area >= self.anchor_ratio:
            return largest
        return None

    @staticmethod
    def _group_node(
        index: int, cluster: Sequence[models.AnyWidget]
    ) -> models.SpatialGroupNode:
        return models.SpatialGroupNode(
            id=f"{_GROUP_ID_PREFIX}{index}",
            centroid_x=sum(w.x + w.width / 2 for w in cluster) / len(cluster),
            centroid_y=sum(w.y + w.height / 2 for w in cluster) / len(cluster),
        )

    @staticmethod
    def _area(widget: models.AnyWidget) -> float:
        return widget.width * widget.height

    @staticmethod
    def _bbox_distance(a: models.AnyWidget, b: models.AnyWidget) -> float:
        """Minimum distance between two bounding boxes (0 when overlapping)."""
        dx = max(0.0, max(a.x, b.x) - min(a.x + a.width, b.x + b.width))
        dy = max(0.0, max(a.y, b.y) - min(a.y + a.height, b.y + b.height))

        return math.sqrt(dx * dx + dy * dy)

    @classmethod
    def _connected_components(
        cls,
        widgets: Sequence[models.AnyWidget],
        gap: float,
    ) -> list[list[models.AnyWidget]]:
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

        groups: dict[int, list[models.AnyWidget]] = collections.defaultdict(list)

        for index, widget in enumerate(widgets):
            groups[find(index)].append(widget)

        return list(groups.values())
