"""Reading zip archives from untrusted sources in memory, with limits against zip bombs."""

import io
import zipfile
from collections.abc import Callable
from pathlib import Path

from flowglyph.errors import AdapterError

MAX_ENTRY_BYTES = 20_000_000
MAX_TOTAL_BYTES = 200_000_000
MAX_COMPRESSION_RATIO = 200


def read_zip(
    source: Path | bytes, name: str, wanted: Callable[[str], bool] = lambda _: True
) -> dict[str, bytes]:
    """The entries of a zip archive that `wanted` accepts, read without touching the disk.

    Raises:
        AdapterError: If the archive is corrupt, or an entry is too large or compresses too well
            to be read safely.
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(source) if isinstance(source, bytes) else source)
    except (zipfile.BadZipFile, OSError) as error:
        raise AdapterError(f"{name}: {error}") from error
    files: dict[str, bytes] = {}
    total = 0
    with archive:
        for info in archive.infolist():
            if info.is_dir() or not wanted(info.filename):
                continue
            ratio = info.file_size / max(info.compress_size, 1)
            total += info.file_size
            if info.file_size > MAX_ENTRY_BYTES or ratio > MAX_COMPRESSION_RATIO:
                raise AdapterError(f"{name}: {info.filename} is too large to read safely")
            if total > MAX_TOTAL_BYTES:
                raise AdapterError(f"{name}: the archive is too large to read safely")
            try:
                files[info.filename] = archive.read(info)
            except (zipfile.BadZipFile, OSError, RuntimeError) as error:
                raise AdapterError(f"{name}: {info.filename}: {error}") from error
    return files
