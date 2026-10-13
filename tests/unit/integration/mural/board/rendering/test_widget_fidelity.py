"""What the MSX for each widget type says about the board's content."""

from typing import Any

from app.integration.mural.board.parsing import parser
from app.integration.mural.board.rendering import msx, registry
from tests.fixtures import mural

_REG = registry.build_default_registry()


def _render(*raw: dict[str, Any]) -> str:
    return msx.render_msx(parser.build_tree(parser.parse_widgets(list(raw))), _REG)


class TestImage:
    def test_never_exposes_the_signed_url(self) -> None:
        result = _render(mural.image("i1"))
        assert "assets.example.com" not in result
        assert "sig=" not in result

    def test_says_it_can_be_viewed(self) -> None:
        result = _render(mural.image("i1"))
        assert 'viewable="true"' in result
        assert "restricted" not in result

    def test_download_restriction_is_flagged(self) -> None:
        result = _render(mural.image("i1", url=None))
        assert 'restricted="true"' in result
        assert "viewable" not in result

    def test_describes_the_image_without_loading_it(self) -> None:
        result = _render(
            mural.image(
                "i1",
                title="Journey map",
                description="Flow of the application",
                caption="Draft 2",
                link="https://example.com/x",
            )
        )
        assert 'title="Journey map"' in result
        assert 'alt="Flow of the application"' in result
        assert 'w="400.0"' in result
        assert 'h="200.0"' in result
        assert 'link="https://example.com/x"' in result
        assert "Draft 2" in result

    def test_cropped_only_when_a_mask_is_set(self) -> None:
        assert "cropped" not in _render(mural.image("i1"))
        mask = {"top": 0, "left": 0, "width": 10, "height": 10}
        assert 'cropped="true"' in _render(mural.image("i1", mask=mask))


class TestFile:
    def test_never_exposes_the_signed_url(self) -> None:
        assert "sig=" not in _render(mural.file_widget("f1"))

    def test_flags_a_preview_and_link(self) -> None:
        result = _render(
            mural.file_widget(
                "f1", previewUrl="https://assets.example.com/p.png", link="https://m/f1"
            )
        )
        assert 'has_preview="true"' in result
        assert 'link="https://m/f1"' in result
        assert "p.png" not in result

    def test_no_preview_flag_without_a_preview(self) -> None:
        assert "has_preview" not in _render(mural.file_widget("f1"))


class TestArrow:
    def test_label_text_is_the_content(self) -> None:
        label = {
            "format": {
                "color": "#000000FF",
                "fontFamily": "proxima-nova",
                "bold": False,
                "italic": False,
                "textAlign": "center",
                "fontSize": 14,
            },
            "labels": [
                {"x": 0, "y": 0, "height": 10, "width": 10, "text": "yes"},
                {"x": 0, "y": 0, "height": 10, "width": 10, "text": "if valid"},
            ],
        }
        result = _render(mural.arrow("a1", start_ref="s1", end_ref="s2", label=label))
        assert "yes / if valid" in result
        assert "</Arrow>" in result

    def test_unlabelled_arrow_is_self_closing(self) -> None:
        assert _render(mural.arrow("a1")).endswith("/>")


class TestComment:
    def test_includes_replies_with_their_authors(self) -> None:
        replies = [
            {"message": "Agreed", "user": {"id": "u2", "firstName": "Sam"}},
            {"message": "Fixed", "user": {"id": "u3", "alias": "pat"}},
        ]
        result = _render(
            mural.comment(
                "c1", "Is this right?", replies=replies, referenceWidgetId="s1"
            )
        )
        assert 'on="s1"' in result
        assert "Is this right?\n  ↳ Sam: Agreed\n  ↳ pat: Fixed" in result

    def test_resolved_is_flagged(self) -> None:
        assert "resolved" not in _render(mural.comment("c1", "hi"))
        resolved = _render(mural.comment("c1", "hi", resolvedBy={"id": "u2"}))
        assert 'resolved="true"' in resolved


class TestHyperlinks:
    def test_sticky_note_link_is_an_href(self) -> None:
        result = _render(mural.sticky("s1", text="docs", hyperlink="https://x.test/a"))
        assert 'href="https://x.test/a"' in result

    def test_no_href_without_a_link(self) -> None:
        assert "href" not in _render(mural.sticky("s1", text="docs"))


class TestHiddenWidgets:
    def test_hidden_and_invisible_widgets_are_left_out(self) -> None:
        result = _render(
            mural.sticky("shown", text="a"),
            mural.sticky("hid", text="b", hidden=True),
            mural.sticky("invis", text="c", invisible=True),
        )
        assert 'id="shown"' in result
        assert "hid" not in result
        assert "invis" not in result

    def test_children_of_a_visible_parent_are_filtered_too(self) -> None:
        result = _render(
            mural.area("a1", "Area"),
            mural.sticky("s1", text="a", parent_id="a1"),
            mural.sticky("s2", text="b", parent_id="a1", hidden=True),
        )
        assert 'id="s1"' in result
        assert "s2" not in result
