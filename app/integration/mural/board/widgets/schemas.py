import enum
from typing import Annotated, Literal

import pydantic
import pydantic.alias_generators


class Font(enum.StrEnum):
    ADELLE = "adelle"
    BLAMBOT_CASUAL = "blambot-casual"
    BLAMBOT_PRO = "blambot-pro"
    LINT_MCCREE = "lint-mccree"
    MARKER_FELT = "marker-felt"
    MUSEO_SLAB = "museo-slab"
    PROXIMA_NOVA = "proxima-nova"
    SHARK_WATER = "shark-water"


class UserRef(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=pydantic.alias_generators.to_camel, populate_by_name=True
    )

    id: str
    first_name: str | None = None
    last_name: str | None = None
    alias: str | None = None


class Widget(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=pydantic.alias_generators.to_camel, populate_by_name=True
    )

    id: str
    type: str
    parent_id: str | None = None
    x: float
    y: float
    width: float
    height: float
    rotation: float
    stacking_order: int
    presentation_index: int
    title: str | None = None
    instruction: str
    hidden: bool
    hide_editor: bool
    hide_owner: bool
    invisible: bool
    locked: bool
    locked_by_facilitator: bool
    created_by: UserRef
    created_on: int
    updated_by: UserRef
    updated_on: int
    content_edited_by: UserRef
    content_edited_on: int


class StickyNoteStyle(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=pydantic.alias_generators.to_camel, populate_by_name=True
    )

    background_color: str
    bold: bool
    border: bool
    italic: bool
    underline: bool
    strike: bool
    font: Font
    font_size: float
    text_align: Literal["left", "center", "right"]


class StickyNoteWidget(Widget):
    type: Literal["sticky note"]
    title: str
    shape: Literal["circle", "rectangle"]
    style: StickyNoteStyle
    text: str | None = None
    html_text: str | None = None
    hyperlink: str | None = None
    hyperlink_title: str | None = None
    min_lines: int | None = None
    tags: list[str] = []


class ShapeStyle(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=pydantic.alias_generators.to_camel, populate_by_name=True
    )

    background_color: str
    border_color: str
    border_style: Literal["solid", "dotted"]
    border_width: Annotated[int, pydantic.Field(ge=1, le=7)]
    bold: bool
    italic: bool
    underline: bool
    strike: bool
    font: Font
    font_color: str
    font_size: Annotated[float, pydantic.Field(ge=1)]
    text_align: Literal["left", "center", "right"]


class ShapeType(enum.StrEnum):
    CIRCLE = "circle"
    DIAMOND = "diamond"
    HEXAGON = "hexagon"
    PENTAGON = "pentagon"
    SQUARE = "square"
    TRIANGLE = "triangle"
    DOCUMENT_SHAPE = "document_shape"
    EVENT_SHAPE = "event_shape"
    LOOP_LIMIT = "loop_limit"
    OFF_PAGE_REFERENCE = "off_page_reference"
    OFF_PAGE_REFERENCE_INCOMING = "off_page_reference_incoming"
    ARROW_DOWN = "arrow_down"
    ARROW_LEFT_RIGHT = "arrow_left_right"
    ARROW_LEFT = "arrow_left"
    ARROW_RIGHT = "arrow_right"
    ARROW_TOP = "arrow_top"
    BADGE = "badge"
    BRACE_LEFT = "brace_left"
    BRACE_RIGHT = "brace_right"
    CHONK_UNICORN = "chonk_unicorn"
    CLOUD = "cloud"
    CONNECTOR = "connector"
    CROSS = "cross"
    DATA = "data"
    DATABASE = "database"
    DECISION = "decision"
    DELAY = "delay"
    DIRECT_DATA = "direct_data"
    DISPLAY = "display"
    DOCUMENT = "document"
    ELLIPSE = "ellipse"
    END = "end"
    HEXAGON_SMART = "hexagon_smart"
    INTERNAL_STORAGE = "internal_storage"
    MANUAL_INPUT = "manual_input"
    MANUAL_LOOP = "manual_loop"
    MERGE = "merge"
    MULTIPLE_DOCUMENTS = "multiple_documents"
    NOTE_LEFT = "note_left"
    NOTE_RIGHT = "note_right"
    OCTAGON = "octagon"
    OFF_PAGE_CONNECTOR = "off_page_connector"
    OR = "or"
    PAPERTAPE = "papertape"
    PENTAGON_SMART = "pentagon_smart"
    PORONGO = "porongo"
    PREDEFINED_PROCESS = "predefined_process"
    PREPARATION = "preparation"
    PROCESS = "process"
    RECTANGLE = "rectangle"
    RHOMBUS_SMART = "rhombus_smart"
    RIBBON = "ribbon"
    RIGHT_TRIANGLE = "right_triangle"
    ROUNDED_SQUARE = "rounded_square"
    SIMPLE_RIBBON = "simple_ribbon"
    SPEECH_BUBBLE_CENTER = "speech_bubble_center"
    SPEECH_BUBBLE_LEFT = "speech_bubble_left"
    SPEECH_BUBBLE_RIGHT = "speech_bubble_right"
    STAR = "star"
    START = "start"
    STEP = "step"
    STORED_DATA = "stored_data"
    SUMMING_JUNCTION = "summing_junction"
    TEARDROP_BUBBLE = "teardrop_bubble"
    TERMINATOR = "terminator"
    THINKING_BUBBLE_LEFT = "thinking_bubble_left"
    THINKING_BUBBLE_RIGHT = "thinking_bubble_right"
    TRAPEZOID = "trapezoid"
    TRIANGLE_SMART = "triangle_smart"


class ShapeWidget(Widget):
    type: Literal["shape"]
    title: str
    shape: ShapeType
    text: str
    html_text: str | None = None
    style: ShapeStyle


class TextStyle(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=pydantic.alias_generators.to_camel, populate_by_name=True
    )

    background_color: str | None = None
    font: Font | None = None
    font_size: Annotated[float, pydantic.Field(ge=1)] | None = None
    text_align: Literal["left", "center", "right"] | None = None


class TextWidget(Widget):
    type: Literal["text"]
    title: str
    fixed_width: bool
    text: str | None = None
    hyperlink: str | None = None
    hyperlink_title: str | None = None
    style: TextStyle = TextStyle()


class IconStyle(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=pydantic.alias_generators.to_camel, populate_by_name=True
    )

    color: str


class IconWidget(Widget):
    type: Literal["icon"]
    title: str
    name: str
    style: IconStyle


class AreaStyle(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=pydantic.alias_generators.to_camel, populate_by_name=True
    )

    background_color: str
    border_color: str
    border_style: Literal["solid", "dashed", "dotted-spaced", "dotted"]
    border_width: int
    title_font_size: Annotated[float, pydantic.Field(ge=1)]


class AreaWidget(Widget):
    type: Literal["area"]
    title: str
    layout: Literal["free", "column", "row"]
    show_title: bool
    style: AreaStyle


class ImageWidget(Widget):
    type: Literal["image"]
    border: bool
    caption: str
    description: str
    expires_in_minutes: int | None
    natural_height: float
    natural_width: float
    show_caption: bool
    thumbnail_url: str
    url: str | None
    aspect_ratio: float | None = None
    link: str | None = None
    mask: dict[str, object] | None = None


class TableColumn(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=pydantic.alias_generators.to_camel, populate_by_name=True
    )

    column_id: str
    width: float


class TableRow(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=pydantic.alias_generators.to_camel, populate_by_name=True
    )

    row_id: str
    height: float
    min_height: float


class TableStyle(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=pydantic.alias_generators.to_camel, populate_by_name=True
    )

    border_color: str
    border_width: int


class TableWidget(Widget):
    type: Literal["table"]
    auto_resize: bool
    columns: list[TableColumn]
    rows: list[TableRow]
    style: TableStyle


class TableCellStyle(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=pydantic.alias_generators.to_camel, populate_by_name=True
    )

    background_color: str


class TableCellWidget(Widget):
    type: Literal["table cell"]
    column_id: str
    row_id: str
    col_span: int
    row_span: int
    style: TableCellStyle


class ArrowPoint(pydantic.BaseModel):
    x: float | None = None
    y: float | None = None


class ArrowLabelFormat(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=pydantic.alias_generators.to_camel, populate_by_name=True
    )

    color: str
    font_family: Font
    bold: bool
    italic: bool
    text_align: Literal["left", "center", "right"]
    font_size: float


class ArrowLabelItem(pydantic.BaseModel):
    x: float
    y: float
    height: float
    width: float
    text: str


class ArrowLabel(pydantic.BaseModel):
    format: ArrowLabelFormat
    labels: list[ArrowLabelItem]


class ArrowStyle(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=pydantic.alias_generators.to_camel, populate_by_name=True
    )

    stroke_color: str
    stroke_style: Literal["solid", "dashed", "dotted-spaced", "dotted"]
    stroke_width: int


class ArrowWidget(Widget):
    type: Literal["arrow"]
    title: str
    arrow_type: Literal["straight", "curved", "orthogonal"]
    tip: Literal["no tip", "single", "double"]
    stackable: bool
    points: Annotated[list[ArrowPoint], pydantic.Field(min_length=2)]
    style: ArrowStyle
    start_ref_id: str | None = None
    end_ref_id: str | None = None
    label: ArrowLabel | None = None


class CommentReply(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        alias_generator=pydantic.alias_generators.to_camel, populate_by_name=True
    )

    created: int | None = None
    message: str | None = None
    user: UserRef | None = None


class CommentWidget(Widget):
    type: Literal["comment"]
    title: str
    message: str
    replies: list[CommentReply]
    timestamp: int | None = None
    reference_widget_id: str | None = None
    resolved_by: UserRef | None = None
    resolved_on: int | None = None


class FileWidget(Widget):
    type: Literal["file"]
    title: str
    url: str | None
    scanning: bool
    expires_in_minutes: int | None = None
    link: str | None = None
    preview_url: str | None = None
