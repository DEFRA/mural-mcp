import pydantic
import pytest

from app.integration.mural.board.widgets import schemas as widgets

_SHAPE_STYLE_KWARGS = {
    "backgroundColor": "#FFF",
    "borderColor": "#000",
    "borderStyle": "solid",
    "bold": False,
    "italic": False,
    "underline": False,
    "strike": False,
    "font": "proxima-nova",
    "fontColor": "#000",
    "fontSize": 14,
    "textAlign": "left",
}


def _arrow_widget_raw(points: list[dict]) -> dict:
    return {
        "id": "arrow-1",
        "type": "arrow",
        "title": "",
        "arrowType": "straight",
        "tip": "single",
        "stackable": False,
        "points": points,
        "style": {
            "strokeColor": "#000",
            "strokeStyle": "solid",
            "strokeWidth": 2,
        },
        "x": 0,
        "y": 0,
        "width": 100,
        "height": 50,
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
        "createdBy": {"id": "u1"},
        "createdOn": 0,
        "updatedBy": {"id": "u1"},
        "updatedOn": 0,
        "contentEditedBy": {"id": "u1"},
        "contentEditedOn": 0,
    }


class TestShapeStyle:
    def test_accepts_border_width_in_range(self):
        style = widgets.ShapeStyle(borderWidth=3, **_SHAPE_STYLE_KWARGS)
        assert style.border_width == 3

    def test_rejects_border_width_above_max(self):
        with pytest.raises(pydantic.ValidationError):
            widgets.ShapeStyle(borderWidth=8, **_SHAPE_STYLE_KWARGS)

    def test_rejects_border_width_below_min(self):
        with pytest.raises(pydantic.ValidationError):
            widgets.ShapeStyle(borderWidth=0, **_SHAPE_STYLE_KWARGS)

    def test_rejects_font_size_below_one(self):
        with pytest.raises(pydantic.ValidationError):
            widgets.ShapeStyle(
                borderWidth=1,
                fontSize=0,
                **{k: v for k, v in _SHAPE_STYLE_KWARGS.items() if k != "fontSize"},
            )


class TestArrowWidget:
    def test_rejects_fewer_than_two_points(self):
        raw = _arrow_widget_raw(points=[{"x": 0, "y": 0}])
        with pytest.raises(pydantic.ValidationError):
            widgets.ArrowWidget(**raw)

    def test_accepts_two_points(self):
        raw = _arrow_widget_raw(points=[{"x": 0, "y": 0}, {"x": 10, "y": 10}])
        widget = widgets.ArrowWidget(**raw)
        assert len(widget.points) == 2
