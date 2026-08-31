from app.integration.mural.board.summary import builder as summary_builder
from app.integration.mural.board.widgets import builder, nodes
from app.integration.mural.board.widgets.strategies import (
    spatial as spatial_strategy,
)


def _user_ref(uid: str = "u1") -> dict:
    return {"id": uid}


def _base_widget(widget_id: str, widget_type: str, **extra) -> dict:
    return {
        "id": widget_id,
        "type": widget_type,
        "x": 0.0,
        "y": 0.0,
        "width": 100.0,
        "height": 100.0,
        "rotation": 0.0,
        "stackingOrder": 0,
        "presentationIndex": -1,
        "instruction": "",
        "hidden": False,
        "hideEditor": False,
        "hideOwner": False,
        "invisible": False,
        "locked": False,
        "lockedByFacilitator": False,
        "createdBy": _user_ref(),
        "createdOn": 0,
        "updatedBy": _user_ref(),
        "updatedOn": 0,
        "contentEditedBy": _user_ref(),
        "contentEditedOn": 0,
        **extra,
    }


def _sticky(
    widget_id: str,
    text: str = "",
    font_size: float = 14,
    parent_id: str | None = None,
) -> dict:
    return _base_widget(
        widget_id,
        "sticky note",
        title=text or widget_id,
        shape="rectangle",
        parentId=parent_id,
        style={
            "backgroundColor": "#FFFF00FF",
            "bold": False,
            "border": False,
            "italic": False,
            "underline": False,
            "strike": False,
            "font": "proxima-nova",
            "fontSize": font_size,
            "textAlign": "left",
        },
        text=text,
    )


def _area(
    widget_id: str,
    title: str,
    x: float = 0,
    y: float = 0,
    w: float = 500,
    h: float = 400,
) -> dict:
    return _base_widget(
        widget_id,
        "area",
        x=x,
        y=y,
        width=w,
        height=h,
        title=title,
        layout="free",
        showTitle=True,
        style={
            "backgroundColor": "#FFFFFF33",
            "borderColor": "#000000FF",
            "borderStyle": "dashed",
            "borderWidth": 1,
            "titleFontSize": 24.0,
        },
    )


class TestBuild:
    def test_empty_board_has_no_regions(self) -> None:
        tree = builder.WidgetTree.build([])

        summary = summary_builder.BoardSummary.build(tree, "mural-abc")

        assert summary.root.id == "mural-abc"
        assert summary.regions == []

    def test_area_widget_becomes_a_region(self) -> None:
        parsed = nodes.parse_widgets(
            [_area("area-1", "Sprint Planning", x=10, y=20, w=300, h=200)]
        )
        tree = builder.WidgetTree.build(parsed)

        summary = summary_builder.BoardSummary.build(tree, "mural-abc")

        assert len(summary.regions) == 1
        region = summary.regions[0]
        assert region.id == "area-1"
        assert region.label == "Sprint Planning"
        assert (region.x, region.y, region.width, region.height) == (10, 20, 300, 200)

    def test_counts_descendants_of_an_area(self) -> None:
        parsed = nodes.parse_widgets(
            [
                _area("area-1", "Sprint Planning"),
                _sticky("s1", text="a", parent_id="area-1"),
                _sticky("s2", text="b", parent_id="area-1"),
            ]
        )
        tree = builder.WidgetTree.build(parsed)

        summary = summary_builder.BoardSummary.build(tree, "mural-abc")

        assert summary.regions[0].count == 2

    def test_ungrouped_widgets_produce_no_regions(self) -> None:
        """Loose sticky notes at the top level (no area, no spatial
        grouping) are not regions -- only AreaWidget and SpatialGroupNode
        roots are."""
        parsed = nodes.parse_widgets([_sticky("s1", text="loose note")])
        tree = builder.WidgetTree.build(parsed)

        summary = summary_builder.BoardSummary.build(tree, "mural-abc")

        assert summary.regions == []

    def test_spatial_group_becomes_a_region_with_an_inferred_label(self) -> None:
        parsed = nodes.parse_widgets(
            [
                _sticky("s1", text="Big Idea", font_size=80, parent_id=None),
                _sticky("s2", text="detail", parent_id=None),
            ]
        )
        # Force both widgets into the same cluster regardless of their (0,0)
        # positions by using a generous cluster_gap.
        tree = builder.WidgetTree.build(
            parsed, spatial_strategy.SpatialGroupingStrategy(cluster_gap=10_000)
        )

        summary = summary_builder.BoardSummary.build(tree, "mural-abc")

        assert len(summary.regions) == 1
        region = summary.regions[0]
        # Same-size widgets (no clear anchor by area) both land under a
        # synthetic SpatialGroupNode, so both are counted as its children.
        assert region.count == 2
        assert region.label == "Big Idea"
