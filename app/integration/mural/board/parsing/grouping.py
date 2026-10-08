"""How a flat widget list is grouped into an adjacency structure."""

import dataclasses
from collections.abc import Sequence
from typing import Protocol

from app.integration.mural.board.parsing import models


@dataclasses.dataclass(frozen=True)
class AdjacencyResult:
    """Output produced by a GroupingStrategy."""

    row_nodes: dict[str, models.TableRowNode]
    col_nodes: dict[str, models.TableColumnNode]
    adjacency: dict[str | None, list[str]]
    spatial_group_nodes: dict[str, models.SpatialGroupNode] = dataclasses.field(
        default_factory=dict
    )


class GroupingStrategy(Protocol):
    """Converts a flat widget list into an adjacency structure."""

    def group(self, widgets: Sequence[models.AnyWidget]) -> AdjacencyResult: ...
