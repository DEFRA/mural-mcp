import html
from collections.abc import Sequence

from app.integration.mural.board.parsing import models, parser
from app.integration.mural.board.parsing import schemas as widget_schemas
from app.integration.mural.board.rendering import paging, registry

_INDENT = "  "


def format_attrs(attrs: dict[str, str]) -> str:
    if not attrs:
        return ""
    return "".join(f' {k}="{html.escape(v, quote=True)}"' for k, v in attrs.items())


# Re-exported: callers that render also need to know what gets rendered.
is_shown = models.is_shown


def render_subtree(
    tree: models.WidgetTree,
    root_id: str,
    reg: registry.WidgetRendererRegistry,
) -> str:
    return "\n".join(_render_node(root_id, tree, reg, indent=0))


def render_msx(
    tree: models.WidgetTree,
    reg: registry.WidgetRendererRegistry,
) -> str:
    lines: list[str] = []
    for rid in tree.adjacency.get(None, []):
        lines += _render_node(rid, tree, reg, indent=0)
    return "\n".join(lines)


def _render_node(
    node_id: str,
    tree: models.WidgetTree,
    reg: registry.WidgetRendererRegistry,
    indent: int,
    force: bool = False,
) -> list[str]:
    node = tree.resolve(node_id)
    if not force and not is_shown(node):
        return []
    tag = reg.get_tag_name(node)
    attr_str = format_attrs(reg.get_attrs(node))

    child_ids = tree.shown_child_ids(node_id)
    content = reg.get_content(node)
    prefix = _INDENT * indent

    if child_ids or content:
        lines: list[str] = [f"{prefix}<{tag}{attr_str}>"]
        if content:
            lines += [
                f"{prefix}{_INDENT}{line}"
                for line in html.escape(content, quote=False).splitlines()
            ]
        for cid in child_ids:
            lines += _render_node(cid, tree, reg, indent + 1)
        lines.append(f"{prefix}</{tag}>")
    else:
        lines = [f"{prefix}<{tag}{attr_str}/>"]

    return lines


def _connection(
    arrow_id: str,
    direction: str,
    role: str,
    other_id: str,
    tree: models.WidgetTree,
) -> str:
    """One <Connection>; the other end's type is given only if it is on the board."""
    attrs = {"arrow_id": arrow_id, "direction": direction, f"{role}_id": other_id}
    if other_id in tree.nodes:
        attrs[f"{role}_type"] = tree.nodes[other_id].type
    return f"  <Connection{format_attrs(attrs)}/>"


class WidgetMsxRenderer:
    def __init__(self, reg: registry.WidgetRendererRegistry) -> None:
        self._reg = reg

    def render_subtree(self, tree: models.WidgetTree, root_id: str) -> str:
        return render_subtree(tree, root_id, self._reg)

    def render_region_page(
        self,
        tree: models.WidgetTree,
        region_id: str,
        *,
        offset: int = 0,
        budget: int = paging.MSX_OUTPUT_BUDGET,
    ) -> tuple[str, paging.Page]:
        """MSX for part of a region: its tag wrapping a run of its direct children.

        Every part repeats the region's own tag, so each one is well-formed
        and says where its widgets sit.
        """
        child_ids = tree.shown_child_ids(region_id)
        chunks, page = paging.paginate(
            child_ids,
            lambda cid: "\n".join(_render_node(cid, tree, self._reg, indent=1)),
            offset=offset,
            budget=budget,
        )
        page.child_regions = [
            paging.ChildRegion(
                id=cid, title=node.title, count=tree.count_shown_descendants(cid)
            )
            for cid in child_ids
            if isinstance(node := tree.resolve(cid), widget_schemas.AreaWidget)
        ]

        node = tree.resolve(region_id)
        tag = self._reg.get_tag_name(node)
        attr_str = format_attrs(self._reg.get_attrs(node))
        if not child_ids:
            return render_subtree(tree, region_id, self._reg), page

        lines = [f"<{tag}{attr_str}>"]
        content = self._reg.get_content(node)
        if content:
            lines += [
                f"{_INDENT}{line}"
                for line in html.escape(content, quote=False).splitlines()
            ]
        lines += chunks
        lines.append(f"</{tag}>")
        return "\n".join(lines), page

    def render_widget(self, widget: models.AnyWidget) -> str:
        """MSX for one widget on its own, shown even if hidden on the board."""
        lines = _render_node(
            widget.id, parser.build_tree([widget]), self._reg, indent=0, force=True
        )
        return "\n".join(lines)

    def render_widgets(
        self,
        widget_ids: Sequence[str],
        tree: models.WidgetTree,
        *,
        offset: int = 0,
        budget: int = paging.MSX_OUTPUT_BUDGET,
    ) -> tuple[str, paging.Page]:
        """MSX for a run of the given widgets, each rendered with its subtree."""
        chunks, page = paging.paginate(
            widget_ids,
            lambda wid: "\n".join(_render_node(wid, tree, self._reg, indent=0)),
            offset=offset,
            budget=budget,
        )
        return "\n".join(chunks), page

    def render_connections(
        self,
        widget_id: str,
        parsed: list[models.AnyWidget],
        tree: models.WidgetTree,
    ) -> str:
        connection_lines: list[str] = []

        for widget in parsed:
            if not isinstance(widget, widget_schemas.ArrowWidget):
                continue
            if widget.start_ref_id == widget_id and widget.end_ref_id:
                connection_lines.append(
                    _connection(
                        widget.id, "outgoing", "target", widget.end_ref_id, tree
                    )
                )
            elif widget.end_ref_id == widget_id and widget.start_ref_id:
                connection_lines.append(
                    _connection(
                        widget.id, "incoming", "source", widget.start_ref_id, tree
                    )
                )

        if not connection_lines:
            return f"<Connections{format_attrs({'widget_id': widget_id})}/>"

        inner = "\n".join(connection_lines)
        opening = f"<Connections{format_attrs({'widget_id': widget_id})}>"
        return f"{opening}\n{inner}\n</Connections>"
