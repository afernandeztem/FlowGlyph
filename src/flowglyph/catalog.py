"""Catalogs of capabilities and workflows, their lock files and how they are searched."""

import json
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any, Literal, cast

import yaml
from pydantic import BaseModel, ConfigDict

from flowglyph._internal import markdown
from flowglyph._internal.hashing import fingerprint
from flowglyph._internal.search import BM25Index, Document
from flowglyph.adapters import Adapter, Diagnostic, detect_adapter, get_adapter
from flowglyph.errors import CatalogError
from flowglyph.ir import IR_VERSION, Capability, CapabilityKind, JsonSchema, Workflow

OVERRIDES_FILE = "flowglyph.overrides.yaml"
LOCK_FILE = "flowglyph.lock"
_DOCUMENTATION_KEYS = frozenset({"description", "examples", "x-seen", "x-default-expression"})


class Bump(IntEnum):
    """How much a capability changed between two extractions."""

    NONE = 0
    PATCH = 1
    MINOR = 2
    MAJOR = 3


class Signature(BaseModel):
    """The parts of a contract that decide whether a change is breaking."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    inputs: dict[str, tuple[str, bool]] = {}
    outputs: dict[str, str] = {}

    @classmethod
    def of(cls, capability: Capability) -> "Signature":
        """The signature of `capability`."""
        return cls(
            inputs={p.name: (p.type, p.required) for p in capability.inputs},
            outputs={p.name: p.type for p in capability.outputs},
        )

    def bump_to(self, new: "Signature") -> Bump:
        """The semver bump needed to go from this signature to `new`."""
        removed_input = self.inputs.keys() - new.inputs.keys()
        removed_output = self.outputs.keys() - new.outputs.keys()
        retyped = any(
            new.inputs[name][0] != spec[0]
            for name, spec in self.inputs.items()
            if name in new.inputs
        ) or any(
            new.outputs[name] != kind for name, kind in self.outputs.items() if name in new.outputs
        )
        newly_required = any(
            required and not self.inputs.get(name, ("", False))[1]
            for name, (_, required) in new.inputs.items()
        )
        if removed_input or removed_output or retyped or newly_required:
            return Bump.MAJOR
        if new != self:
            return Bump.MINOR
        return Bump.NONE


class LockEntry(BaseModel):
    """What the lock file remembers about one capability."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    source_hash: str
    contract_hash: str
    metadata_hash: str
    documentation_hash: str
    signature: Signature


class Lock(BaseModel):
    """Reproducibility record of an extraction, used to version capabilities over time."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ir_version: str = IR_VERSION
    adapters: dict[str, str] = {}
    artifacts: dict[str, str] = {}
    capabilities: dict[str, LockEntry] = {}

    @classmethod
    def read(cls, path: str | Path) -> "Lock":
        """Load a lock file."""
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))

    def write(self, path: str | Path) -> None:
        """Write the lock file with stable formatting, so it diffs cleanly."""
        text = json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True)
        Path(path).write_text(text + "\n", encoding="utf-8")


@dataclass(frozen=True)
class Change:
    """One capability that differs between two locks."""

    capability: str
    kind: Literal["added", "removed", "changed"]
    bump: Bump
    old_version: str | None
    new_version: str | None


@dataclass
class Catalog:
    """Capabilities and workflows extracted from one or more sources."""

    capabilities: dict[str, Capability] = field(default_factory=dict[str, Capability])
    workflows: dict[str, Workflow] = field(default_factory=dict[str, Workflow])
    lock: Lock = field(default_factory=Lock)
    diagnostics: tuple[Diagnostic, ...] = ()
    changes: tuple[Change, ...] = ()
    _index: BM25Index | None = field(default=None, init=False, repr=False)

    def __len__(self) -> int:
        return len(self.capabilities)

    def __iter__(self) -> Iterator[Capability]:
        return iter(self.capabilities.values())

    def get(self, reference: str) -> Capability:
        """Find a capability by id, by unique id suffix (`Framework/InitAllSettings`) or title.

        Raises:
            CatalogError: If nothing matches or the reference is ambiguous.
        """
        if reference in self.capabilities:
            return self.capabilities[reference]
        matches = [
            capability
            for capability in self.capabilities.values()
            if capability.id.endswith("/" + reference) or capability.title == reference
        ]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise CatalogError(f"no capability matches {reference!r}")
        candidates = ", ".join(sorted(match.id for match in matches))
        raise CatalogError(f"{reference!r} is ambiguous: {candidates}")

    def workflow(self, reference: str) -> Workflow:
        """The workflow graph behind the capability matching `reference`."""
        capability = self.get(reference)
        if capability.id not in self.workflows:
            raise CatalogError(f"{capability.id} has no workflow graph")
        return self.workflows[capability.id]

    def search(
        self,
        query: str,
        limit: int = 10,
        *,
        kind: CapabilityKind | None = None,
        invocable: bool | None = None,
    ) -> list[Capability]:
        """Capabilities ranked by relevance to a free-text `query`."""
        if self._index is None:
            self._index = BM25Index([_document(c, self.workflows) for c in self])
        hits = self._index.search(query, limit=len(self.capabilities))
        results = [self.capabilities[key] for key, _ in hits]
        if kind is not None:
            results = [c for c in results if c.kind == kind]
        if invocable is not None:
            results = [c for c in results if c.invocable is invocable]
        return results[:limit]

    def merge(self, other: "Catalog") -> "Catalog":
        """A catalog with the contents of both; `other` wins on id collisions."""
        return Catalog(
            capabilities={**self.capabilities, **other.capabilities},
            workflows={**self.workflows, **other.workflows},
            lock=Lock(
                adapters={**self.lock.adapters, **other.lock.adapters},
                artifacts={**self.lock.artifacts, **other.lock.artifacts},
                capabilities={**self.lock.capabilities, **other.lock.capabilities},
            ),
            diagnostics=self.diagnostics + other.diagnostics,
        )

    def save(self, directory: str | Path) -> Path:
        """Write the catalog, its graph, its lock file and Markdown cards to `directory`.

        The output is deterministic: saving the same catalog twice produces identical files.
        """
        target = Path(directory)
        cards = target / "capabilities"
        cards.mkdir(parents=True, exist_ok=True)
        lines = [self.capabilities[key].model_dump_json() for key in sorted(self.capabilities)]
        (target / "catalog.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        graph = {
            "ir_version": IR_VERSION,
            "workflows": [
                self.workflows[key].model_dump(mode="json") for key in sorted(self.workflows)
            ],
        }
        (target / "graph.json").write_text(
            json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        self.lock.write(target / LOCK_FILE)
        expected = {markdown.card_filename(c) for c in self}
        for stale in cards.glob("*.md"):
            if stale.name not in expected:
                stale.unlink()
        for capability in self:
            text = markdown.render_capability(capability, self.workflows, self.capabilities)
            (cards / markdown.card_filename(capability)).write_text(text, encoding="utf-8")
        (target / "INDEX.md").write_text(markdown.render_index(self), encoding="utf-8")
        return target


def extract(
    path: str | Path,
    *,
    adapter: str | Adapter = "auto",
    previous: Lock | str | Path | None = None,
) -> Catalog:
    """Extract a catalog from a source directory or file.

    Args:
        path: The project directory or file to read.
        adapter: An adapter name, an adapter instance, or `"auto"` to detect one.
        previous: The lock of an earlier extraction, used to version capabilities. When
            omitted, capabilities start at 1.0.0.

    Returns:
        The catalog, with `changes` describing what moved since `previous`.
    """
    source = Path(path)
    if not source.exists():
        raise CatalogError(f"{source} does not exist")
    if isinstance(adapter, str):
        adapter = detect_adapter(source) if adapter == "auto" else get_adapter(adapter)
    extraction = adapter.extract(source)
    root = source if source.is_dir() else source.parent
    capabilities = _apply_overrides(extraction.capabilities, root / OVERRIDES_FILE)
    old_lock = Lock.read(previous) if isinstance(previous, str | Path) else previous
    versioned, entries, changes = _version(capabilities, old_lock)
    return Catalog(
        capabilities={capability.id: capability for capability in versioned},
        workflows={workflow.id: workflow for workflow in extraction.workflows},
        lock=Lock(
            adapters={adapter.name: adapter.version},
            artifacts=dict(sorted(extraction.artifacts.items())),
            capabilities=entries,
        ),
        diagnostics=tuple(extraction.diagnostics),
        changes=tuple(changes),
    )


def load_catalog(directory: str | Path) -> Catalog:
    """Load a catalog previously written with `Catalog.save`, without re-parsing sources.

    Raises:
        CatalogError: If the directory does not contain a saved catalog.
    """
    source = Path(directory)
    catalog_file = source / "catalog.jsonl"
    if not catalog_file.is_file():
        raise CatalogError(f"{source} does not contain a catalog.jsonl")
    capabilities = [
        Capability.model_validate_json(line)
        for line in catalog_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    graph_file = source / "graph.json"
    graph: dict[str, Any] = (
        json.loads(graph_file.read_text(encoding="utf-8")) if graph_file.is_file() else {}
    )
    lock_file = source / LOCK_FILE
    return Catalog(
        capabilities={capability.id: capability for capability in capabilities},
        workflows={
            workflow.id: workflow
            for workflow in (Workflow.model_validate(item) for item in graph.get("workflows", []))
        },
        lock=Lock.read(lock_file) if lock_file.is_file() else Lock(),
    )


def diff_locks(old: Lock, new: Lock) -> list[Change]:
    """Capabilities added, removed or changed between two locks."""
    changes: list[Change] = []
    for capability_id in sorted(old.capabilities.keys() | new.capabilities.keys()):
        before = old.capabilities.get(capability_id)
        after = new.capabilities.get(capability_id)
        if before is None and after is not None:
            changes.append(Change(capability_id, "added", Bump.MAJOR, None, after.version))
        elif after is None and before is not None:
            changes.append(Change(capability_id, "removed", Bump.MAJOR, before.version, None))
        elif before is not None and after is not None:
            bump = _bump(before, after)
            if bump is not Bump.NONE:
                changes.append(
                    Change(capability_id, "changed", bump, before.version, after.version)
                )
    return changes


def _version(
    capabilities: Iterable[Capability], previous: Lock | None
) -> tuple[list[Capability], dict[str, LockEntry], list[Change]]:
    versioned: list[Capability] = []
    entries: dict[str, LockEntry] = {}
    changes: list[Change] = []
    for capability in sorted(capabilities, key=lambda c: c.id):
        entry = _lock_entry(capability, "1.0.0")
        before = previous.capabilities.get(capability.id) if previous else None
        if before is None:
            if previous is not None:
                changes.append(Change(capability.id, "added", Bump.MAJOR, None, entry.version))
        else:
            bump = _bump(before, entry)
            version = _increment(before.version, bump)
            entry = entry.model_copy(update={"version": version})
            if bump is not Bump.NONE:
                changes.append(Change(capability.id, "changed", bump, before.version, version))
        versioned.append(capability.model_copy(update={"version": entry.version}))
        entries[capability.id] = entry
    if previous is not None:
        changes.extend(
            Change(capability_id, "removed", Bump.MAJOR, before.version, None)
            for capability_id, before in sorted(previous.capabilities.items())
            if capability_id not in entries
        )
    return versioned, entries, changes


def _lock_entry(capability: Capability, version: str) -> LockEntry:
    contract = {
        "input": _strip_documentation(capability.input_schema),
        "output": _strip_documentation(capability.output_schema),
    }
    metadata = capability.model_dump(
        mode="json", include={"effects", "idempotency", "security", "errors", "kind", "invocable"}
    )
    documentation = {
        "title": capability.title,
        "description": capability.description,
        "parameters": [(p.name, p.description) for p in capability.inputs + capability.outputs],
    }
    return LockEntry(
        version=version,
        source_hash=capability.source.source_hash,
        contract_hash=fingerprint(contract),
        metadata_hash=fingerprint(metadata),
        documentation_hash=fingerprint(documentation),
        signature=Signature.of(capability),
    )


def _bump(before: LockEntry, after: LockEntry) -> Bump:
    if before.contract_hash != after.contract_hash:
        return max(before.signature.bump_to(after.signature), Bump.MINOR)
    if before.metadata_hash != after.metadata_hash:
        return Bump.MINOR
    if before.documentation_hash != after.documentation_hash:
        return Bump.PATCH
    return Bump.NONE


def _increment(version: str, bump: Bump) -> str:
    major, minor, patch = (int(part) for part in version.split("."))
    if bump is Bump.MAJOR:
        return f"{major + 1}.0.0"
    if bump is Bump.MINOR:
        return f"{major}.{minor + 1}.0"
    if bump is Bump.PATCH:
        return f"{major}.{minor}.{patch + 1}"
    return version


def _strip_documentation(schema: JsonSchema) -> JsonSchema:
    stripped: JsonSchema = {}
    for key, value in schema.items():
        if key in _DOCUMENTATION_KEYS:
            continue
        if isinstance(value, Mapping):
            stripped[key] = _strip_documentation(cast("JsonSchema", value))
        else:
            stripped[key] = value
    return stripped


def _apply_overrides(capabilities: Iterable[Capability], path: Path) -> list[Capability]:
    if not path.is_file():
        return list(capabilities)
    document = cast("dict[str, Any]", yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    overrides = cast("dict[str, dict[str, Any]]", document.get("capabilities", {}))
    result: list[Capability] = []
    for capability in capabilities:
        patch = overrides.get(capability.id)
        if patch is None:
            result.append(capability)
            continue
        if "idempotency" in patch:
            patch = {
                **patch,
                "idempotency": {
                    **patch["idempotency"],
                    "provenance": "declared",
                    "confidence": 1.0,
                    "inferred_by": None,
                },
            }
        merged = _deep_merge(capability.model_dump(mode="json"), patch)
        result.append(Capability.model_validate(merged))
    return result


def _deep_merge(base: dict[str, Any], patch: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        current = merged.get(key)
        if isinstance(value, Mapping) and isinstance(current, dict):
            merged[key] = _deep_merge(
                cast("dict[str, Any]", current), cast("Mapping[str, Any]", value)
            )
        else:
            merged[key] = value
    return merged


def _document(capability: Capability, workflows: Mapping[str, Workflow]) -> Document:
    fields: list[tuple[str, int]] = [
        (capability.title, 3),
        (capability.id.rsplit("/", 1)[-1], 3),
        (capability.description, 1),
        (capability.category, 1),
    ]
    for parameter in capability.inputs + capability.outputs:
        fields.append((parameter.name, 2))
        if parameter.description:
            fields.append((parameter.description, 1))
    workflow = workflows.get(capability.id)
    if workflow is not None:
        fields.extend((node.label, 1) for node in workflow.nodes)
    return Document(key=capability.id, fields=fields)
