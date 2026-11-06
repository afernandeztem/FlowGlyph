"""Catalogs of capabilities and workflows, their lock files and how they are searched.

`extract` builds a catalog from sources; `load_catalog` reads one saved with `Catalog.save`. The
lock records what was extracted, and comparing locks gives each capability a semantic version.
"""

from flowglyph.catalog.extraction import extract
from flowglyph.catalog.lock import LOCK_FILE, Bump, Lock, LockEntry, Signature
from flowglyph.catalog.model import Catalog, load_catalog
from flowglyph.catalog.overrides import OVERRIDES_FILE
from flowglyph.catalog.versioning import Change, diff_locks

__all__ = [
    "LOCK_FILE",
    "OVERRIDES_FILE",
    "Bump",
    "Catalog",
    "Change",
    "Lock",
    "LockEntry",
    "Signature",
    "diff_locks",
    "extract",
    "load_catalog",
]
