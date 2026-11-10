class BoardRegionNotFoundError(Exception):
    """Raised when a requested region id does not exist on the board."""


class WidgetNotFoundError(Exception):
    """Raised when a requested widget id does not exist on the board."""


class BoardImageError(Exception):
    """A widget's image could not be loaded.

    Messages are written for the agent calling the tool, so they never carry
    the signed asset URL.
    """


class WidgetNotAnImageError(BoardImageError):
    """The widget is neither an image nor a file with a preview."""


class ImageRestrictedError(BoardImageError):
    """The board restricts downloads, so Mural withholds the image URL."""


class ImageNotAvailableError(BoardImageError):
    """The image could not be downloaded (expired link, host unreachable, no preview)."""


class ImageTooLargeError(BoardImageError):
    """The image exceeds the download size or pixel limit."""


class ImageHostNotAllowedError(BoardImageError):
    """The image is served from a host outside MURAL_ASSET_HOSTS."""


class UnsupportedImageError(BoardImageError):
    """The downloaded bytes are not an image format we can read."""
