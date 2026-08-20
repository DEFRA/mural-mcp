from app.integration.mural.board.widgets import nodes
from app.integration.mural.board.widgets import schemas as widgets
from app.integration.mural.board.widgets.strategies import parent_id, spatial


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


def test_strategy_flat_widgets() -> None:
    """Test ParentIdStrategy with flat (all top-level) widgets."""
    w1 = create_sticky_widget("w1")
    w2 = create_sticky_widget("w2")
    strategy = parent_id.ParentIdStrategy()
    result = strategy.group([w1, w2])
    assert None in result.adjacency
    assert set(result.adjacency[None]) == {"w1", "w2"}


def test_strategy_parent_child_hierarchy() -> None:
    """Test ParentIdStrategy with parent-child relationships."""
    parent = create_sticky_widget("parent")
    child1 = create_sticky_widget("child1", parent_id="parent")
    child2 = create_sticky_widget("child2", parent_id="parent")
    strategy = parent_id.ParentIdStrategy()
    result = strategy.group([parent, child1, child2])
    assert result.adjacency[None] == ["parent"]
    assert set(result.adjacency["parent"]) == {"child1", "child2"}


def test_strategy_table_expansion() -> None:
    """Test that ParentIdStrategy expands table widgets into row nodes."""
    table = widgets.TableWidget(
        id="table-1",
        type="table",
        x=0,
        y=0,
        width=300,
        height=200,
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
        title="Table",
        autoResize=True,
        columns=[
            widgets.TableColumn(columnId="col-1", width=100),
            widgets.TableColumn(columnId="col-2", width=100),
        ],
        rows=[
            widgets.TableRow(rowId="row-1", height=50, minHeight=50),
            widgets.TableRow(rowId="row-2", height=50, minHeight=50),
        ],
        style=widgets.TableStyle(borderColor="#000", borderWidth=1),
    )
    strategy = parent_id.ParentIdStrategy()
    result = strategy.group([table])
    assert "row-1" in result.row_nodes
    assert "row-2" in result.row_nodes
    assert result.row_nodes["row-1"].table_id == "table-1"


def test_strategy_table_cell_placement() -> None:
    """Test that ParentIdStrategy places table cells under correct column nodes."""
    table = widgets.TableWidget(
        id="table-1",
        type="table",
        x=0,
        y=0,
        width=300,
        height=200,
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
        title="Table",
        autoResize=True,
        columns=[
            widgets.TableColumn(columnId="col-1", width=100),
        ],
        rows=[
            widgets.TableRow(rowId="row-1", height=50, minHeight=50),
        ],
        style=widgets.TableStyle(borderColor="#000", borderWidth=1),
    )
    cell = widgets.TableCellWidget(
        id="cell-1",
        type="table cell",
        rowId="row-1",
        columnId="col-1",
        colSpan=1,
        rowSpan=1,
        x=0,
        y=0,
        width=100,
        height=50,
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
        style=widgets.TableCellStyle(backgroundColor="#FFF"),
    )
    strategy = parent_id.ParentIdStrategy()
    result = strategy.group([table, cell])
    col_node_id = "row-1/col-1"
    assert col_node_id in result.col_nodes
    assert result.adjacency[col_node_id] == ["cell-1"]


_USER = {"id": "user1"}
_WIDGET_BASE = {
    "rotation": 0,
    "stackingOrder": 0,
    "presentationIndex": -1,
    "instruction": "",
    "hidden": False,
    "hideEditor": False,
    "hideOwner": False,
    "invisible": False,
    "locked": False,
    "lockedByFacilitator": False,
    "createdBy": _USER,
    "createdOn": 1234567890,
    "updatedBy": _USER,
    "updatedOn": 1234567890,
    "contentEditedBy": _USER,
    "contentEditedOn": 1234567890,
}

_SHAPE_STYLE = widgets.ShapeStyle(
    backgroundColor="#FFF",
    borderColor="#000",
    borderStyle="solid",
    borderWidth=1,
    bold=False,
    italic=False,
    underline=False,
    strike=False,
    font="proxima-nova",
    fontColor="#000",
    fontSize=14,
    textAlign="left",
)


def make_shape(
    widget_id: str, x: float, y: float, w: float, h: float
) -> widgets.ShapeWidget:
    return widgets.ShapeWidget(
        id=widget_id,
        type="shape",
        x=x,
        y=y,
        width=w,
        height=h,
        title="",
        text="",
        shape="rectangle",
        style=_SHAPE_STYLE,
        **_WIDGET_BASE,
    )


def test_spatial_single_widget_at_root() -> None:
    w = make_shape("w1", 0, 0, 100, 100)
    result = spatial.SpatialGroupingStrategy().group([w])
    assert result.adjacency.get(None) == ["w1"]
    assert not result.spatial_group_nodes


def test_spatial_isolated_widgets_each_at_root() -> None:
    # Far apart — no cluster
    a = make_shape("a", 0, 0, 100, 100)
    b = make_shape("b", 5000, 0, 100, 100)
    result = spatial.SpatialGroupingStrategy(cluster_gap=100).group([a, b])
    assert set(result.adjacency.get(None, [])) == {"a", "b"}
    assert not result.spatial_group_nodes


def test_spatial_large_anchor_becomes_parent() -> None:
    # Screen (500×800) + small slug (100×30) placed 50px above it — within gap
    screen = make_shape("screen", 0, 100, 500, 800)
    slug = make_shape("slug", 50, 50, 200, 30)  # 50px above screen top edge
    result = spatial.SpatialGroupingStrategy(cluster_gap=100, anchor_ratio=3.0).group(
        [screen, slug]
    )
    # screen area = 400 000, slug area = 6 000 → ratio >> 3
    assert result.adjacency.get(None) == ["screen"]
    assert set(result.adjacency.get("screen", [])) == {"slug"}
    assert not result.spatial_group_nodes


def test_spatial_no_clear_anchor_creates_group_node() -> None:
    # Two equal-size shapes close together
    a = make_shape("a", 0, 0, 100, 100)
    b = make_shape("b", 150, 0, 100, 100)  # 50px gap
    result = spatial.SpatialGroupingStrategy(cluster_gap=100, anchor_ratio=3.0).group(
        [a, b]
    )
    assert not result.adjacency.get("a")
    assert not result.adjacency.get("b")
    assert result.spatial_group_nodes
    group_id = next(iter(result.spatial_group_nodes))
    assert set(result.adjacency.get(group_id, [])) == {"a", "b"}
    assert isinstance(result.spatial_group_nodes[group_id], nodes.SpatialGroupNode)


def test_spatial_slug_above_correct_screen() -> None:
    # Two screens side by side, each with its own slug above it.
    # Slug positions are chosen so each is closest (by bbox distance) to its own screen.
    screen_a = make_shape("screen_a", 0, 200, 400, 600)
    slug_a = make_shape("slug_a", 50, 150, 200, 30)  # 20px above screen_a

    screen_b = make_shape("screen_b", 600, 200, 400, 600)
    slug_b = make_shape("slug_b", 650, 150, 200, 30)  # 20px above screen_b

    result = spatial.SpatialGroupingStrategy(cluster_gap=100, anchor_ratio=3.0).group(
        [screen_a, slug_a, screen_b, slug_b]
    )

    # Each screen is anchor of its own cluster
    assert "slug_a" in result.adjacency.get("screen_a", [])
    assert "slug_b" in result.adjacency.get("screen_b", [])
    # Slugs must not be swapped
    assert "slug_b" not in result.adjacency.get("screen_a", [])
    assert "slug_a" not in result.adjacency.get("screen_b", [])


def test_spatial_tables_only_expanded_when_present() -> None:
    w = make_shape("w1", 0, 0, 100, 100)
    result = spatial.SpatialGroupingStrategy().group([w])
    assert result.row_nodes == {}
    assert result.col_nodes == {}
