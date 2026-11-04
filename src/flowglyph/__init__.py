"""FlowGlyph: enterprise automations as a vendor-neutral IR for agents."""

from importlib.metadata import PackageNotFoundError, version

from flowglyph.errors import FlowGlyphError

try:
    __version__ = version("flowglyph")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = ["FlowGlyphError", "__version__"]
