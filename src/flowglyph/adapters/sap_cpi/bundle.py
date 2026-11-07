"""Reading an iFlow artifact, zipped or unpacked: manifest, `.iflw` files and parameters."""

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from flowglyph._internal import archives
from flowglyph.errors import AdapterError

_WANTED = (".iflw", "MANIFEST.MF", "parameters.prop")
_MANIFEST = "META-INF/MANIFEST.MF"
_PARAMETER_LINE = re.compile(r"^\s*([^#!=\s][^=:]*?)\s*[=:]")


@dataclass(frozen=True)
class Bundle:
    """One SAP Cloud Integration artifact: its manifest and the files an adapter needs.

    Parameter values are never kept: they routinely hold hosts, users and keys. Only the names
    of externalized parameters are read.
    """

    location: str
    name: str
    symbolic_name: str
    version: str | None
    bundle_type: str
    iflows: dict[str, bytes]
    parameters: tuple[str, ...]


def read_zip(path: Path, location: str) -> Bundle:
    """Read an exported artifact `.zip` without extracting it to disk.

    Raises:
        AdapterError: If the archive is corrupt, too large or not an SAP artifact.
    """
    files = archives.read_zip(path, str(path), lambda name: name.endswith(_WANTED))
    return _bundle(location, files)


def read_directory(root: Path, location: str) -> Bundle:
    """Read an artifact that was unpacked into `root`."""
    files = {
        file.relative_to(root).as_posix(): file.read_bytes()
        for file in root.rglob("*")
        if file.is_file()
        and (file.suffix == ".iflw" or file.name in {"MANIFEST.MF", "parameters.prop"})
    }
    return _bundle(location, files)


def manifest_type(data: bytes) -> str | None:
    """The `SAP-BundleType` of a manifest, if it is an SAP artifact manifest."""
    return _manifest(data).get("SAP-BundleType")


def _bundle(location: str, files: dict[str, bytes]) -> Bundle:
    manifest_name = next((name for name in files if name.endswith(_MANIFEST)), None)
    manifest = _manifest(files[manifest_name]) if manifest_name else {}
    if "SAP-BundleType" not in manifest and not any(name.endswith(".iflw") for name in files):
        raise AdapterError(f"{location} is not an SAP Cloud Integration artifact")
    iflows = {name: data for name, data in sorted(files.items()) if name.endswith(".iflw")}
    fallback = PurePosixPath(location).stem
    parameters_file = next(
        (data for name, data in files.items() if name.endswith("parameters.prop")), b""
    )
    return Bundle(
        location=location,
        name=manifest.get("Bundle-Name") or fallback,
        symbolic_name=manifest.get("Bundle-SymbolicName", fallback).split(";", 1)[0].strip(),
        version=manifest.get("Bundle-Version"),
        bundle_type=manifest.get("SAP-BundleType", "IntegrationFlow"),
        iflows=iflows,
        parameters=tuple(sorted(_parameter_names(parameters_file))),
    )


def _manifest(data: bytes) -> dict[str, str]:
    """Parse a JAR manifest, joining continuation lines (lines starting with one space)."""
    headers: dict[str, str] = {}
    current: str | None = None
    for raw in data.decode("utf-8", errors="replace").splitlines():
        if raw.startswith(" ") and current:
            headers[current] += raw[1:]
        elif ":" in raw:
            current, _, value = raw.partition(":")
            current = current.strip()
            headers[current] = value.strip()
    return headers


def _parameter_names(data: bytes) -> set[str]:
    names: set[str] = set()
    for line in data.decode("utf-8", errors="replace").splitlines():
        match = _PARAMETER_LINE.match(line)
        if match:
            names.add(match.group(1).replace("\\ ", " "))
    return names
