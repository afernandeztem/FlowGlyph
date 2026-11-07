"""Reading an SAP Build Process Automation project: an exported `.mtar`, or its unpacked content.

An `.mtar` is a zip holding `lobby/lobby_project.json` and, per project, a `content.zip` with
`project.json` and one folder per artifact: its `artifact.json` header and its content files.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, cast

from flowglyph._internal import archives
from flowglyph.errors import AdapterError

PROCESS = "bpi.process"
AUTOMATION = "automation"
DECISION = "bpi.decision"


@dataclass(frozen=True)
class Artifact:
    """One artifact of a project: its header and the content its model is stored in."""

    uid: str
    type: str
    name: str
    identifier: str
    description: str
    header: dict[str, Any]
    content: dict[str, Any]


@dataclass
class Project:
    """A project and its artifacts, keyed by uid."""

    name: str
    description: str
    version: str | None
    artifacts: dict[str, Artifact] = field(default_factory=dict[str, Artifact])

    def of_type(self, kind: str) -> list[Artifact]:
        """Artifacts of one type, by name."""
        return sorted(
            (artifact for artifact in self.artifacts.values() if artifact.type == kind),
            key=lambda artifact: artifact.name,
        )


def read_mtar(path: Path, location: str) -> list[Project]:
    """Every project in an exported `.mtar`.

    Raises:
        AdapterError: If the archive is corrupt or holds no project.
    """
    files = archives.read_zip(path, location)
    lobby = _json(files.get("lobby/lobby_project.json"))
    projects = [
        _project(archives.read_zip(data, f"{location}:{name}"), lobby)
        for name, data in sorted(files.items())
        if name.endswith("content.zip")
    ]
    found = [project for project in projects if project.artifacts]
    if not found:
        raise AdapterError(f"{location} holds no SAP Build Process Automation project")
    return found


def read_directory(root: Path) -> Project:
    """A project unpacked from its `content.zip` into `root`."""
    files = {
        file.relative_to(root).as_posix(): file.read_bytes()
        for file in root.rglob("*")
        if file.is_file() and file.stat().st_size <= archives.MAX_ENTRY_BYTES
    }
    return _project(files, {})


def is_project_directory(root: Path) -> bool:
    """Whether `root` holds an unpacked project: a `project.json` beside artifact folders."""
    manifest = _json(_read(root / "project.json"))
    return bool(manifest.get("projectName")) and any(root.glob("*/artifact.json"))


def is_mtar(path: Path) -> bool:
    """Whether `path` is an exported project archive."""
    if path.suffix.lower() != ".mtar":
        return False
    try:
        names = archives.read_zip(path, path.name, lambda name: name.endswith("mtad.yaml"))
    except AdapterError:
        return False
    return any(b"com.sap.lobby.content" in data for data in names.values())


def _project(files: dict[str, bytes], lobby: dict[str, Any]) -> Project:
    manifest = _json(files.get("project.json"))
    project = Project(
        name=str(manifest.get("projectName") or lobby.get("name") or "project"),
        description=str(manifest.get("projectDescription") or lobby.get("description") or ""),
        version=str(lobby["version"]) if lobby.get("version") else None,
    )
    for name, data in sorted(files.items()):
        if PurePosixPath(name).name != "artifact.json":
            continue
        folder = str(PurePosixPath(name).parent)
        header = _json(data)
        if not header.get("uid") or not header.get("type"):
            continue
        content: dict[str, Any] = {}
        for item in cast("list[dict[str, Any]]", header.get("contents") or []):
            content = _json(files.get(f"{folder}/{item.get('uid')}")) or content
            if content:
                break
        uid = str(header["uid"])
        project.artifacts[uid] = Artifact(
            uid=uid,
            type=str(header["type"]),
            name=str(header.get("name") or uid),
            identifier=str(header.get("identifier") or uid),
            description=str(header.get("description") or ""),
            header=cast("dict[str, Any]", header.get("header") or {}),
            content=content,
        )
    return project


def _read(path: Path) -> bytes | None:
    return path.read_bytes() if path.is_file() else None


def _json(data: bytes | None) -> dict[str, Any]:
    if not data:
        return {}
    try:
        document: Any = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}
    return cast("dict[str, Any]", document) if isinstance(document, dict) else {}
