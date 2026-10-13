from app.integration.mural.board.parsing import parser
from app.integration.mural.board.parsing import schemas as widgets
from app.integration.mural.board.rendering import msx, registry
from tests.fixtures import mural

_REG = registry.build_default_registry()


def create_sticky_widget(
    widget_id: str, parent_id: str | None = None, text: str = "Test"
) -> widgets.StickyNoteWidget:
    """Helper to create a sticky note widget."""
    return widgets.StickyNoteWidget(
        id=widget_id,
        type="sticky note",
        parentId=parent_id,
        x=0,
        y=0,
        width=100,
        height=100,
        rotation=0,
        stackingOrder=0,
        presentationIndex=-1,
        instruction="",
        hidden=False,
        hideEditor=False,
        hideOwner=False,
        invisible=False,
        locked=False,
        lockedByFacilitator=False,
        createdBy={"id": "user1"},
        createdOn=1234567890,
        updatedBy={"id": "user1"},
        updatedOn=1234567890,
        contentEditedBy={"id": "user1"},
        contentEditedOn=1234567890,
        title="Note",
        shape="rectangle",
        text=text,
        style=widgets.StickyNoteStyle(
            backgroundColor="#FFFFFF",
            bold=False,
            border=False,
            italic=False,
            underline=False,
            strike=False,
            font="proxima-nova",
            fontSize=14,
            textAlign="left",
        ),
    )


class TestRenderMsx:
    def test_empty_tree(self) -> None:
        tree = parser.build_tree([])
        result = msx.render_msx(tree, _REG)
        assert result == ""

    def test_single_leaf(self) -> None:
        """A widget with text is never self-closing -- the text has to live
        somewhere."""
        widget = create_sticky_widget("w1", text="Hello")
        tree = parser.build_tree([widget])
        result = msx.render_msx(tree, _REG)
        assert 'id="w1"' in result
        assert "</StickyNote>" in result
        assert "/>" not in result

    def test_parent_with_children(self) -> None:
        """The child tag is nested inside the parent's open/close pair, not
        merely present."""
        parent = create_sticky_widget("parent", parent_id=None, text="Parent")
        child = create_sticky_widget("child", parent_id="parent", text="Child")
        tree = parser.build_tree([parent, child])
        result = msx.render_msx(tree, _REG)

        parent_open = result.index('<StickyNote id="parent"')
        child_open = result.index('<StickyNote id="child"')
        parent_close = result.rindex("</StickyNote>")

        assert parent_open < child_open < parent_close

    def test_multiple_siblings(self) -> None:
        w1 = create_sticky_widget("w1", text="First")
        w2 = create_sticky_widget("w2", text="Second")
        tree = parser.build_tree([w1, w2])
        result = msx.render_msx(tree, _REG)
        assert result.count("<StickyNote") == 2

    def test_sticky_text_as_inner_content(self) -> None:
        """Sticky note text renders inside the tag, not as an attribute."""
        widget = create_sticky_widget("w1", text="Hello")
        tree = parser.build_tree([widget])
        result = msx.render_msx(tree, _REG)
        assert 'text="Hello"' not in result
        assert "Hello" in result
        assert "</StickyNote>" in result

    def test_sticky_html_text_takes_precedence(self) -> None:
        """html_text is used as inner content when both text and html_text
        are set."""
        widget = create_sticky_widget("w1", text="plain")
        widget = widget.model_copy(update={"html_text": "<p>rich</p>"})
        tree = parser.build_tree([widget])
        result = msx.render_msx(tree, _REG)
        assert "rich" in result
        assert "<p>" not in result
        assert "plain" not in result

    def test_sticky_html_text_is_reduced_to_plain_lines(self) -> None:
        widget = create_sticky_widget("w1").model_copy(
            update={"html_text": "<p>one <b>two</b></p><p>three &amp; four</p>"}
        )
        result = msx.render_msx(parser.build_tree([widget]), _REG)
        assert "\n  one two\n  three &amp; four\n" in result

    def test_text_content_is_escaped(self) -> None:
        widget = create_sticky_widget("w1", text="1 < 2 </StickyNote>")
        result = msx.render_msx(parser.build_tree([widget]), _REG)
        assert "1 &lt; 2 &lt;/StickyNote&gt;" in result
        assert result.count("</StickyNote>") == 1

    def test_attribute_values_are_escaped(self) -> None:
        raw = mural.area("a1", 'Say "hi" <now>')
        result = msx.render_msx(parser.build_tree(parser.parse_widgets([raw])), _REG)
        assert 'title="Say &quot;hi&quot; &lt;now&gt;"' in result

    def test_unknown_widget_renders_with_its_type(self) -> None:
        raw = mural.base_widget("d1", "drawing")
        result = msx.render_msx(parser.build_tree(parser.parse_widgets([raw])), _REG)
        assert result == '<Widget id="d1" type="drawing"/>'

    def test_sticky_no_text_is_self_closing(self) -> None:
        """Sticky note with no text and no children renders as self-closing
        tag."""
        widget = create_sticky_widget("w1", text="")
        widget = widget.model_copy(update={"text": None})
        tree = parser.build_tree([widget])
        result = msx.render_msx(tree, _REG)
        assert "/>" in result
        assert "</StickyNote>" not in result


class TestSummaryEscaping:
    def test_region_labels_are_escaped(self) -> None:
        from app.integration.mural.board.parsing import summary
        from app.integration.mural.board.rendering import summary as summary_renderer

        raw = mural.area("a1", 'Q&A "live"')
        tree = parser.build_tree(parser.parse_widgets([raw]))
        result = summary_renderer.SummaryMsxRenderer(_REG).render(
            summary.BoardSummary.build(tree, "m1")
        )
        assert 'label="Q&amp;A &quot;live&quot;"' in result
