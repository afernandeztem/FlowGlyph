"""Short names that tell apart artifacts sharing a name in different folders."""

import re
from pathlib import PurePosixPath

_UNSAFE = re.compile(r"[^A-Za-z0-9.-]+")


def distinguishing_names(paths: list[str]) -> list[str]:
    """The shortest path segment that tells each of several files apart.

    `["v2/API/API.edmx", "v4/API/API.edmx"]` gives `["v2", "v4"]`; files in one folder fall back
    to their names.
    """
    parts = [PurePosixPath(path).with_suffix("").parts for path in paths]
    for index in range(max(len(p) for p in parts)):
        segments = [p[index] if index < len(p) else "" for p in parts]
        if len(set(segments)) == len(segments):
            return [_UNSAFE.sub("_", segment).strip("_") for segment in segments]
    return [_UNSAFE.sub("_", "/".join(p)).strip("_") for p in parts]
