"""Exceptions raised by FlowGlyph."""


class FlowGlyphError(Exception):
    """Base class for every error raised by FlowGlyph."""


class AdapterError(FlowGlyphError):
    """A source artifact could not be translated into IR."""


class AdapterNotFoundError(AdapterError):
    """No registered adapter accepts the given source."""


class CatalogError(FlowGlyphError):
    """A catalog could not be loaded, saved or queried."""


class ValidationError(FlowGlyphError):
    """Arguments or IR documents do not match their schema."""


class ExecutionError(FlowGlyphError):
    """A capability could not be run against the system it belongs to."""
