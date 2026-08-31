from app.integration.mural.board.widgets import builder
from app.integration.mural.board.widgets import schemas as widgets


def create_sticky_widget(
    widget_id: str, parent_id: str | None = None
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


class TestBuild:
    def test_empty_tree(self) -> None:
        tree = builder.WidgetTree.build([])
        assert tree.nodes == {}
        assert tree.row_nodes == {}
        assert tree.col_nodes == {}
        assert tree.adjacency == {}

    def test_single_widget(self) -> None:
        widget = create_sticky_widget("w1")
        tree = builder.WidgetTree.build([widget])
        assert tree.nodes["w1"] == widget
        assert tree.adjacency[None] == ["w1"]
        assert tree.adjacency.get("w1", []) == []

    def test_parent_child_hierarchy(self) -> None:
        parent = create_sticky_widget("parent", parent_id=None)
        child1 = create_sticky_widget("child1", parent_id="parent")
        child2 = create_sticky_widget("child2", parent_id="parent")
        tree = builder.WidgetTree.build([parent, child1, child2])
        assert tree.adjacency[None] == ["parent"]
        assert set(tree.adjacency["parent"]) == {"child1", "child2"}


class TestResolve:
    def test_resolve_widget_by_id(self) -> None:
        widget = create_sticky_widget("w1")
        tree = builder.WidgetTree.build([widget])
        resolved = tree.resolve("w1")
        assert resolved == widget


class TestChildren:
    def test_returns_empty_for_leaf(self) -> None:
        widget = create_sticky_widget("w1")
        tree = builder.WidgetTree.build([widget])
        children = tree.children("w1")
        assert children == []

    def test_returns_all_direct_children(self) -> None:
        parent = create_sticky_widget("parent", parent_id=None)
        child1 = create_sticky_widget("child1", parent_id="parent")
        child2 = create_sticky_widget("child2", parent_id="parent")
        tree = builder.WidgetTree.build([parent, child1, child2])
        children = tree.children("parent")
        assert len(children) == 2
        child_ids = {c.id for c in children}
        assert child_ids == {"child1", "child2"}


class TestStr:
    def test_string_representation_includes_root_and_widget_type(self) -> None:
        parent = create_sticky_widget("parent", parent_id=None)
        child = create_sticky_widget("child", parent_id="parent")
        tree = builder.WidgetTree.build([parent, child])
        tree_str = str(tree)
        assert "<root>" in tree_str
        assert "sticky note" in tree_str
