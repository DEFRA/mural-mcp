from app.integration.mural.board import registry
from app.integration.mural.board.renderers import msx
from app.integration.mural.board.widgets import builder
from app.integration.mural.board.widgets import schemas as widgets

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


def test_render_empty_tree() -> None:
    """Test rendering an empty tree."""
    tree = builder.WidgetTree.build([])
    result = msx.render_msx(tree, _REG)
    assert result == ""


def test_render_single_leaf() -> None:
    """Test rendering a single top-level widget (self-closing tag)."""
    widget = create_sticky_widget("w1", text="Hello")
    tree = builder.WidgetTree.build([widget])
    result = msx.render_msx(tree, _REG)
    assert "<StickyNote" in result
    assert 'id="w1"' in result
    assert "/>" in result or "</StickyNote>" in result


def test_render_parent_with_children() -> None:
    """Test rendering a parent widget with children (nested tags)."""
    parent = create_sticky_widget("parent", parent_id=None, text="Parent")
    child = create_sticky_widget("child", parent_id="parent", text="Child")
    tree = builder.WidgetTree.build([parent, child])
    result = msx.render_msx(tree, _REG)
    assert "<StickyNote" in result
    assert "</StickyNote>" in result
    lines = result.strip().split("\n")
    assert len(lines) >= 2


def test_render_multiple_siblings() -> None:
    """Test rendering multiple sibling widgets."""
    w1 = create_sticky_widget("w1", text="First")
    w2 = create_sticky_widget("w2", text="Second")
    tree = builder.WidgetTree.build([w1, w2])
    result = msx.render_msx(tree, _REG)
    assert result.count("<StickyNote") == 2


def test_format_attrs_empty() -> None:
    """Test formatting empty attributes."""
    attrs = {}
    result = msx._format_attrs(attrs)
    assert result == ""


def test_format_attrs_single() -> None:
    """Test formatting a single attribute."""
    attrs = {"id": "widget-1"}
    result = msx._format_attrs(attrs)
    assert result == ' id="widget-1"'


def test_format_attrs_multiple() -> None:
    """Test formatting multiple attributes."""
    attrs = {"id": "w1", "text": "Hello", "color": "red"}
    result = msx._format_attrs(attrs)
    assert ' id="w1"' in result
    assert ' text="Hello"' in result
    assert ' color="red"' in result


def test_render_sticky_text_as_inner_content() -> None:
    """Sticky note text renders inside the tag, not as an attribute."""
    widget = create_sticky_widget("w1", text="Hello")
    tree = builder.WidgetTree.build([widget])
    result = msx.render_msx(tree, _REG)
    assert 'text="Hello"' not in result
    assert "Hello" in result
    assert "</StickyNote>" in result


def test_render_sticky_html_text_takes_precedence() -> None:
    """html_text is used as inner content when both text and html_text are set."""
    widget = create_sticky_widget("w1", text="plain")
    widget = widget.model_copy(update={"html_text": "<p>rich</p>"})
    tree = builder.WidgetTree.build([widget])
    result = msx.render_msx(tree, _REG)
    assert "<p>rich</p>" in result
    assert "plain" not in result


def test_render_sticky_no_text_is_self_closing() -> None:
    """Sticky note with no text and no children renders as self-closing tag."""
    widget = create_sticky_widget("w1", text="")
    widget = widget.model_copy(update={"text": None})
    tree = builder.WidgetTree.build([widget])
    result = msx.render_msx(tree, _REG)
    assert "/>" in result
    assert "</StickyNote>" not in result
