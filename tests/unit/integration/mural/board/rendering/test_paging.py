import xml.etree.ElementTree as ET

from app.integration.mural.board.parsing import parser
from app.integration.mural.board.rendering import msx, paging, registry
from tests.fixtures import mural

_RENDERER = msx.WidgetMsxRenderer(registry.build_default_registry())


def _parse(text: str) -> ET.Element:
    """Parse MSX as XML to prove it is well-formed. The input is this
    renderer's own output from fixed fixtures, not untrusted data."""
    return ET.fromstring(text)  # noqa: S314


def _render(item_id: str) -> str:
    return f"<{item_id}/>"


class TestPaginate:
    def test_everything_fits(self) -> None:
        chunks, page = paging.paginate(["a", "b"], _render, offset=0, budget=100)
        assert chunks == ["<a/>", "<b/>"]
        assert page.model_dump() == {
            "shown": 2,
            "total": 2,
            "offset": 0,
            "next_offset": None,
            "child_regions": [],
        }

    def test_stops_before_the_item_that_would_go_over(self) -> None:
        chunks, page = paging.paginate(
            ["aaaa", "bbbb", "cccc"], _render, offset=0, budget=15
        )
        assert chunks == ["<aaaa/>", "<bbbb/>"][: len(chunks)]
        assert page.next_offset == len(chunks)
        assert 0 < len(chunks) < 3

    def test_continues_from_the_offset(self) -> None:
        chunks, page = paging.paginate(["a", "b", "c"], _render, offset=1, budget=100)
        assert chunks == ["<b/>", "<c/>"]
        assert (page.shown, page.offset, page.next_offset) == (2, 1, None)

    def test_an_item_bigger_than_the_budget_is_still_shown(self) -> None:
        chunks, page = paging.paginate(["huge", "b"], _render, offset=0, budget=1)
        assert chunks == ["<huge/>"]
        assert page.next_offset == 1

    def test_an_offset_past_the_end_is_empty_and_complete(self) -> None:
        chunks, page = paging.paginate(["a"], _render, offset=5, budget=100)
        assert chunks == []
        assert (page.shown, page.total, page.next_offset) == (0, 1, None)

    def test_only_renders_what_it_returns(self) -> None:
        rendered: list[str] = []

        def render(item_id: str) -> str:
            rendered.append(item_id)
            return "x" * 10

        paging.paginate([str(i) for i in range(100)], render, offset=0, budget=25)
        assert len(rendered) <= 4


def _region_tree(count: int, text_size: int = 500):
    widgets = [mural.area("a1", "Big area")]
    widgets += [
        mural.sticky(f"s{i}", text="x" * text_size, parent_id="a1")
        for i in range(count)
    ]
    return parser.build_tree(parser.parse_widgets(widgets))


class TestRegionPage:
    def test_every_part_is_well_formed_msx(self) -> None:
        tree = _region_tree(50)
        offset: int | None = 0
        while offset is not None:
            text, page = _RENDERER.render_region_page(
                tree, "a1", offset=offset, budget=5_000
            )
            _parse(text)
            offset = page.next_offset

    def test_parts_together_hold_every_child_once(self) -> None:
        tree = _region_tree(50)
        seen: list[str] = []
        offset: int | None = 0
        while offset is not None:
            text, page = _RENDERER.render_region_page(
                tree, "a1", offset=offset, budget=5_000
            )
            seen += [el.get("id") for el in _parse(text)]
            offset = page.next_offset
        assert seen == [f"s{i}" for i in range(50)]

    def test_each_part_keeps_the_region_tag(self) -> None:
        text, _ = _RENDERER.render_region_page(
            _region_tree(50), "a1", offset=20, budget=5_000
        )
        root = _parse(text)
        assert root.tag == "Area"
        assert root.get("title") == "Big area"

    def test_lists_child_areas_with_their_counts(self) -> None:
        widgets = [
            mural.area("a1", "Outer"),
            {**mural.area("a2", "Inner"), "parentId": "a1"},
            mural.sticky("s1", parent_id="a2"),
            mural.sticky("s2", parent_id="a2"),
        ]
        tree = parser.build_tree(parser.parse_widgets(widgets))
        _, page = _RENDERER.render_region_page(tree, "a1")
        assert [(c.id, c.title, c.count) for c in page.child_regions] == [
            ("a2", "Inner", 2)
        ]

    def test_an_empty_region_is_complete(self) -> None:
        tree = parser.build_tree(parser.parse_widgets([mural.area("a1", "Empty")]))
        text, page = _RENDERER.render_region_page(tree, "a1")
        assert text.startswith("<Area")
        assert (page.total, page.next_offset) == (0, None)
