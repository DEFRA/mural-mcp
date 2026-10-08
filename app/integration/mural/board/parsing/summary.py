import dataclasses
from collections.abc import Sequence

from app.integration.mural.board.parsing import models
from app.integration.mural.board.parsing import schemas as widget_schemas

# A sticky, shape or text at this font size or above is a region heading.
_HEADING_FONT_SIZE = 80


@dataclasses.dataclass(frozen=True)
class BoardSummary:
    root: models.BoardSummaryNode
    regions: list[models.RegionNode]

    @classmethod
    def build(cls, tree: models.WidgetTree, mural_id: str) -> "BoardSummary":
        regions: list[models.RegionNode] = []

        for root_id in tree.adjacency.get(None, []):
            node = tree.resolve(root_id)

            if isinstance(node, widget_schemas.AreaWidget):
                regions.append(
                    models.RegionNode(
                        id=root_id,
                        label=node.title or "",
                        count=cls._count_descendants(tree, root_id),
                        x=node.x,
                        y=node.y,
                        width=node.width,
                        height=node.height,
                    )
                )
            elif isinstance(node, models.SpatialGroupNode):
                child_ids = tree.adjacency.get(root_id, [])
                raw_children = [
                    tree.resolve(cid) for cid in child_ids if cid in tree.nodes
                ]
                widget_children = [
                    c for c in raw_children if isinstance(c, widget_schemas.Widget)
                ]
                x, y, w, h = (
                    cls._region_bounds(widget_children)
                    if widget_children
                    else (node.centroid_x, node.centroid_y, 0.0, 0.0)
                )
                regions.append(
                    models.RegionNode(
                        id=root_id,
                        label=cls._infer_label(tree, root_id),
                        count=len(child_ids),
                        x=x,
                        y=y,
                        width=w,
                        height=h,
                    )
                )

        return cls(root=models.BoardSummaryNode(id=mural_id), regions=regions)

    @staticmethod
    def _count_descendants(tree: models.WidgetTree, node_id: str) -> int:
        child_ids = tree.adjacency.get(node_id, [])
        return len(child_ids) + sum(
            BoardSummary._count_descendants(tree, cid) for cid in child_ids
        )

    @staticmethod
    def _region_bounds(
        children: Sequence[widget_schemas.Widget],
    ) -> tuple[float, float, float, float]:
        min_x = min(w.x for w in children)
        min_y = min(w.y for w in children)
        max_x = max(w.x + w.width for w in children)
        max_y = max(w.y + w.height for w in children)
        return min_x, min_y, max_x - min_x, max_y - min_y

    @staticmethod
    def _infer_label(tree: models.WidgetTree, node_id: str) -> str:
        child_ids = tree.adjacency.get(node_id, [])
        children = [tree.resolve(cid) for cid in child_ids]
        for child in children:
            if (
                isinstance(
                    child, widget_schemas.StickyNoteWidget | widget_schemas.ShapeWidget
                )
                and child.style.font_size >= _HEADING_FONT_SIZE
            ):
                return child.text or child.title or ""
            if (
                isinstance(child, widget_schemas.TextWidget)
                and child.style.font_size is not None
                and child.style.font_size >= _HEADING_FONT_SIZE
            ):
                return child.text or child.title or ""
        for child in children:
            if isinstance(child, widget_schemas.StickyNoteWidget) and child.text:
                return child.text
            text: str | None = getattr(child, "text", None) or getattr(
                child, "title", None
            )
            if text:
                return text
        return ""
