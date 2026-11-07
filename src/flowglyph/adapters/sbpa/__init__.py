"""Adapter for SAP Build Process Automation projects, exported as `.mtar` or unpacked.

Every process becomes a workflow capability whose graph runs automations, forms and decisions.
Automations and decisions become capabilities of their own that processes invoke. Starting a
process always creates an instance, so no process is naturally idempotent.
"""

import re
from collections import defaultdict
from pathlib import Path
from typing import Any, ClassVar, cast

from flowglyph._internal.hashing import digest
from flowglyph.adapters import Diagnostic, Extraction
from flowglyph.adapters.sbpa.package import (
    AUTOMATION,
    DECISION,
    PROCESS,
    Artifact,
    Project,
    is_mtar,
    is_project_directory,
    read_directory,
    read_mtar,
)
from flowglyph.errors import AdapterError
from flowglyph.ir import (
    Capability,
    Edge,
    Effects,
    Idempotency,
    JsonSchema,
    Node,
    Source,
    Tri,
    Trigger,
    Workflow,
)

_WFS = "com.sap.bpm.wfs."
_UNSAFE = re.compile(r"[^\w.-]+")
_STEP_ID = re.compile(r"^(?:automation|decision|subprocess|action)_(?P<identifier>.+)_\d+$")
_INSTANCE = Effects(reads=Tri.NO, mutates_state=Tri.YES, destructive=Tri.NO, external=Tri.YES)
_PERSON = Effects(reads=Tri.NO, mutates_state=Tri.NO, destructive=Tri.NO, external=Tri.YES)
_PURE = Effects(reads=Tri.NO, mutates_state=Tri.NO, destructive=Tri.NO, external=Tri.NO)
_SEND = Effects(reads=Tri.NO, mutates_state=Tri.YES, destructive=Tri.NO, external=Tri.YES)
_UNKNOWN = Effects(
    reads=Tri.UNKNOWN, mutates_state=Tri.UNKNOWN, destructive=Tri.UNKNOWN, external=Tri.YES
)
_STEP_EFFECTS = {
    "UserTask": _PERSON,
    "RuleTask": _PURE,
    "MailTask": _SEND,
    "ActionTask": _UNKNOWN,
    "ScriptTask": _UNKNOWN,
}
_ROUTING = frozenset({"StartEvent", "EndEvent", "IntermediateTimerEvent", "BoundaryEvent"})
_SIMPLE_TYPES = {"string": "string", "number": "number", "boolean": "boolean", "date": "string"}
_SCHEMA_KEYS = frozenset(
    {"type", "properties", "required", "items", "format", "enum", "description", "title"}
)
_INSTANCE_NOTE = "each start creates a new process instance"


class SapBuildProcessAutomationAdapter:
    """Turns SAP Build Process Automation projects into processes, automations and decisions.

    Processes are workflows that run automations (desktop and API bots), forms (people) and
    decisions (business rules). Effects come from those steps.
    """

    name: ClassVar[str] = "sbpa"
    version: ClassVar[str] = "0.1.0"

    def detect(self, path: Path) -> bool:
        """Whether `path` is an exported project or a folder holding one."""
        return bool(self.discover(path))

    def discover(self, root: Path) -> list[Path]:
        """Every `.mtar` export and unpacked project under `root`, each read on its own."""
        if root.is_file():
            return [root] if is_mtar(root) else []
        if not root.is_dir():
            return []
        found = [file for file in sorted(root.rglob("*.mtar")) if is_mtar(file)]
        found.extend(
            manifest.parent
            for manifest in sorted(root.rglob("project.json"))
            if is_project_directory(manifest.parent)
        )
        return found

    def extract(self, path: Path) -> Extraction:
        """Extract the project or projects at `path`."""
        location = path.name
        try:
            if path.is_file():
                projects = read_mtar(path, location)
                source_hash = digest(path.read_bytes())
            else:
                projects = [read_directory(path)]
                source_hash = digest(
                    b"".join(file.read_bytes() for file in sorted(path.rglob("*.json")))
                )
        except AdapterError as error:
            return Extraction(diagnostics=[Diagnostic("error", location, str(error))])
        capabilities: list[Capability] = []
        workflows: list[Workflow] = []
        diagnostics: list[Diagnostic] = []
        for project in projects:
            found, graphs, notes = _extract_project(project, location, source_hash)
            capabilities.extend(found)
            workflows.extend(graphs)
            diagnostics.extend(notes)
        return Extraction(
            capabilities=capabilities,
            workflows=workflows,
            artifacts={location: source_hash},
            diagnostics=diagnostics,
        )


def _extract_project(
    project: Project, location: str, source_hash: str
) -> tuple[list[Capability], list[Workflow], list[Diagnostic]]:
    prefix = f"sbpa/{_slug(project.name)}"
    ids = {uid: f"{prefix}/{_slug(a.identifier)}" for uid, a in project.artifacts.items()}

    def source(artifact: Artifact) -> Source:
        return Source(
            provider="sbpa",
            artifact=artifact.identifier,
            location=f"{location}#{artifact.name}",
            source_hash=source_hash,
            artifact_version=project.version,
        )

    used_in: defaultdict[str, list[str]] = defaultdict(list)
    capabilities: list[Capability] = []
    workflows: list[Workflow] = []
    diagnostics: list[Diagnostic] = []
    for artifact in project.of_type(PROCESS):
        model = _model(artifact)
        if not model:
            diagnostics.append(Diagnostic("warning", location, f"{artifact.name} has no model"))
            continue
        workflow, effects = _graph(ids[artifact.uid], model, project, ids)
        for call in workflow.calls:
            used_in[call].append(artifact.name)
        workflows.append(workflow)
        trigger, invocable = _trigger(artifact)
        capabilities.append(
            Capability(
                id=ids[artifact.uid],
                kind="workflow",
                title=artifact.name,
                description=artifact.description or project.description,
                category=project.name,
                input_schema=_process_inputs(model),
                effects=Effects.combine([_INSTANCE, *effects]),
                idempotency=Idempotency(mode="none", confidence=0.8),
                trigger=trigger,
                notes=(_INSTANCE_NOTE,),
                source=source(artifact),
                invocable=invocable,
            )
        )
    for artifact in project.of_type(AUTOMATION) + project.of_type(DECISION):
        automation = artifact.type == AUTOMATION
        capabilities.append(
            Capability(
                id=ids[artifact.uid],
                kind="workflow" if automation else "operation",
                title=artifact.name,
                description=artifact.description or artifact.name,
                category="automation" if automation else "decision",
                input_schema=_header_schema(artifact.header.get("inputs")),
                output_schema=_header_schema(artifact.header.get("outputs")),
                effects=_UNKNOWN if automation else _PURE,
                idempotency=Idempotency(mode="none", confidence=0.6)
                if automation
                else Idempotency(mode="natural", confidence=0.9),
                used_in=tuple(sorted(used_in[ids[artifact.uid]])),
                source=source(artifact),
                invocable=False,
            )
        )
    return capabilities, workflows, diagnostics


def _model(artifact: Artifact) -> dict[str, dict[str, Any]]:
    """The elements of a process model, keyed by their uid."""
    body = cast("dict[str, Any]", artifact.content.get("artifact") or artifact.content)
    model = cast("dict[str, Any]", body.get("model") or {})
    contents = cast("dict[str, Any]", model.get("contents") or {})
    return {
        key: cast("dict[str, Any]", value)
        for key, value in contents.items()
        if isinstance(value, dict)
    }


def _kind(element: dict[str, Any]) -> str:
    return str(element.get("classDefinition", "")).removeprefix(_WFS)


def _graph(
    capability_id: str,
    model: dict[str, dict[str, Any]],
    project: Project,
    ids: dict[str, str],
) -> tuple[Workflow, list[Effects]]:
    """The process graph, and the effects of its steps."""
    flows = [element for element in model.values() if _kind(element) == "SequenceFlow"]
    steps = {
        key: element
        for key, element in model.items()
        if _kind(element) not in {"Model", "Schemas", "SequenceFlow", *_ROUTING}
    }
    nodes: list[Node] = []
    calls: list[str] = []
    unresolved: list[str] = []
    effects: list[Effects] = []
    for key, element in steps.items():
        kind = _kind(element)
        name = str(element.get("name") or element.get("id") or key)
        target_uid = str(element.get("artifactId") or "") or _by_step_id(element, project)
        target = project.artifacts.get(target_uid)
        if kind == "AutomationTask" or (target is not None and target.type == PROCESS):
            called = ids.get(target_uid)
            if called:
                calls.append(called)
            else:
                unresolved.append(target_uid or name)
            effects.append(_UNKNOWN)
            node = Node(
                id=key, kind="invoke" if called else "activity", label=name, capability=called
            )
        elif target is not None and target.type == DECISION:
            calls.append(ids[target_uid])
            effects.append(_PURE)
            node = Node(id=key, kind="invoke", label=name, capability=ids[target_uid])
        elif kind.endswith("Gateway"):
            node = Node(id=key, kind="decision", label=name)
        else:
            effects.append(_STEP_EFFECTS.get(kind, _UNKNOWN))
            label = f"{name} (form)" if kind == "UserTask" else f"{name} ({kind})"
            node = Node(id=key, kind="activity", label=label)
        nodes.append(node)
    edges = _edges(flows, set(steps))
    sources: defaultdict[str, set[str]] = defaultdict(set)
    for edge in edges:
        sources[edge.target].add(edge.source)
    nodes = [
        node.model_copy(update={"join": "any"}) if len(sources[node.id]) > 1 else node
        for node in nodes
    ]
    workflow = Workflow(
        id=capability_id,
        capability=capability_id,
        nodes=tuple(nodes),
        edges=tuple(edges),
        calls=tuple(dict.fromkeys(calls)),
        unresolved_calls=tuple(dict.fromkeys(unresolved)),
    )
    return workflow, effects


def _by_step_id(element: dict[str, Any], project: Project) -> str:
    """The artifact a step runs, read from the id SAP gives it: `decision_<identifier>_<n>`."""
    match = _STEP_ID.match(str(element.get("id") or ""))
    if match is None:
        return ""
    identifier = match["identifier"]
    return next(
        (uid for uid, artifact in project.artifacts.items() if artifact.identifier == identifier),
        "",
    )


def _edges(flows: list[dict[str, Any]], kept: set[str]) -> list[Edge]:
    outgoing: defaultdict[str, list[tuple[str, str | None]]] = defaultdict(list)
    for flow in flows:
        condition = flow.get("condition")
        outgoing[str(flow.get("sourceRef"))].append(
            (str(flow.get("targetRef")), str(condition) if condition else None)
        )
    edges: set[Edge] = set()
    for start in kept:
        seen: set[str] = set()
        pending = list(outgoing[start])
        while pending:
            target, condition = pending.pop()
            if target in kept:
                edges.add(Edge(source=start, target=target, condition=condition))
            elif target not in seen:
                seen.add(target)
                pending.extend((nxt, condition or cond) for nxt, cond in outgoing[target])
    return sorted(edges, key=lambda e: (e.source, e.target, e.condition or ""))


def _trigger(artifact: Artifact) -> tuple[Trigger, bool]:
    """Forms are started by people; an API trigger lets a caller start the process."""
    content = cast("dict[str, Any]", artifact.content.get("artifact") or artifact.content)
    meta = cast("dict[str, Any]", content.get("metaData") or {})
    triggers = cast("list[dict[str, Any]]", meta.get("triggers") or [])
    for trigger in triggers:
        kind = str(trigger.get("type") or "")
        if "api" in kind.lower():
            return Trigger(channel="SAP Build API trigger", address=artifact.identifier), True
    if triggers:
        body = cast("dict[str, Any]", triggers[0].get("body") or {})
        return Trigger(channel="SAP Build form", address=str(body.get("name") or "") or None), False
    return Trigger(channel="SAP Build Process Automation", address=artifact.identifier), False


def _process_inputs(model: dict[str, dict[str, Any]]) -> JsonSchema:
    """What the start event hands the process: the JSON Schema its form or trigger declares."""
    schemas: dict[str, Any] = _field(_first(model, "Schemas"), "schemas")
    interface: dict[str, Any] = _field(_field(_first(model, "StartEvent"), "interfaces"), "out")
    content: dict[str, Any] = _field(_field(schemas, str(interface.get("schema"))), "content")
    definition = str(interface.get("definition") or "").removeprefix("#/definitions/")
    found: dict[str, Any] = _field(_field(content, "definitions"), definition)
    cleaned: JsonSchema = _clean(found, top=True) if found else {"type": "object", "properties": {}}
    cleaned["additionalProperties"] = False
    return cleaned


def _first(model: dict[str, dict[str, Any]], kind: str) -> dict[str, Any]:
    empty: dict[str, Any] = {}
    return next((element for element in model.values() if _kind(element) == kind), empty)


def _field(data: dict[str, Any], name: str) -> dict[str, Any]:
    value: Any = data.get(name)
    return cast("dict[str, Any]", value) if isinstance(value, dict) else {}


def _clean(schema: dict[str, Any], *, top: bool = False) -> JsonSchema:
    """A JSON Schema without SAP's editor metadata (`uid`, `dimension`, `$schema`).

    A field's title becomes its description when it has none; the schema's own title (`input`,
    `output`) is dropped, since it names the editor's slot, not the data.
    """
    cleaned: JsonSchema = {}
    for key, value in schema.items():
        if key not in _SCHEMA_KEYS or value in ("", None):
            continue
        if key == "properties":
            properties = _field(schema, "properties")
            cleaned[key] = {name: _clean(_field(properties, name)) for name in properties}
        elif key == "items":
            cleaned[key] = _clean(_field(schema, "items"))
        elif key == "title":
            if not top:
                cleaned.setdefault("description", value)
        else:
            cleaned[key] = value
    return cleaned


def _header_schema(parameters: Any) -> JsonSchema:
    """The inputs or outputs an automation or decision declares in its header."""
    properties: dict[str, JsonSchema] = {}
    for parameter in cast(
        "list[dict[str, Any]]", parameters if isinstance(parameters, list) else []
    ):
        name = str(parameter.get("identifier") or "")
        if not name:
            continue
        simple = str(parameter.get("type", "")).lower() == "simple"
        json_type = (
            _SIMPLE_TYPES.get(str(parameter.get("typeName", "")).lower(), "object")
            if simple
            else "object"
        )
        spec: JsonSchema = {"type": json_type}
        if int(parameter.get("dimension") or 0) > 0:
            spec = {"type": "array", "items": spec}
        if parameter.get("description"):
            spec["description"] = str(parameter["description"])
        if not simple and parameter.get("typeName"):
            spec["x-sbpa-type"] = str(parameter["typeName"])
        properties[name] = spec
    return {"type": "object", "properties": properties, "additionalProperties": False}


def _slug(text: str) -> str:
    return _UNSAFE.sub("_", text).strip("_") or "artifact"


__all__ = ["SapBuildProcessAutomationAdapter"]
