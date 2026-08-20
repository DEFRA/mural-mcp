from app.integration.mural.board.summary import nodes


def test_region_node_holds_its_fields() -> None:
    region = nodes.RegionNode(
        id="area-1",
        label="Sprint Planning",
        count=3,
        x=1.0,
        y=2.0,
        width=3.0,
        height=4.0,
    )

    assert region.id == "area-1"
    assert region.label == "Sprint Planning"
    assert region.count == 3
    assert (region.x, region.y, region.width, region.height) == (1.0, 2.0, 3.0, 4.0)


def test_board_summary_node_holds_the_mural_id() -> None:
    root = nodes.BoardSummaryNode(id="mural-abc")

    assert root.id == "mural-abc"
