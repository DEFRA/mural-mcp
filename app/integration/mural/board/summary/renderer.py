from app.integration.mural.board import registry
from app.integration.mural.board.summary import builder


def _format_attrs(attrs: dict[str, str]) -> str:
    if not attrs:
        return ""
    return "".join(f' {k}="{v}"' for k, v in attrs.items())


class SummaryMsxRenderer:
    def __init__(self, reg: registry.WidgetRendererRegistry) -> None:
        self._reg = reg

    def render(self, summary: builder.BoardSummary) -> str:
        tag = self._reg.get_tag_name(summary.root)
        attrs = _format_attrs(self._reg.get_attrs(summary.root))

        region_lines: list[str] = []
        for region in summary.regions:
            r_tag = self._reg.get_tag_name(region)
            r_attrs = _format_attrs(self._reg.get_attrs(region))
            region_lines.append(f"  <{r_tag}{r_attrs}/>")

        inner = "\n".join(region_lines)
        return f"<{tag}{attrs}>\n{inner}\n</{tag}>"
