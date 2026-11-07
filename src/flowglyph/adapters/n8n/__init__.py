"""Adapter for n8n workflows exported as JSON, one workflow or a list of them per file.

Every workflow becomes a capability started the way its trigger says: a webhook, a form, a
schedule or another workflow. Its nodes decide the effects, `Execute Workflow` nodes link
workflows into a call graph, and the credentials it uses are recorded by name, never by value.
"""

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, cast

from flowglyph._internal.hashing import digest
from flowglyph._internal.paths import distinguishing_names
from flowglyph.adapters import Diagnostic, Extraction
from flowglyph.adapters.n8n.nodes import (
    CALL,
    DECISIONS,
    is_trigger,
    node_effects,
    short_type,
)
from flowglyph.ir import (
    Capability,
    Edge,
    Effects,
    Idempotency,
    JsonSchema,
    Node,
    Source,
    Trigger,
    Workflow,
)

_MAX_BYTES = 20 * 1024 * 1024
_UNSAFE = re.compile(r"[^\w.-]+")
_MARKDOWN_NOISE = re.compile(r"!\[[^\]]*\]\([^)]*\)|^#+\s*", re.M)
_INPUT_TYPES = {"string", "number", "boolean", "array", "object"}
_TRIGGER_ORDER = ("webhook", "formTrigger", "executeWorkflowTrigger", "scheduleTrigger", "cron")
_IF_OUTPUTS = 2


@dataclass
class _Entry:
    artifact: str
    source_hash: str
    workflow: dict[str, Any]
    capability_id: str = ""
    calls: list[str] = field(default_factory=list[str])
    unresolved: list[str] = field(default_factory=list[str])


class N8nAdapter:
    """Turns n8n workflows into capabilities, linked through their Execute Workflow nodes."""

    name: ClassVar[str] = "n8n"
    version: ClassVar[str] = "0.1.0"

    def detect(self, path: Path) -> bool:
        """Whether `path` is an n8n export or a folder holding one."""
        return bool(_files(path))

    def discover(self, root: Path) -> list[Path]:
        """`root` itself when it holds n8n exports: they are read together to resolve calls."""
        return [root] if _files(root) else []

    def extract(self, path: Path) -> Extraction:
        """Extract every workflow at `path`."""
        root = path if path.is_dir() else path.parent
        entries: list[_Entry] = []
        artifacts: dict[str, str] = {}
        for file in _files(path):
            artifact = file.relative_to(root).as_posix()
            data = file.read_bytes()
            artifacts[artifact] = digest(data)
            entries.extend(
                _Entry(artifact, artifacts[artifact], workflow) for workflow in _workflows(data)
            )
        _assign_ids(entries)
        by_reference = _references(entries)
        diagnostics: list[Diagnostic] = []
        capabilities: dict[str, Capability] = {}
        graphs: list[Workflow] = []
        for entry in entries:
            graph = _graph(entry, by_reference)
            graphs.append(graph)
            diagnostics.extend(
                Diagnostic("warning", entry.artifact, f"calls workflow {call}, not in the sources")
                for call in graph.unresolved_calls
            )
            capabilities[entry.capability_id] = self._capability(entry)
        _propagate(capabilities, graphs)
        return Extraction(
            capabilities=list(capabilities.values()),
            workflows=graphs,
            artifacts=artifacts,
            diagnostics=diagnostics,
        )

    def _capability(self, entry: _Entry) -> Capability:
        workflow = entry.workflow
        nodes = _nodes(workflow)
        effects = Effects.combine([e for node in nodes if (e := node_effects(node))])
        trigger, inputs, invocable = _trigger(nodes, workflow)
        name = str(workflow.get("name") or entry.capability_id)
        return Capability(
            id=entry.capability_id,
            kind="workflow",
            title=name,
            description=_description(nodes, name) or f"n8n workflow {name}.",
            category="n8n",
            input_schema=inputs,
            effects=effects,
            idempotency=Idempotency(mode="natural", confidence=0.8)
            if not effects.has_side_effects
            else Idempotency(mode="none", confidence=0.7),
            trigger=trigger,
            configuration=_credentials(nodes),
            tags=_tags(workflow),
            source=Source(
                provider=self.name,
                artifact=str(workflow.get("id") or name),
                location=entry.artifact,
                source_hash=entry.source_hash,
                artifact_version=str(workflow["versionId"]) if workflow.get("versionId") else None,
            ),
            invocable=invocable,
        )


def _files(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix.lower() == ".json" and _looks_like_n8n(path) else []
    if not path.is_dir():
        return []
    return sorted(
        file
        for file in path.rglob("*.json")
        if ".git" not in file.parts and "node_modules" not in file.parts and _looks_like_n8n(file)
    )


def _looks_like_n8n(file: Path) -> bool:
    if file.stat().st_size > _MAX_BYTES:
        return False
    data = file.read_bytes()
    return b'"connections"' in data and b"n8n-nodes-" in data and bool(_workflows(data))


def _workflows(data: bytes) -> list[dict[str, Any]]:
    """The workflows in an export: one object, or a list as `n8n export:workflow --all` writes."""
    try:
        document: Any = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []
    candidates = cast("list[Any]", document) if isinstance(document, list) else [document]
    objects = [cast("dict[str, Any]", item) for item in candidates if isinstance(item, dict)]
    return [
        item
        for item in objects
        if isinstance(item.get("nodes"), list) and isinstance(item.get("connections"), dict)
    ]


def _nodes(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    return [node for node in cast("list[Any]", workflow["nodes"]) if isinstance(node, dict)]


def _assign_ids(entries: list[_Entry]) -> None:
    groups: defaultdict[str, list[_Entry]] = defaultdict(list)
    for entry in entries:
        name = str(entry.workflow.get("name") or Path(entry.artifact).stem)
        groups[_UNSAFE.sub("_", name).strip("_") or "workflow"].append(entry)
    for key, group in groups.items():
        if len(group) == 1:
            group[0].capability_id = f"n8n/{key}"
            continue
        suffixes = distinguishing_names([entry.artifact for entry in group])
        for entry, suffix in zip(group, suffixes, strict=True):
            entry.capability_id = f"n8n/{key}.{_UNSAFE.sub('_', suffix)}"


def _references(entries: list[_Entry]) -> dict[str, str]:
    """Workflow ids, names and file names, each mapped to the capability it identifies."""
    found: dict[str, str] = {}
    for entry in entries:
        for reference in (entry.workflow.get("name"), Path(entry.artifact).name):
            if reference:
                found.setdefault(str(reference), entry.capability_id)
        if entry.workflow.get("id"):
            found[str(entry.workflow["id"])] = entry.capability_id
    return found


def _called(node: dict[str, Any]) -> list[str]:
    """What an Execute Workflow node points at: its id, its cached name, or a file path."""
    parameters: dict[str, Any] = node.get("parameters") or {}
    if parameters.get("source") == "localFile":
        return [Path(str(parameters.get("workflowPath", ""))).name]
    target: Any = parameters.get("workflowId")
    if isinstance(target, dict):
        locator = cast("dict[str, Any]", target)
        found: list[Any] = [locator.get("value"), locator.get("cachedResultName")]
        return [str(value) for value in found if value]
    return [str(target)] if target else []


def _graph(entry: _Entry, references: dict[str, str]) -> Workflow:
    nodes = {str(node.get("name")): node for node in _nodes(entry.workflow)}
    kept: dict[str, Node] = {}
    calls: list[str] = []
    unresolved: list[str] = []
    for name, node in nodes.items():
        kind = short_type(node)
        if kind == CALL:
            targets = _called(node)
            capability = next((references[t] for t in targets if t in references), None)
            if capability:
                calls.append(capability)
            else:
                unresolved.append(targets[0] if targets else name)
            kept[name] = Node(
                id=name,
                kind="invoke" if capability else "activity",
                label=name,
                capability=capability,
            )
        elif kind in DECISIONS:
            kept[name] = Node(id=name, kind="decision", label=name)
        elif node_effects(node) is not None:
            kept[name] = Node(id=name, kind="activity", label=f"{name} ({kind})")
    edges = _edges(entry.workflow, nodes, set(kept))
    sources: defaultdict[str, set[str]] = defaultdict(set)
    for edge in edges:
        sources[edge.target].add(edge.source)
    graph_nodes = [
        node.model_copy(update={"join": "any"}) if len(sources[node.id]) > 1 else node
        for node in kept.values()
    ]
    return Workflow(
        id=entry.capability_id,
        capability=entry.capability_id,
        nodes=tuple(graph_nodes),
        edges=tuple(edges),
        calls=tuple(dict.fromkeys(calls)),
        unresolved_calls=tuple(dict.fromkeys(unresolved)),
    )


def _edges(
    workflow: dict[str, Any], nodes: dict[str, dict[str, Any]], kept: set[str]
) -> list[Edge]:
    """Edges between kept nodes, following connections through the nodes that were folded."""
    outgoing: defaultdict[str, list[tuple[str, str | None]]] = defaultdict(list)
    connections = cast("dict[str, Any]", workflow["connections"])
    for source, kinds in connections.items():
        node = nodes.get(source, {})
        outputs = cast("list[Any]", cast("dict[str, Any]", kinds).get("main") or [])
        for index, targets in enumerate(outputs):
            condition = _branch(node, index, len(outputs))
            for target in cast("list[dict[str, Any]]", targets or []):
                outgoing[source].append((str(target.get("node")), condition))
    starts = kept | {name for name, node in nodes.items() if is_trigger(node)}
    edges: set[Edge] = set()
    for start in starts:
        seen: set[str] = set()
        pending = list(outgoing[start])
        while pending:
            target, condition = pending.pop()
            if target in kept and start in kept:
                edges.add(Edge(source=start, target=target, condition=condition))
            elif target not in seen and target not in kept:
                seen.add(target)
                pending.extend((nxt, condition or cond) for nxt, cond in outgoing[target])
    return sorted(edges, key=lambda e: (e.source, e.target, e.condition or ""))


def _branch(node: dict[str, Any], index: int, outputs: int) -> str | None:
    """The condition of one output of a branching node: `true`, `false`, or the output number."""
    kind = short_type(node)
    if kind == "if" and outputs == _IF_OUTPUTS:
        return "true" if index == 0 else "false"
    if kind in {"switch", "filter"} and outputs > 1:
        return f"output {index}"
    return None


def _trigger(
    nodes: list[dict[str, Any]], workflow: dict[str, Any]
) -> tuple[Trigger | None, JsonSchema, bool]:
    """How the workflow starts, what it receives, and whether an outside caller can start it."""
    triggers = sorted(
        (node for node in nodes if is_trigger(node) and not node.get("disabled")),
        key=lambda node: (
            _TRIGGER_ORDER.index(short_type(node)) if short_type(node) in _TRIGGER_ORDER else 9
        ),
    )
    empty: JsonSchema = {"type": "object", "properties": {}, "additionalProperties": False}
    if not triggers:
        return None, empty, False
    node = triggers[0]
    kind = short_type(node)
    parameters: dict[str, Any] = node.get("parameters") or {}
    if kind == "webhook":
        return _webhook(node, parameters)
    if kind == "executeWorkflowTrigger":
        reference = str(workflow.get("id") or workflow.get("name") or "")
        trigger = Trigger(channel="Execute Workflow", address=reference or None)
        return trigger, _declared_inputs(parameters), False
    if kind in {"scheduleTrigger", "cron"}:
        schedule = Trigger(kind="schedule", channel="schedule", address=_schedule(parameters))
        return schedule, empty, False
    if kind == "formTrigger":
        started, invocable = Trigger(channel="n8n form", address=parameters.get("path")), True
    elif kind == "manualTrigger":
        started, invocable = Trigger(channel="manual"), False
    else:
        started, invocable = Trigger(kind="event", channel=kind.removesuffix("Trigger")), False
    return started, empty, invocable


def _webhook(node: dict[str, Any], parameters: dict[str, Any]) -> tuple[Trigger, JsonSchema, bool]:
    method = str(parameters.get("httpMethod") or "GET").upper()
    path = str(parameters.get("path") or node.get("webhookId") or "")
    inputs: JsonSchema = {
        "type": "object",
        "properties": {
            "body": {"type": "object", "description": "the request body"},
            "query": {"type": "object", "description": "query string parameters"},
        },
        "additionalProperties": False,
    }
    return Trigger(channel="HTTP", address=f"{method} /webhook/{path}"), inputs, True


def _declared_inputs(parameters: dict[str, Any]) -> JsonSchema:
    values = cast(
        "list[dict[str, Any]]",
        cast("dict[str, Any]", parameters.get("workflowInputs") or {}).get("values") or [],
    )
    properties: dict[str, JsonSchema] = {}
    for value in values:
        name = str(value.get("name") or "")
        if not name:
            continue
        declared = str(value.get("type") or "any")
        properties[name] = {"type": declared} if declared in _INPUT_TYPES else {}
    return {
        "type": "object",
        "properties": properties,
        "required": [],
        "additionalProperties": not properties,
    }


def _schedule(parameters: dict[str, Any]) -> str | None:
    rule = cast("dict[str, Any]", parameters.get("rule") or {})
    intervals = cast("list[Any]", rule.get("interval") or [])
    items = [cast("dict[str, Any]", item) for item in intervals if isinstance(item, dict)]
    parts = [str(item.get("expression") or item.get("field") or "") for item in items]
    return ", ".join(part for part in parts if part) or None


def _description(nodes: list[dict[str, Any]], name: str) -> str:
    """The first sticky note's text: where n8n users write what a workflow is for."""
    for node in nodes:
        if short_type(node) == "stickyNote":
            content = str(cast("dict[str, Any]", node.get("parameters") or {}).get("content") or "")
            lines = _MARKDOWN_NOISE.sub("", content).strip().splitlines()
            if lines and lines[0].strip().lower() == name.lower():
                lines = lines[1:]
            text = "\n".join(lines).strip()
            if text:
                return text[:1000]
    return ""


def _tags(workflow: dict[str, Any]) -> tuple[str, ...]:
    tags: list[Any] = cast("list[Any]", workflow.get("tags") or [])
    names = [cast("dict[str, Any]", tag).get("name") for tag in tags if isinstance(tag, dict)]
    return tuple(str(name) for name in names if name)


def _credentials(nodes: list[dict[str, Any]]) -> tuple[str, ...]:
    """Credentials by type and name, as the export records them; n8n never exports secrets."""
    found: set[str] = set()
    for node in nodes:
        credentials = cast("dict[str, Any]", node.get("credentials") or {})
        for kind, reference in credentials.items():
            details = cast("dict[str, Any]", reference) if isinstance(reference, dict) else {}
            label: Any = details.get("name")
            found.add(f"{kind}: {label}" if label else kind)
    return tuple(sorted(found))


def _propagate(capabilities: dict[str, Capability], graphs: list[Workflow]) -> None:
    """Give each workflow the effects of the workflows it calls, until nothing changes."""
    calls = {graph.capability: graph.calls for graph in graphs}
    changed = True
    while changed:
        changed = False
        for capability_id, callees in calls.items():
            capability = capabilities[capability_id]
            effects = Effects.combine(
                [
                    capability.effects,
                    *(capabilities[c].effects for c in callees if c in capabilities),
                ]
            )
            if effects != capability.effects:
                idempotency = capability.idempotency
                if effects.has_side_effects and idempotency.mode == "natural":
                    idempotency = Idempotency(mode="none", confidence=0.7)
                capabilities[capability_id] = capability.model_copy(
                    update={"effects": effects, "idempotency": idempotency}
                )
                changed = True


__all__ = ["N8nAdapter"]
