"""Errors raised while parsing a Mural board."""


class BoardParseError(Exception):
    """Raised when a raw widget cannot be read as a known Mural widget type."""
