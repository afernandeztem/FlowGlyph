"""What a UiPath project's `project.json` says about the project as a whole."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

_UNSAFE_ID_CHARACTERS = re.compile(r"[^\w./-]+")


@dataclass(frozen=True)
class Project:
    """A UiPath project: its identity, runtime settings and package dependencies."""

    root: Path
    name: str
    description: str
    main: str
    output_type: str | None
    expression_language: str | None
    target_framework: str | None
    studio_version: str | None
    dependencies: dict[str, str] = field(default_factory=dict[str, str])
    entry_points: tuple[str, ...] = ()

    @property
    def slug(self) -> str:
        """The project part of its capability ids: `uipath/<slug>/...`."""
        return slug(self.name)


def read_project(root: Path) -> Project:
    """The project rooted at `root`, from its `project.json`, or what can be told without one."""
    manifest = _manifest(root / "project.json")
    options = cast("dict[str, Any]", manifest.get("designOptions") or {})
    entry_points = [
        str(cast("dict[str, Any]", item).get("filePath"))
        for item in cast("list[Any]", manifest.get("entryPoints") or [])
        if isinstance(item, dict) and cast("dict[str, Any]", item).get("filePath")
    ]
    main = str(manifest.get("main") or "Main.xaml")
    dependencies = cast("dict[str, Any]", manifest.get("dependencies") or {})
    return Project(
        root=root,
        name=str(manifest.get("name") or root.resolve().name),
        description=str(manifest.get("description") or ""),
        main=main,
        output_type=_text(options.get("outputType") or manifest.get("projectType")),
        expression_language=_text(manifest.get("expressionLanguage")),
        target_framework=_text(manifest.get("targetFramework")),
        studio_version=_text(manifest.get("studioVersion")),
        dependencies={
            str(name): str(version).strip("[]") for name, version in dependencies.items()
        },
        entry_points=tuple(dict.fromkeys([main, *entry_points])),
    )


def slug(text: str) -> str:
    """`text` as a capability id segment."""
    return _UNSAFE_ID_CHARACTERS.sub("_", text).strip("_")


def _manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data: Any = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return cast("dict[str, Any]", data) if isinstance(data, dict) else {}


def _text(value: Any) -> str | None:
    return str(value) if value else None
