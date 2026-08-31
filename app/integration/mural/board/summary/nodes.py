import dataclasses


@dataclasses.dataclass
class RegionNode:
    """A top-level region in the board summary view.

    Produced from an AreaWidget or SpatialGroupNode; never stored in WidgetTree.
    """

    id: str
    label: str
    count: int
    x: float
    y: float
    width: float
    height: float


@dataclasses.dataclass
class BoardSummaryNode:
    """Root of the board summary tree.

    Never stored in WidgetTree.
    """

    id: str  # mural_id
