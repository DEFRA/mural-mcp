from collections.abc import Callable
from typing import Any

from app.mural.board.summary import nodes as summary_nodes
from app.mural.board.widgets import nodes
from app.mural.board.widgets import schemas as widgets

type AttrExtractor = Callable[[Any], dict[str, str]]
type ContentExtractor = Callable[[Any], str | None]


class WidgetRendererRegistry:
    """Maps widget/node types to their MSX tag name and attribute extractor.

    Register a type with `register()`. The renderer calls `get_tag_name()`,
    `get_attrs()`, and `get_content()` — no isinstance chains needed in the
    renderer itself.
    """

    def __init__(self) -> None:
        self._tags: dict[type, str] = {}
        self._attrs: dict[type, AttrExtractor] = {}
        self._content: dict[type, ContentExtractor] = {}

    def register(
        self,
        widget_type: type,
        *,
        tag: str,
        attrs: AttrExtractor,
        content: ContentExtractor | None = None,
    ) -> None:
        self._tags[widget_type] = tag
        self._attrs[widget_type] = attrs
        if content is not None:
            self._content[widget_type] = content

    def get_tag_name(self, node: Any) -> str:
        return self._tags.get(type(node), type(node).__name__)

    def get_attrs(self, node: Any) -> dict[str, str]:
        extractor = self._attrs.get(type(node))
        return extractor(node) if extractor else {"id": node.id}

    def get_content(self, node: Any) -> str | None:
        extractor = self._content.get(type(node))
        return extractor(node) if extractor else None


def _font_size_to_role(font_size: float) -> str:
    if font_size >= 80:
        return "heading"

    if font_size >= 50:
        return "label"

    return "caption"


def build_default_registry() -> WidgetRendererRegistry:
    reg = WidgetRendererRegistry()

    reg.register(
        summary_nodes.BoardSummaryNode,
        tag="BoardSummary",
        attrs=lambda n: {"mural_id": n.id},
    )

    reg.register(
        summary_nodes.RegionNode,
        tag="Region",
        attrs=lambda n: {
            "id": n.id,
            "label": n.label,
            "count": str(n.count),
            "x": str(n.x),
            "y": str(n.y),
            "width": str(n.width),
            "height": str(n.height),
        },
    )

    reg.register(
        nodes.TableRowNode,
        tag="Row",
        attrs=lambda n: {"id": n.id},
    )

    reg.register(
        nodes.TableColumnNode,
        tag="Column",
        attrs=lambda n: {"id": n.id},
    )

    reg.register(
        nodes.SpatialGroupNode,
        tag="Group",
        attrs=lambda n: {
            "id": n.id,
            "centroid_x": str(n.centroid_x),
            "centroid_y": str(n.centroid_y),
        },
    )

    reg.register(
        widgets.StickyNoteWidget,
        tag="StickyNote",
        attrs=lambda n: {
            "id": n.id,
            "color": n.style.background_color,
            "text_align": n.style.text_align,
            "role": _font_size_to_role(n.style.font_size),
            **({"tags": ",".join(n.tags)} if n.tags else {}),
            **({"rotation": str(n.rotation)} if n.rotation else {}),
        },
        content=lambda n: n.html_text or n.text or None,
    )

    reg.register(
        widgets.ShapeWidget,
        tag="Shape",
        attrs=lambda n: {
            "id": n.id,
            "shape": n.shape,
            "title": n.title,
            "background_color": n.style.background_color,
            "border_color": n.style.border_color,
            "font_color": n.style.font_color,
            "text_align": n.style.text_align,
            "role": _font_size_to_role(n.style.font_size),
            **({"rotation": str(n.rotation)} if n.rotation else {}),
        },
        content=lambda n: n.html_text or n.text or None,
    )

    reg.register(
        widgets.TextWidget,
        tag="Text",
        attrs=lambda n: {
            "id": n.id,
            "title": n.title,
            **(
                {"background_color": n.style.background_color}
                if n.style.background_color
                else {}
            ),
            **({"text_align": n.style.text_align} if n.style.text_align else {}),
            **(
                {"role": _font_size_to_role(n.style.font_size)}
                if n.style.font_size
                else {}
            ),
            **({"rotation": str(n.rotation)} if n.rotation else {}),
        },
        content=lambda n: n.text or None,
    )

    reg.register(
        widgets.IconWidget,
        tag="Icon",
        attrs=lambda n: {
            "id": n.id,
            "name": n.name,
            "title": n.title,
            "color": n.style.color,
            **({"rotation": str(n.rotation)} if n.rotation else {}),
        },
    )

    reg.register(
        widgets.AreaWidget,
        tag="Area",
        attrs=lambda n: {
            "id": n.id,
            "title": n.title,
            "layout": n.layout,
            "background_color": n.style.background_color,
            "border_color": n.style.border_color,
            "border_style": n.style.border_style,
            "role": _font_size_to_role(n.style.title_font_size),
        },
    )

    reg.register(
        widgets.ImageWidget,
        tag="Image",
        attrs=lambda n: {
            "id": n.id,
            **({"url": n.url} if n.url else {}),
            **({"rotation": str(n.rotation)} if n.rotation else {}),
        },
        content=lambda n: n.caption or None,
    )

    reg.register(
        widgets.TableWidget,
        tag="Table",
        attrs=lambda n: {
            "id": n.id,
            "border_color": n.style.border_color,
            "border_width": str(n.style.border_width),
        },
    )

    reg.register(
        widgets.TableCellWidget,
        tag="TableCell",
        attrs=lambda n: {
            "id": n.id,
            "background_color": n.style.background_color,
        },
    )

    reg.register(
        widgets.ArrowWidget,
        tag="Arrow",
        attrs=lambda n: {
            "id": n.id,
            "arrow_type": n.arrow_type,
            "tip": n.tip,
            "stroke_color": n.style.stroke_color,
            **({"start_ref_id": n.start_ref_id} if n.start_ref_id else {}),
            **({"end_ref_id": n.end_ref_id} if n.end_ref_id else {}),
        },
    )

    reg.register(
        widgets.CommentWidget,
        tag="Comment",
        attrs=lambda n: {
            "id": n.id,
            **({"replies": str(len(n.replies))} if n.replies else {}),
        },
        content=lambda n: n.message or None,
    )

    reg.register(
        widgets.FileWidget,
        tag="File",
        attrs=lambda n: {
            "id": n.id,
            "title": n.title,
            **({"url": n.url} if n.url else {}),
            **({"rotation": str(n.rotation)} if n.rotation else {}),
        },
    )

    return reg
