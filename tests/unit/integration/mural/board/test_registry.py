from app.integration.mural.board import registry
from app.integration.mural.board.widgets import nodes
from app.integration.mural.board.widgets import schemas as widgets

_REG = registry.build_default_registry()


def test_register_and_get_tag() -> None:
    """Test registering a widget type and retrieving its tag."""
    reg = registry.WidgetRendererRegistry()
    reg.register(
        widgets.StickyNoteWidget,
        tag="StickyNote",
        attrs=lambda n: {"id": n.id, "text": n.text or ""},
    )
    tag = reg.get_tag_name(
        widgets.StickyNoteWidget(
            id="w1",
            type="sticky note",
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
                backgroundColor="#FFF",
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
    )
    assert tag == "StickyNote"


def test_get_tag_name_fallback() -> None:
    """Test that get_tag_name falls back to class name if not registered."""
    reg = registry.WidgetRendererRegistry()
    obj = object()
    tag = reg.get_tag_name(obj)
    assert tag == "object"


def test_get_attrs_with_extractor() -> None:
    """Test get_attrs with a registered extractor."""
    reg = registry.WidgetRendererRegistry()
    node = nodes.TableRowNode(
        id="row-1",
        table_id="table-1",
        row=widgets.TableRow(rowId="row-1", height=50, minHeight=50),
    )
    reg.register(
        nodes.TableRowNode,
        tag="Row",
        attrs=lambda n: {"row_id": n.row.row_id, "height": str(n.row.height)},
    )
    attrs = reg.get_attrs(node)
    assert attrs["row_id"] == "row-1"
    assert attrs["height"] == "50.0"


def test_get_attrs_fallback_no_extractor() -> None:
    """Test get_attrs with no registered extractor falls back to id."""
    reg = registry.WidgetRendererRegistry()
    obj = type("Obj", (), {"id": "obj-123"})()
    attrs = reg.get_attrs(obj)
    assert attrs["id"] == "obj-123"


def _make_user_ref() -> dict:
    return {"id": "u1", "firstName": "Test", "lastName": "User"}


def _base_widget_kwargs() -> dict:
    return {
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
        "createdBy": _make_user_ref(),
        "createdOn": 0,
        "updatedBy": _make_user_ref(),
        "updatedOn": 0,
        "contentEditedBy": _make_user_ref(),
        "contentEditedOn": 0,
    }


def test_sticky_note_style_attrs() -> None:
    """StickyNote attrs include color, text_align, and role; raw font_size is excluded."""
    widget = widgets.StickyNoteWidget(
        id="sn1",
        type="sticky note",
        title="Note",
        shape="rectangle",
        style=widgets.StickyNoteStyle(
            backgroundColor="#FF0000FF",
            bold=False,
            border=False,
            italic=False,
            underline=False,
            strike=False,
            font="proxima-nova",
            fontSize=14,
            textAlign="left",
        ),
        **_base_widget_kwargs(),
    )
    attrs = _REG.get_attrs(widget)
    assert attrs["color"] == "#FF0000FF"
    assert attrs["text_align"] == "left"
    assert attrs["role"] == "caption"
    assert "font" not in attrs
    assert "font_size" not in attrs


def test_shape_style_attrs() -> None:
    """Shape attrs include background_color, border_color, font_color, text_align, and role; raw font_size is excluded."""
    widget = widgets.ShapeWidget(
        id="sh1",
        type="shape",
        title="Box",
        shape="rectangle",
        text="hello",
        style=widgets.ShapeStyle(
            backgroundColor="#00FF00FF",
            borderColor="#FF0000FF",
            borderStyle="solid",
            borderWidth=2,
            bold=False,
            italic=False,
            underline=False,
            strike=False,
            font="proxima-nova",
            fontColor="#0000FFFF",
            fontSize=16,
            textAlign="center",
        ),
        **_base_widget_kwargs(),
    )
    attrs = _REG.get_attrs(widget)
    assert attrs["background_color"] == "#00FF00FF"
    assert attrs["border_color"] == "#FF0000FF"
    assert attrs["font_color"] == "#0000FFFF"
    assert attrs["text_align"] == "center"
    assert attrs["role"] == "caption"
    assert "font" not in attrs
    assert "font_size" not in attrs


def test_icon_style_attrs() -> None:
    """Icon attrs include color from style."""
    widget = widgets.IconWidget(
        id="ic1",
        type="icon",
        title="Star",
        name="star",
        style=widgets.IconStyle(color="#ABCDEFFF"),
        **_base_widget_kwargs(),
    )
    attrs = _REG.get_attrs(widget)
    assert attrs["color"] == "#ABCDEFFF"


def test_area_style_attrs() -> None:
    """Area attrs include background_color, border_color, border_style."""
    widget = widgets.AreaWidget(
        id="a1",
        type="area",
        title="Zone",
        layout="free",
        showTitle=True,
        style=widgets.AreaStyle(
            backgroundColor="#FFFFFF33",
            borderColor="#000000FF",
            borderStyle="dashed",
            borderWidth=1,
            titleFontSize=12,
        ),
        **_base_widget_kwargs(),
    )
    attrs = _REG.get_attrs(widget)
    assert attrs["background_color"] == "#FFFFFF33"
    assert attrs["border_color"] == "#000000FF"
    assert attrs["border_style"] == "dashed"
    assert attrs["role"] == "caption"


def test_arrow_style_attrs() -> None:
    """Arrow attrs include stroke_color; stroke_style and stroke_width are excluded."""
    widget = widgets.ArrowWidget(
        id="ar1",
        type="arrow",
        title="Link",
        arrow_type="straight",
        tip="single",
        stackable=False,
        points=[widgets.ArrowPoint(x=0, y=0), widgets.ArrowPoint(x=10, y=10)],
        style=widgets.ArrowStyle(
            strokeColor="#FF00FFFF", strokeStyle="dashed", strokeWidth=2
        ),
        **_base_widget_kwargs(),
    )
    attrs = _REG.get_attrs(widget)
    assert attrs["stroke_color"] == "#FF00FFFF"
    assert "stroke_style" not in attrs
    assert "stroke_width" not in attrs


def test_rotation_omitted_when_zero() -> None:
    """Rotation attribute is absent when rotation is 0."""
    widget = widgets.StickyNoteWidget(
        id="sn2",
        type="sticky note",
        title="Note",
        shape="rectangle",
        style=widgets.StickyNoteStyle(
            backgroundColor="#FFFFFFFF",
            bold=False,
            border=False,
            italic=False,
            underline=False,
            strike=False,
            font="proxima-nova",
            fontSize=14,
            textAlign="left",
        ),
        **_base_widget_kwargs(),
    )
    attrs = _REG.get_attrs(widget)
    assert "rotation" not in attrs


def test_rotation_included_when_nonzero() -> None:
    """Rotation attribute is present when rotation is non-zero."""
    kwargs = {**_base_widget_kwargs(), "rotation": 45.0}
    widget = widgets.StickyNoteWidget(
        id="sn3",
        type="sticky note",
        title="Note",
        shape="rectangle",
        style=widgets.StickyNoteStyle(
            backgroundColor="#FFFFFFFF",
            bold=False,
            border=False,
            italic=False,
            underline=False,
            strike=False,
            font="proxima-nova",
            fontSize=14,
            textAlign="left",
        ),
        **kwargs,
    )
    attrs = _REG.get_attrs(widget)
    assert attrs["rotation"] == "45.0"


def test_font_size_to_role_thresholds() -> None:
    """_font_size_to_role maps size to heading/label/caption at the defined thresholds."""
    fn = registry._font_size_to_role
    assert fn(80) == "heading"
    assert fn(100) == "heading"
    assert fn(50) == "label"
    assert fn(79.9) == "label"
    assert fn(49.9) == "caption"
    assert fn(14) == "caption"
    assert fn(1) == "caption"


def test_text_widget_role_present() -> None:
    """TextWidget emits role when font_size is set."""
    widget = widgets.TextWidget(
        id="tx1",
        type="text",
        title="Heading",
        fixedWidth=False,
        style=widgets.TextStyle(fontSize=80),
        **_base_widget_kwargs(),
    )
    attrs = _REG.get_attrs(widget)
    assert attrs["role"] == "heading"


def test_text_widget_role_absent_when_no_font_size() -> None:
    """TextWidget omits role when font_size is absent."""
    widget = widgets.TextWidget(
        id="tx2",
        type="text",
        title="Body",
        fixedWidth=False,
        **_base_widget_kwargs(),
    )
    attrs = _REG.get_attrs(widget)
    assert "role" not in attrs


def test_default_registry_has_all_widget_types() -> None:
    """Test that the default registry has registrations for all widget types."""
    reg = registry.build_default_registry()
    widget_types = [
        widgets.StickyNoteWidget,
        widgets.ShapeWidget,
        widgets.TextWidget,
        widgets.IconWidget,
        widgets.AreaWidget,
        widgets.ImageWidget,
        widgets.TableWidget,
        widgets.TableCellWidget,
        widgets.ArrowWidget,
        widgets.CommentWidget,
        widgets.FileWidget,
        nodes.TableRowNode,
        nodes.TableColumnNode,
    ]
    for wtype in widget_types:
        obj = type("Obj", (), {"type": "test"})()
        tag = reg.get_tag_name(
            obj if wtype not in [nodes.TableRowNode, nodes.TableColumnNode] else obj
        )
        assert isinstance(tag, str)
