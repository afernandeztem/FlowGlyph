"""The catalog: capabilities and workflows extracted together, searchable and saved to disk."""

import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from flowglyph._internal import markdown
from flowglyph._internal.search import BM25Index, Document
from flowglyph.adapters import Diagnostic
from flowglyph.catalog.lock import LOCK_FILE, Lock
from flowglyph.catalog.versioning import Change
from flowglyph.errors import CatalogError
from flowglyph.ir import IR_VERSION, Capability, CapabilityKind, Workflow


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

    def problems(self) -> list[str]:
        """Broken references inside the catalog: what `flowglyph validate` reports."""
        found: list[str] = []
        for workflow in self.workflows.values():
            if workflow.capability not in self.capabilities:
                found.append(f"workflow {workflow.id} belongs to unknown {workflow.capability}")
            node_ids = {node.id for node in workflow.nodes}
            found.extend(
                f"workflow {workflow.id} node {node.id} references unknown {node.capability}"
                for node in workflow.nodes
                if node.capability and node.capability not in self.capabilities
            )
            found.extend(
                f"workflow {workflow.id} edge {edge.source} -> {edge.target} leaves the graph"
                for edge in workflow.edges
                if edge.source not in node_ids or edge.target not in node_ids
            )
        for capability in self.capabilities.values():
            entry = self.lock.capabilities.get(capability.id)
            if entry is None:
                found.append(f"{capability.id} is missing from the lock file")
            elif entry.version != capability.version:
                found.append(
                    f"{capability.id} is {capability.version} but the lock says {entry.version}"
                )
            compensation = capability.idempotency.compensation
            if compensation and compensation not in self.capabilities:
                found.append(f"{capability.id} is compensated by unknown {compensation}")
        return found

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
        (target / "catalog.jsonl").write_text(
            "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
        )
        graph = {
            "ir_version": IR_VERSION,
            "workflows": [
                self.workflows[key].model_dump(mode="json") for key in sorted(self.workflows)
            ],
        }
        (target / "graph.json").write_text(
            json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        self.lock.write(target / LOCK_FILE)
        expected = {markdown.card_filename(c) for c in self}
        for stale in cards.glob("*.md"):
            if stale.name not in expected:
                stale.unlink()
        for capability in self:
            text = markdown.render_capability(capability, self.workflows, self.capabilities)
            (cards / markdown.card_filename(capability)).write_text(
                text, encoding="utf-8", newline="\n"
            )
        (target / "INDEX.md").write_text(
            markdown.render_index(self), encoding="utf-8", newline="\n"
        )
        return target


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
