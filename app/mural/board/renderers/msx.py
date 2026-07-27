from collections.abc import Iterable

from app.mural.board import registry
from app.mural.board.widgets import builder, nodes
from app.mural.board.widgets import schemas as widget_schemas


def _format_attrs(attrs: dict[str, str]) -> str:
    if not attrs:
        return ""
    return "".join(f' {k}="{v}"' for k, v in attrs.items())


def render_subtree(
    tree: builder.WidgetTree,
    root_id: str,
    reg: registry.WidgetRendererRegistry,
) -> str:
    return "\n".join(_render_node(root_id, tree, reg, indent=0))


def render_msx(
    tree: builder.WidgetTree,
    reg: registry.WidgetRendererRegistry,
) -> str:
    lines: list[str] = []
    for rid in tree.adjacency.get(None, []):
        lines += _render_node(rid, tree, reg, indent=0)
    return "\n".join(lines)


def _render_node(
    node_id: str,
    tree: builder.WidgetTree,
    reg: registry.WidgetRendererRegistry,
    indent: int,
) -> list[str]:
    node = tree.resolve(node_id)
    tag = reg.get_tag_name(node)
    attr_str = _format_attrs(reg.get_attrs(node))

    child_ids = tree.adjacency.get(node_id, [])
    content = reg.get_content(node)
    prefix = "  " * indent

    if child_ids or content:
        lines: list[str] = [f"{prefix}<{tag}{attr_str}>"]
        if content:
            lines.append(f"{prefix}  {content}")
        for cid in child_ids:
            lines += _render_node(cid, tree, reg, indent + 1)
        lines.append(f"{prefix}</{tag}>")
    else:
        lines = [f"{prefix}<{tag}{attr_str}/>"]

    return lines


class WidgetMsxRenderer:
    def __init__(self, reg: registry.WidgetRendererRegistry) -> None:
        self._reg = reg

    def render_subtree(self, tree: builder.WidgetTree, root_id: str) -> str:
        return render_subtree(tree, root_id, self._reg)

    def render_widgets(
        self, widget_ids: Iterable[str], tree: builder.WidgetTree
    ) -> str:
        lines: list[str] = []
        for widget_id in widget_ids:
            lines += _render_node(widget_id, tree, self._reg, indent=0)
        return "\n".join(lines)

    def render_connections(
        self,
        widget_id: str,
        parsed: list[nodes.AnyWidget],
        tree: builder.WidgetTree,
    ) -> str:
        connection_lines: list[str] = []

        for widget in parsed:
            if not isinstance(widget, widget_schemas.ArrowWidget):
                continue
            if widget.start_ref_id == widget_id and widget.end_ref_id:
                connection_lines.append(
                    f'  <Connection arrow_id="{widget.id}" direction="outgoing"'
                    f' target_id="{widget.end_ref_id}"'
                    f' target_type="{tree.nodes[widget.end_ref_id].type}"'
                    f"/>"
                    if widget.end_ref_id in tree.nodes
                    else f'  <Connection arrow_id="{widget.id}" direction="outgoing"'
                    f' target_id="{widget.end_ref_id}"/>'
                )
            elif widget.end_ref_id == widget_id and widget.start_ref_id:
                connection_lines.append(
                    f'  <Connection arrow_id="{widget.id}" direction="incoming"'
                    f' source_id="{widget.start_ref_id}"'
                    f' source_type="{tree.nodes[widget.start_ref_id].type}"'
                    f"/>"
                    if widget.start_ref_id in tree.nodes
                    else f'  <Connection arrow_id="{widget.id}" direction="incoming"'
                    f' source_id="{widget.start_ref_id}"/>'
                )

        if not connection_lines:
            return f'<Connections widget_id="{widget_id}"/>'

        inner = "\n".join(connection_lines)
        return f'<Connections widget_id="{widget_id}">\n{inner}\n</Connections>'
