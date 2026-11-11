import pytest

from app.integration.mural.board.parsing import errors, parser
from app.integration.mural.board.parsing import schemas as widgets
from tests.fixtures import mural


class TestParseWidgets:
    def test_sticky_note_widget(self) -> None:
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
        parsed = parser.parse_widgets([raw])
        assert len(parsed) == 1
        assert isinstance(parsed[0], widgets.StickyNoteWidget)
        assert parsed[0].title == "Note"
        assert parsed[0].text == "Test note"

    def test_multiple_widgets_of_different_types(self) -> None:
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
        parsed = parser.parse_widgets([shape_raw, icon_raw])
        assert len(parsed) == 2
        assert isinstance(parsed[0], widgets.ShapeWidget)
        assert isinstance(parsed[1], widgets.IconWidget)

    def test_unknown_widget_type_becomes_an_unknown_widget(self) -> None:
        raw = mural.base_widget("unknown-1", "drawing", parentId="area-1", x=5.0)
        parsed = parser.parse_widgets([raw])
        assert len(parsed) == 1
        assert isinstance(parsed[0], widgets.UnknownWidget)
        assert parsed[0].type == "drawing"
        assert parsed[0].parent_id == "area-1"
        assert parsed[0].x == 5.0

    def test_known_type_with_a_bad_field_becomes_an_unknown_widget(self) -> None:
        raw = mural.sticky("s1", text="hi")
        del raw["style"]
        parsed = parser.parse_widgets([raw])
        assert isinstance(parsed[0], widgets.UnknownWidget)
        assert parsed[0].type == "sticky note"

    def test_a_bad_widget_does_not_stop_the_rest_of_the_board(self) -> None:
        parsed = parser.parse_widgets(
            [mural.sticky("s1"), {"id": "x", "type": "drawing"}, mural.sticky("s2")]
        )
        assert [type(w) for w in parsed] == [
            widgets.StickyNoteWidget,
            widgets.UnknownWidget,
            widgets.StickyNoteWidget,
        ]

    def test_malformed_geometry_keeps_the_widget_by_identity(self) -> None:
        raw = {"id": "w1", "type": "drawing", "x": "not a number"}
        parsed = parser.parse_widgets([raw])
        assert isinstance(parsed[0], widgets.UnknownWidget)
        assert parsed[0].id == "w1"
        assert parsed[0].x == 0.0

    def test_a_widget_with_no_id_raises(self) -> None:
        with pytest.raises(errors.BoardParseError):
            parser.parse_widgets([{"type": "sticky note"}])

    def test_the_failure_log_names_fields_but_not_content(self, caplog) -> None:
        raw = mural.sticky("s1", text="secret words")
        del raw["style"]
        with caplog.at_level("WARNING"):
            parser.parse_widgets([raw])
        assert "style" in caplog.text
        assert "secret words" not in caplog.text
