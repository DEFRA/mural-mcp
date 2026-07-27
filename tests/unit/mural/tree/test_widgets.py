import pydantic
import pytest

from app.mural.board.widgets import schemas as widgets

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


def test_shape_style_accepts_border_width_in_range():
    style = widgets.ShapeStyle(borderWidth=3, **_SHAPE_STYLE_KWARGS)
    assert style.border_width == 3


def test_shape_style_rejects_border_width_above_max():
    with pytest.raises(pydantic.ValidationError):
        widgets.ShapeStyle(borderWidth=8, **_SHAPE_STYLE_KWARGS)


def test_shape_style_rejects_border_width_below_min():
    with pytest.raises(pydantic.ValidationError):
        widgets.ShapeStyle(borderWidth=0, **_SHAPE_STYLE_KWARGS)


def test_shape_style_rejects_font_size_below_one():
    with pytest.raises(pydantic.ValidationError):
        widgets.ShapeStyle(
            borderWidth=1,
            fontSize=0,
            **{k: v for k, v in _SHAPE_STYLE_KWARGS.items() if k != "fontSize"},
        )


def test_arrow_widget_rejects_fewer_than_two_points():
    raw = _arrow_widget_raw(points=[{"x": 0, "y": 0}])
    with pytest.raises(pydantic.ValidationError):
        widgets.ArrowWidget(**raw)


def test_arrow_widget_accepts_two_points():
    raw = _arrow_widget_raw(points=[{"x": 0, "y": 0}, {"x": 10, "y": 10}])
    widget = widgets.ArrowWidget(**raw)
    assert len(widget.points) == 2


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
