from collections.abc import Callable
from typing import Any

from app.integration.mural.board.parsing import models
from app.integration.mural.board.parsing import schemas as widgets
from app.integration.mural.board.rendering import text

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


def _rich_text(node: widgets.StickyNoteWidget | widgets.ShapeWidget) -> str | None:
    """Plain text of a widget's content, preferring its rich text."""
    from_html = text.html_to_text(node.html_text) if node.html_text else ""
    return from_html or node.text or None


def _author_name(user: widgets.UserRef | None) -> str:
    if user is None:
        return "unknown"
    name = " ".join(p for p in (user.first_name, user.last_name) if p)
    return name or user.alias or "unknown"


def _comment_content(node: widgets.CommentWidget) -> str | None:
    lines = [node.message] if node.message else []
    lines += [
        f"↳ {_author_name(r.user)}: {r.message}" for r in node.replies if r.message
    ]
    return "\n".join(lines) or None


def _arrow_content(node: widgets.ArrowWidget) -> str | None:
    if node.label is None:
        return None
    return " / ".join(item.text for item in node.label.labels if item.text) or None


def _link_attrs(node: widgets.StickyNoteWidget | widgets.TextWidget) -> dict[str, str]:
    return {"href": node.hyperlink} if node.hyperlink else {}


def build_default_registry() -> WidgetRendererRegistry:
    reg = WidgetRendererRegistry()

    reg.register(
        models.BoardSummaryNode,
        tag="BoardSummary",
        attrs=lambda n: {"mural_id": n.id},
    )

    reg.register(
        models.RegionNode,
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
        models.TableRowNode,
        tag="Row",
        attrs=lambda n: {"id": n.id},
    )

    reg.register(
        models.TableColumnNode,
        tag="Column",
        attrs=lambda n: {"id": n.id},
    )

    reg.register(
        models.SpatialGroupNode,
        tag="Group",
        attrs=lambda n: {
            "id": n.id,
            "centroid_x": str(n.centroid_x),
            "centroid_y": str(n.centroid_y),
        },
    )

    reg.register(
        widgets.UnknownWidget,
        tag="Widget",
        attrs=lambda n: {"id": n.id, "type": n.type},
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
            **_link_attrs(n),
            **({"rotation": str(n.rotation)} if n.rotation else {}),
        },
        content=_rich_text,
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
        content=_rich_text,
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
            **_link_attrs(n),
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
            **({"title": n.title} if n.title else {}),
            **({"alt": n.description} if n.description else {}),
            "w": str(n.natural_width),
            "h": str(n.natural_height),
            **({"cropped": "true"} if n.mask else {}),
            **({"link": n.link} if n.link else {}),
            # url is null when the board restricts downloads
            **({"viewable": "true"} if n.url else {"restricted": "true"}),
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
        content=_arrow_content,
    )

    reg.register(
        widgets.CommentWidget,
        tag="Comment",
        attrs=lambda n: {
            "id": n.id,
            "author": _author_name(n.created_by),
            **({"on": n.reference_widget_id} if n.reference_widget_id else {}),
            **({"resolved": "true"} if n.resolved_by else {}),
        },
        content=_comment_content,
    )

    reg.register(
        widgets.FileWidget,
        tag="File",
        attrs=lambda n: {
            "id": n.id,
            "title": n.title,
            **({"has_preview": "true"} if n.preview_url else {}),
            **({"link": n.link} if n.link else {}),
            **({"rotation": str(n.rotation)} if n.rotation else {}),
        },
    )

    return reg
