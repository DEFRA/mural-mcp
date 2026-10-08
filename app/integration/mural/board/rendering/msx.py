from collections.abc import Iterable

from app.integration.mural.board.parsing import models
from app.integration.mural.board.parsing import schemas as widget_schemas
from app.integration.mural.board.rendering import registry

_INDENT = "  "


def _format_attrs(attrs: dict[str, str]) -> str:
    if not attrs:
        return ""
    return "".join(f' {k}="{v}"' for k, v in attrs.items())


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
) -> list[str]:
    node = tree.resolve(node_id)
    tag = reg.get_tag_name(node)
    attr_str = _format_attrs(reg.get_attrs(node))

    child_ids = tree.adjacency.get(node_id, [])
    content = reg.get_content(node)
    prefix = _INDENT * indent

    if child_ids or content:
        lines: list[str] = [f"{prefix}<{tag}{attr_str}>"]
        if content:
            lines.append(f"{prefix}{_INDENT}{content}")
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
    attrs = f'arrow_id="{arrow_id}" direction="{direction}" {role}_id="{other_id}"'
    if other_id in tree.nodes:
        attrs += f' {role}_type="{tree.nodes[other_id].type}"'
    return f"  <Connection {attrs}/>"


class WidgetMsxRenderer:
    def __init__(self, reg: registry.WidgetRendererRegistry) -> None:
        self._reg = reg

    def render_subtree(self, tree: models.WidgetTree, root_id: str) -> str:
        return render_subtree(tree, root_id, self._reg)

    def render_widgets(self, widget_ids: Iterable[str], tree: models.WidgetTree) -> str:
        lines: list[str] = []
        for widget_id in widget_ids:
            lines += _render_node(widget_id, tree, self._reg, indent=0)
        return "\n".join(lines)

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
            return f'<Connections widget_id="{widget_id}"/>'

        inner = "\n".join(connection_lines)
        return f'<Connections widget_id="{widget_id}">\n{inner}\n</Connections>'
