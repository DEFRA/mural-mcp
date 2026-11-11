"""Plain-text extraction for widget rich text."""

import html.parser

_BLOCK_TAGS = frozenset(
    {"br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}
)


class _TextExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:  # noqa: ARG002
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def html_to_text(value: str) -> str:
    """Strip markup from widget html text, keeping line breaks between blocks."""
    extractor = _TextExtractor()
    extractor.feed(value)
    extractor.close()
    lines = (line.strip() for line in "".join(extractor.parts).splitlines())
    return "\n".join(line for line in lines if line)
