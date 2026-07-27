import pydantic
import pytest

from app.mural.board.widgets import nodes
from app.mural.board.widgets import schemas as widgets


def test_parse_sticky_note_widget() -> None:
    """Test parsing a sticky note widget."""
    raw = {
        "id": "widget-1",
        "type": "sticky note",
        "title": "Note",
        "shape": "rectangle",
        "x": 0,
        "y": 0,
        "width": 100,
        "height": 100,
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
        "createdBy": {"id": "user1"},
        "createdOn": 1234567890,
        "updatedBy": {"id": "user1"},
        "updatedOn": 1234567890,
        "contentEditedBy": {"id": "user1"},
        "contentEditedOn": 1234567890,
        "style": {
            "backgroundColor": "#FFFFFF",
            "bold": False,
            "border": False,
            "font": "proxima-nova",
            "fontSize": 14,
            "italic": False,
            "strike": False,
            "textAlign": "left",
            "underline": False,
        },
        "text": "Test note",
    }
    parsed = nodes.parse_widgets([raw])
    assert len(parsed) == 1
    assert isinstance(parsed[0], widgets.StickyNoteWidget)
    assert parsed[0].title == "Note"
    assert parsed[0].text == "Test note"


def test_parse_multiple_widgets() -> None:
    """Test parsing multiple widgets of different types."""
    shape_raw = {
        "id": "shape-1",
        "type": "shape",
        "title": "My Shape",
        "shape": "circle",
        "x": 0,
        "y": 0,
        "width": 100,
        "height": 100,
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
        "createdBy": {"id": "user1"},
        "createdOn": 1234567890,
        "updatedBy": {"id": "user1"},
        "updatedOn": 1234567890,
        "contentEditedBy": {"id": "user1"},
        "contentEditedOn": 1234567890,
        "text": "Shape text",
        "style": {
            "backgroundColor": "#FFFFFF",
            "borderColor": "#000000",
            "borderStyle": "solid",
            "borderWidth": 1,
            "bold": False,
            "italic": False,
            "underline": False,
            "strike": False,
            "font": "proxima-nova",
            "fontColor": "#000000",
            "fontSize": 14,
            "textAlign": "left",
        },
    }
    icon_raw = {
        "id": "icon-1",
        "type": "icon",
        "title": "Icon",
        "name": "1234567",
        "x": 0,
        "y": 0,
        "width": 50,
        "height": 50,
        "rotation": 0,
        "stackingOrder": 1,
        "presentationIndex": -1,
        "instruction": "",
        "hidden": False,
        "hideEditor": False,
        "hideOwner": False,
        "invisible": False,
        "locked": False,
        "lockedByFacilitator": False,
        "createdBy": {"id": "user1"},
        "createdOn": 1234567890,
        "updatedBy": {"id": "user1"},
        "updatedOn": 1234567890,
        "contentEditedBy": {"id": "user1"},
        "contentEditedOn": 1234567890,
        "style": {"color": "#0F766EFF"},
    }
    parsed = nodes.parse_widgets([shape_raw, icon_raw])
    assert len(parsed) == 2
    assert isinstance(parsed[0], widgets.ShapeWidget)
    assert isinstance(parsed[1], widgets.IconWidget)


def test_parse_unknown_widget_type_fails() -> None:
    """Test that parsing an unknown widget type raises ValidationError."""
    raw = {
        "id": "unknown-1",
        "type": "unknown_widget_type",
        "x": 0,
        "y": 0,
        "width": 100,
        "height": 100,
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
        "createdBy": {"id": "user1"},
        "createdOn": 1234567890,
        "updatedBy": {"id": "user1"},
        "updatedOn": 1234567890,
        "contentEditedBy": {"id": "user1"},
        "contentEditedOn": 1234567890,
    }
    with pytest.raises(pydantic.ValidationError):
        nodes.parse_widgets([raw])
