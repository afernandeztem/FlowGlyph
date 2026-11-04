"""Adapter for UiPath Studio projects (`project.json` plus `.xaml` workflows)."""

import json
import re
from pathlib import Path, PurePosixPath
from typing import ClassVar

from flowglyph._internal.hashing import digest
from flowglyph.adapters import Diagnostic, Extraction
from flowglyph.adapters.uipath.parser import ActivityStats, ParsedWorkflow, WorkflowParser
from flowglyph.adapters.uipath.taxonomy import Taxonomy, default_taxonomy
from flowglyph.adapters.uipath.xaml import load, split_tag
from flowglyph.errors import AdapterError
from flowglyph.ir import Capability, Effects, Idempotency, JsonSchema, Source, Workflow

_SKIPPED_DIRECTORIES = frozenset({".local", ".screenshots", ".objects", ".settings", ".tmh"})
_UNSAFE_ID_CHARACTERS = re.compile(r"[^\w./-]+")


class UiPathAdapter:
    """Extracts capabilities and workflow graphs from a UiPath project.

    Every `.xaml` workflow becomes an invocable capability, typed from its arguments, plus a
    workflow graph. Every activity type in use becomes a non-invocable capability that
    documents the parameters seen across the project.
    """

    name: ClassVar[str] = "uipath"
    version: ClassVar[str] = "0.1.0"

    def __init__(self, taxonomy: Taxonomy | None = None) -> None:
        """Create the adapter, optionally with a custom taxonomy."""
        self.taxonomy = taxonomy or default_taxonomy()

    def detect(self, path: Path) -> bool:
        """Whether `path` is a UiPath project directory or a single `.xaml` file."""
        if path.is_file():
            return path.suffix.lower() == ".xaml"
        return (path / "project.json").is_file() or any(path.glob("*.xaml"))

    def discover(self, root: Path) -> list[Path]:
        """Every UiPath project under `root`: one per `project.json` that has workflows.

        Workflows outside any project are grouped into one extra source rooted at `root`.
        """
        if root.is_file():
            return [root] if self.detect(root) else []
        projects = sorted(
            manifest.parent
            for manifest in root.rglob("project.json")
            if not _SKIPPED_DIRECTORIES.intersection(manifest.relative_to(root).parts)
            and _workflow_files(manifest.parent)
        )
        if root not in projects and _workflow_files(root):
            projects.insert(0, root)
        return projects

    def extract(self, path: Path) -> Extraction:
        """Extract the project rooted at `path`."""
        root = path if path.is_dir() else path.parent
        files = [path] if path.is_file() else _workflow_files(root)
        manifest = _manifest(root)
        project = _slug(str(manifest.get("name") or root.resolve().name))
        main = str(manifest.get("main", "Main.xaml"))

        artifacts = {_relative(file, root): digest(file.read_bytes()) for file in files}
        capability_ids = {
            artifact: f"uipath/{project}/{_slug(artifact.removesuffix('.xaml'))}"
            for artifact in artifacts
        }
        parser = WorkflowParser(
            taxonomy=self.taxonomy,
            resolve_invoke=lambda target: _resolve(target, capability_ids),
        )
        parsed: list[ParsedWorkflow] = []
        diagnostics: list[Diagnostic] = []
        for file in files:
            artifact = _relative(file, root)
            try:
                document = load(file)
            except AdapterError as error:
                diagnostics.append(Diagnostic("error", artifact, str(error)))
                continue
            if split_tag(document.tag)[1] != "Activity":
                diagnostics.append(Diagnostic("info", artifact, "not a workflow, skipped"))
                continue
            capability_id = capability_ids[artifact]
            result = parser.parse(document, artifact, capability_id, capability_id)
            parsed.append(result)
            diagnostics.extend(Diagnostic("warning", artifact, note) for note in result.notes)
            diagnostics.extend(
                Diagnostic("warning", artifact, _unresolved_message(target))
                for target in result.workflow.unresolved_calls
            )

        effects = _transitive_effects(parsed)
        workflows: list[Workflow] = [item.workflow for item in parsed]
        capabilities = [
            self._workflow_capability(item, effects[item.workflow.id], artifacts, main)
            for item in parsed
        ]
        capabilities.extend(
            self._activity_capability(stats, artifacts)
            for stats in sorted(parser.activities.values(), key=lambda stats: stats.name)
            if stats.uses
        )
        return Extraction(
            capabilities=capabilities,
            workflows=workflows,
            artifacts=artifacts,
            diagnostics=diagnostics,
        )

    def _workflow_capability(
        self, item: ParsedWorkflow, effects: Effects, artifacts: dict[str, str], main: str
    ) -> Capability:
        return Capability(
            id=item.workflow.id,
            kind="workflow",
            title=item.class_name,
            description=item.description,
            category="workflow",
            input_schema=item.input_schema,
            output_schema=item.output_schema,
            effects=effects,
            idempotency=_inferred_idempotency(effects),
            tags=("entry-point",) if item.artifact == main else (),
            notes=tuple(item.notes),
            source=Source(
                provider=self.name,
                artifact=item.class_name,
                location=item.artifact,
                source_hash=artifacts[item.artifact],
            ),
        )

    def _activity_capability(self, stats: ActivityStats, artifacts: dict[str, str]) -> Capability:
        properties: dict[str, JsonSchema] = {}
        for parameter, uses in sorted(stats.parameter_uses.items()):
            spec: JsonSchema = {"x-seen": f"{uses}/{stats.uses}"}
            if stats.parameter_types[parameter]:
                spec["x-clr-types"] = sorted(stats.parameter_types[parameter])
            if stats.parameter_examples[parameter]:
                spec["examples"] = stats.parameter_examples[parameter]
            properties[parameter] = spec
        required = sorted(name for name, uses in stats.parameter_uses.items() if uses == stats.uses)
        files = sorted(stats.files)
        return Capability(
            id=stats.capability_id,
            kind="activity",
            title=stats.name,
            description=stats.notes[0] if stats.notes else "",
            category=stats.category.name,
            input_schema={"type": "object", "properties": properties, "required": required},
            effects=stats.category.effects,
            idempotency=_inferred_idempotency(stats.category.effects),
            tags=tuple(f"used-in:{file}" for file in files),
            source=Source(
                provider=self.name,
                artifact=f"{{{stats.namespace}}}{stats.name}",
                location=files[0],
                source_hash=artifacts[files[0]],
            ),
            invocable=False,
        )


def _workflow_files(root: Path) -> list[Path]:
    """Workflows of the project at `root`, leaving out projects nested inside it."""
    nested = {manifest.parent for manifest in root.rglob("project.json") if manifest.parent != root}
    return sorted(
        file
        for file in root.rglob("*.xaml")
        if not _SKIPPED_DIRECTORIES.intersection(file.relative_to(root).parts)
        and not any(project in file.parents for project in nested)
    )


def _manifest(root: Path) -> dict[str, object]:
    manifest = root / "project.json"
    if not manifest.is_file():
        return {}
    try:
        data: object = json.loads(manifest.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as error:
        raise AdapterError(f"{manifest}: {error}") from error
    return data if isinstance(data, dict) else {}  # pyright: ignore[reportUnknownVariableType]


def _relative(file: Path, root: Path) -> str:
    return file.relative_to(root).as_posix()


def _slug(text: str) -> str:
    return _UNSAFE_ID_CHARACTERS.sub("_", text).strip("_")


def _resolve(target: str, capability_ids: dict[str, str]) -> str | None:
    normalized = PurePosixPath(target.lstrip("./")).as_posix().lower()
    for artifact, capability_id in capability_ids.items():
        candidate = artifact.lower()
        if candidate == normalized or candidate.endswith("/" + normalized):
            return capability_id
    return None


def _unresolved_message(target: str) -> str:
    if target.startswith("["):
        return f"invokes a workflow chosen at runtime by the expression {target}"
    return f"invoked workflow not found in the project: {target}"


def _transitive_effects(parsed: list[ParsedWorkflow]) -> dict[str, Effects]:
    by_id = {item.workflow.id: item for item in parsed}
    resolved: dict[str, Effects] = {}

    def visit(workflow_id: str, stack: frozenset[str]) -> Effects:
        if workflow_id in resolved:
            return resolved[workflow_id]
        item = by_id[workflow_id]
        callees = [
            visit(callee, stack | {workflow_id})
            for callee in item.workflow.calls
            if callee in by_id and callee not in stack
        ]
        resolved[workflow_id] = Effects.combine([item.effects, *callees])
        return resolved[workflow_id]

    for workflow_id in by_id:
        visit(workflow_id, frozenset())
    return resolved


def _inferred_idempotency(effects: Effects) -> Idempotency:
    if not effects.has_side_effects:
        return Idempotency(mode="natural", confidence=0.8)
    return Idempotency(mode="none", confidence=0.7)


__all__ = ["UiPathAdapter"]
