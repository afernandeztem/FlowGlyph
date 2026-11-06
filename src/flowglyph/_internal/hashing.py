"""Content hashes for lock files, stable across runs and machines."""

import hashlib
import json
from typing import Any


def digest(data: bytes) -> str:
    """Short, stable content hash used in lock files."""
    return "sha256:" + hashlib.sha256(data).hexdigest()[:32]


def fingerprint(value: Any) -> str:
    """Hash of a JSON-serialisable value, independent of key order."""
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return digest(canonical.encode())
