"""Mural public API v1 widget shapes -- the single owner of this vendor
contract. Import from here instead of redeclaring a widget dict inline.

VERIFIED against tests/cassettes/mural_get_widgets.yaml -- a real recorded
response -- for `sticky note`, `shape`, `icon`, `text`, `area` and `comment`
widgets (see that cassette's two pages for the exact payloads). `arrow` is
NOT present in that recording; its shape here is inferred from the Mural API
docs and app.integration.mural.board.widgets.schemas.ArrowWidget, not from a
recorded response. If you add another widget type without a cassette entry
to match, say so in the same way.

Factories return the raw dict shape the vendor sends (what
app.integration.mural.board.widgets.nodes.parse_widgets consumes). Every
factory accepts `**overrides` -- never share a mutable instance between
tests.
"""

from typing import Any


def user_ref(uid: str = "u1") -> dict[str, Any]:
    return {"id": uid}


def base_widget(widget_id: str, widget_type: str, **overrides: Any) -> dict[str, Any]:
    widget: dict[str, Any] = {
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
        "createdBy": user_ref(),
        "createdOn": 0,
        "updatedBy": user_ref(),
        "updatedOn": 0,
        "contentEditedBy": user_ref(),
        "contentEditedOn": 0,
    }
    widget.update(overrides)
    return widget


def sticky(
    widget_id: str,
    *,
    text: str = "",
    font_size: float = 14,
    parent_id: str | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    return base_widget(
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
        **overrides,
    )


def area(
    widget_id: str,
    title: str,
    *,
    x: float = 0,
    y: float = 0,
    w: float = 500,
    h: float = 400,
    **overrides: Any,
) -> dict[str, Any]:
    return base_widget(
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
        **overrides,
    )


def arrow(
    widget_id: str,
    *,
    start_ref: str | None = None,
    end_ref: str | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    """NOT verified against a cassette -- no arrow widget appears in
    tests/cassettes/mural_get_widgets.yaml. Shape inferred from
    app.integration.mural.board.widgets.schemas.ArrowWidget."""
    widget = base_widget(
        widget_id,
        "arrow",
        title="",
        arrowType="straight",
        tip="single",
        stackable=False,
        points=[{"x": 0, "y": 0}, {"x": 10, "y": 10}],
        style={"strokeColor": "#000000FF", "strokeStyle": "solid", "strokeWidth": 2},
        **overrides,
    )
    if start_ref:
        widget["startRefId"] = start_ref
    if end_ref:
        widget["endRefId"] = end_ref
    return widget
