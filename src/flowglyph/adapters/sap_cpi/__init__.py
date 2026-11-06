"""Adapter for SAP Cloud Integration (SAP Integration Suite) integration flows.

Reads iFlows exported as `.zip` artifacts or unpacked into folders. Every endpoint an iFlow
exposes becomes a capability; its receivers and steps decide the effects; ProcessDirect links
between iFlows become calls in the workflow graph; and design problems that make an iFlow fragile
are reported, so `flowglyph wiki lint` can point at them.
"""

import re
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from flowglyph._internal.hashing import digest
from flowglyph._internal.paths import distinguishing_names
from flowglyph._internal.xml import parse_xml
from flowglyph.adapters import Diagnostic, Extraction
from flowglyph.adapters.sap_cpi.bundle import Bundle, manifest_type, read_directory, read_zip
from flowglyph.adapters.sap_cpi.iflow import Channel, IFlow, Process, Step, parse_iflow
from flowglyph.adapters.sap_cpi.rules import (
    channel_effects,
    declared_idempotency,
    design_findings,
    step_effects,
)
from flowglyph.errors import AdapterError
from flowglyph.ir import (
    Capability,
    Edge,
    Effects,
    Idempotency,
    JsonSchema,
    Node,
    Security,
    Source,
    Trigger,
    Workflow,
)

_UNSAFE = re.compile(r"[^A-Za-z0-9.-]+")
_KEPT_ACTIVITIES = frozenset({"ExternalCall", "ProcessCallElement", "DBstorage", "Script"})
_INVOCABLE_SENDERS = frozenset(
    {"HTTPS", "HTTP", "SOAP", "PROCESSDIRECT", "ODATA", "HCIODATA", "IDOC", "REST", "AS2", "AS4"}
)


@dataclass
class _Entry:
    bundle: Bundle
    artifact: str
    source_hash: str
    iflow: IFlow
    key: str = ""
    capabilities: list[Capability] = field(default_factory=list[Capability])


class SapCpiAdapter:
    """Turns SAP Cloud Integration iFlows into capabilities, one per endpoint they expose.

    Receivers and steps decide the effects. Idempotency is taken from what the iFlow itself
    declares (an idempotent process call, an exactly-once adapter) before anything is inferred.
    """

    name: ClassVar[str] = "sap-cpi"
    version: ClassVar[str] = "0.1.0"

    def detect(self, path: Path) -> bool:
        """Whether `path` is an iFlow artifact or a folder containing one."""
        return bool(_artifacts(path))

    def discover(self, root: Path) -> list[Path]:
        """`root` itself when it holds iFlows: they are read together to resolve their links."""
        return [root] if _artifacts(root) else []

    def extract(self, path: Path) -> Extraction:
        """Extract every iFlow at `path`."""
        root = path if path.is_dir() else path.parent
        entries: list[_Entry] = []
        artifacts: dict[str, str] = {}
        diagnostics: list[Diagnostic] = []
        for artifact_path in _artifacts(path):
            location = artifact_path.relative_to(root).as_posix() or artifact_path.name
            try:
                bundle = (
                    read_directory(artifact_path, location)
                    if artifact_path.is_dir()
                    else read_zip(artifact_path, location)
                )
            except AdapterError as error:
                diagnostics.append(Diagnostic("error", location, str(error)))
                continue
            if bundle.bundle_type != "IntegrationFlow" or not bundle.iflows:
                kind = bundle.bundle_type or "artifact"
                diagnostics.append(Diagnostic("info", location, f"{kind}, not an integration flow"))
                continue
            for name, data in bundle.iflows.items():
                artifact = location if artifact_path.is_file() else f"{location}/{name}"
                artifacts[artifact] = digest(data)
                try:
                    document = parse_xml(data, artifact)
                except AdapterError as error:
                    diagnostics.append(Diagnostic("error", artifact, str(error)))
                    continue
                entries.append(_Entry(bundle, artifact, artifacts[artifact], parse_iflow(document)))
        _assign_keys(entries)
        for entry in entries:
            findings = design_findings(entry.iflow)
            notes = tuple(f"{level}: {message}" for level, message in findings)
            entry.capabilities = [
                capability.model_copy(update={"notes": capability.notes + notes})
                for capability in self._capabilities(entry)
            ]
            diagnostics.extend(
                Diagnostic(level, entry.artifact, message) for level, message in findings
            )
        endpoints = _process_direct_endpoints(entries)
        workflows = [_workflow(entry, endpoints) for entry in entries if entry.capabilities]
        _propagate_effects(entries, workflows)
        return Extraction(
            capabilities=[c for entry in entries for c in entry.capabilities],
            workflows=_expand(workflows, entries),
            artifacts=artifacts,
            diagnostics=diagnostics,
        )

    def _capabilities(self, entry: _Entry) -> list[Capability]:
        iflow = entry.iflow
        senders = iflow.senders or [None]
        timer = iflow.main is not None and any(s.event == "timer" for s in iflow.main.steps)
        found: list[Capability] = []
        for sender in senders:
            suffix = (
                f"/{_slug(sender.component + '_' + sender.address)}"
                if len(senders) > 1 and sender
                else ""
            )
            found.append(
                self._capability(entry, sender, f"sap-cpi/{entry.key}{suffix}", timer=timer)
            )
        return found

    def _capability(
        self, entry: _Entry, sender: Channel | None, capability_id: str, *, timer: bool
    ) -> Capability:
        bundle = entry.bundle
        iflow = entry.iflow
        effects = Effects.combine(list(_own_effects(iflow)))
        declared = declared_idempotency(iflow)
        if declared is not None:
            idempotency, note = declared
        elif not effects.has_side_effects:
            idempotency, note = Idempotency(mode="natural", confidence=0.8), None
        else:
            idempotency, note = Idempotency(mode="none", confidence=0.7), None
        trigger = (
            f"{sender.component} {sender.address}".strip()
            if sender
            else ("timer" if timer else "no sender")
        )
        invocable = sender is not None and sender.component.upper() in _INVOCABLE_SENDERS
        if sender is not None:
            started = Trigger(kind="call", channel=sender.component, address=sender.address or None)
        else:
            started = Trigger(kind="schedule", channel="Timer") if timer else None
        return Capability(
            id=capability_id,
            kind="workflow",
            title=bundle.name
            if not sender or len(iflow.senders) <= 1
            else f"{bundle.name} ({trigger})",
            description=f"Integration flow {bundle.name}, started by {trigger}.",
            category=entry.key.split(".", 1)[0],
            input_schema=_input_schema(sender),
            output_schema={
                "type": "object",
                "properties": {"body": {"description": "response payload"}},
            },
            effects=effects,
            idempotency=idempotency,
            security=_security(sender),
            trigger=started,
            configuration=tuple(sorted(iflow.references() | set(bundle.parameters))),
            notes=tuple(n for n in (note,) if n),
            source=Source(
                provider="sap-cpi",
                artifact=bundle.symbolic_name,
                location=entry.artifact,
                source_hash=entry.source_hash,
                artifact_version=bundle.version,
            ),
            invocable=invocable,
        )


def _artifacts(path: Path) -> list[Path]:
    """Exported `.zip` artifacts and unpacked artifact folders under `path`."""
    if path.is_file():
        is_zip = path.suffix == ".zip" and _is_artifact_zip(path)
        return [path] if is_zip or path.suffix == ".iflw" else []
    if not path.is_dir():
        return []
    found: list[Path] = []
    for manifest in sorted(path.rglob("META-INF/MANIFEST.MF")):
        root = manifest.parent.parent
        if manifest_type(manifest.read_bytes()) and any(root.rglob("*.iflw")):
            found.append(root)
    unpacked = set(found)
    found.extend(
        file
        for file in sorted(path.rglob("*.zip"))
        if not any(folder in file.parents for folder in unpacked) and _is_artifact_zip(file)
    )
    found.extend(
        file
        for file in sorted(path.rglob("*.iflw"))
        if not any(folder in file.parents for folder in unpacked)
    )
    return found


def _is_artifact_zip(path: Path) -> bool:
    try:
        bundle = read_zip(path, path.name)
    except AdapterError:
        return False
    return bool(bundle.iflows) or bundle.bundle_type not in {"", "IntegrationFlow"}


def _assign_keys(entries: list[_Entry]) -> None:
    groups: defaultdict[str, list[_Entry]] = defaultdict(list)
    for entry in entries:
        groups[_slug(entry.bundle.symbolic_name)].append(entry)
    for key, group in groups.items():
        if len(group) == 1:
            group[0].key = key
            continue
        versions = [entry.bundle.version or "" for entry in group]
        suffixes = (
            [_slug(version) for version in versions]
            if len(set(versions)) == len(versions) and all(versions)
            else distinguishing_names([entry.artifact for entry in group])
        )
        for entry, suffix in zip(group, suffixes, strict=True):
            entry.key = f"{key}.{suffix}"


def _own_effects(iflow: IFlow) -> Iterable[Effects]:
    for channel in iflow.receivers:
        effects = channel_effects(channel)
        if effects is not None:
            yield effects
    for process in iflow.processes.values():
        for step in process.all_steps:
            effects = step_effects(step)
            if effects is not None:
                yield effects


def _input_schema(sender: Channel | None) -> JsonSchema:
    properties: dict[str, JsonSchema] = {}
    if sender is not None:
        properties["body"] = {
            "description": f"Payload for the {sender.component} endpoint {sender.address}".strip(),
            "x-endpoint": sender.address,
            "x-adapter": sender.component,
        }
    return {
        "type": "object",
        "properties": properties,
        "required": [],
        "additionalProperties": False,
    }


def _security(sender: Channel | None) -> Security:
    if sender is None:
        return Security()
    role = sender.properties.get("userRole")
    return Security(scopes=(role,) if role else ())


def _process_direct_endpoints(entries: list[_Entry]) -> dict[str, str]:
    endpoints: dict[str, str] = {}
    for entry in entries:
        for sender, capability in zip(entry.iflow.senders, entry.capabilities, strict=False):
            if sender.component.upper() == "PROCESSDIRECT" and sender.address:
                endpoints[sender.address] = capability.id
    return endpoints


def _workflow(entry: _Entry, endpoints: dict[str, str]) -> Workflow:
    capability_id = entry.capabilities[0].id
    process = entry.iflow.main
    if process is None:
        return Workflow(id=capability_id, capability=capability_id)
    builder = _GraphBuilder(entry.iflow, process, endpoints, entry.iflow.processes)
    return builder.build(capability_id)


@dataclass
class _GraphBuilder:
    iflow: IFlow
    process: Process
    endpoints: dict[str, str]
    processes: dict[str, Process]
    calls: list[str] = field(default_factory=list[str])
    unresolved: list[str] = field(default_factory=list[str])

    def build(self, capability_id: str) -> Workflow:
        kept = [step for step in self.process.steps if self._kept(step)]
        kept_ids = {step.id for step in kept}
        nodes = [self._node(step) for step in kept]
        for process in self.processes.values():
            for step in process.all_steps:
                # Local processes, end events and exception handlers call other iFlows too.
                if step.id not in kept_ids:
                    self._resolve(self.iflow.receivers_of(step.id))
        edges = self._edges(kept_ids)
        sources: defaultdict[str, set[str]] = defaultdict(set)
        for edge in edges:
            sources[edge.target].add(edge.source)
        parallel = {s.id for s in kept if s.kind == "parallelGateway"}
        nodes = [
            node.model_copy(update={"join": "any"})
            if len(sources[node.id]) > 1 and node.id not in parallel
            else node
            for node in nodes
        ]
        return Workflow(
            id=capability_id,
            capability=capability_id,
            nodes=tuple(nodes),
            edges=tuple(edges),
            calls=tuple(dict.fromkeys(self.calls)),
            unresolved_calls=tuple(dict.fromkeys(self.unresolved)),
        )

    def _kept(self, step: Step) -> bool:
        if step.kind in {"exclusiveGateway", "parallelGateway"}:
            return True
        return step.activity_type in _KEPT_ACTIVITIES or step_effects(step) is not None

    def _node(self, step: Step) -> Node:
        if step.kind in {"exclusiveGateway", "parallelGateway"}:
            return Node(id=step.id, kind="decision", label=step.name)
        if step.activity_type == "ProcessCallElement":
            local = self.processes.get(step.properties.get("processId", ""))
            label = f"{step.name}: local process {local.name if local else '?'}"
            return Node(id=step.id, kind="container", label=label)
        receivers = self.iflow.receivers_of(step.id)
        capability = self._resolve(receivers)
        detail = ", ".join(_describe(channel) for channel in receivers)
        label = f"{step.name} ({detail})" if detail else step.name
        kind = "invoke" if capability else "activity"
        return Node(id=step.id, kind=kind, label=label, capability=capability)

    def _resolve(self, receivers: list[Channel]) -> str | None:
        """Record ProcessDirect calls to other iFlows; the capability called, if any."""
        called = None
        for channel in receivers:
            if channel.component.upper() != "PROCESSDIRECT":
                continue
            target = self.endpoints.get(channel.address)
            if target:
                self.calls.append(target)
                called = target
            else:
                self.unresolved.append(channel.address)
        return called

    def _edges(self, kept: set[str]) -> list[Edge]:
        outgoing: defaultdict[str, list[tuple[str, str | None]]] = defaultdict(list)
        for flow in self.process.flows:
            source = self.process.step(flow.source)
            condition = flow.condition
            if source is not None and source.default_flow == flow.id:
                condition = "otherwise"
            outgoing[flow.source].append((flow.target, condition))
        edges: list[Edge] = []
        for start in kept:
            seen: set[str] = set()
            pending = [(target, condition) for target, condition in outgoing[start]]
            while pending:
                target, condition = pending.pop()
                if target in kept:
                    edges.append(Edge(source=start, target=target, condition=condition))
                elif target not in seen:
                    seen.add(target)
                    pending.extend((nxt, condition or cond) for nxt, cond in outgoing[target])
        return sorted(set(edges), key=lambda e: (e.source, e.target, e.condition or ""))


def _describe(channel: Channel) -> str:
    method = channel.properties.get("httpMethod", "")
    parts = [channel.component, method, channel.address]
    return " ".join(part for part in parts if part)


def _propagate_effects(entries: list[_Entry], workflows: list[Workflow]) -> None:
    """Give each iFlow the effects of the iFlows it calls through ProcessDirect."""
    by_id = {c.id: c for entry in entries for c in entry.capabilities}
    graph = {w.capability: w.calls for w in workflows}
    changed = True
    while changed:
        changed = False
        for entry in entries:
            calls = graph.get(entry.capabilities[0].id, ())
            callees = [by_id[callee].effects for callee in calls if callee in by_id]
            for index, capability in enumerate(entry.capabilities):
                combined = Effects.combine([capability.effects, *callees])
                if combined == capability.effects:
                    continue
                updated = capability.model_copy(
                    update={"effects": combined, "idempotency": _recheck(capability, combined)}
                )
                entry.capabilities[index] = updated
                by_id[updated.id] = updated
                changed = True


def _recheck(capability: Capability, effects: Effects) -> Idempotency:
    idempotency = capability.idempotency
    inferred_safe = idempotency.provenance == "inferred" and idempotency.mode == "natural"
    if inferred_safe and effects.has_side_effects:
        return Idempotency(mode="none", confidence=0.7)
    return idempotency


def _expand(workflows: list[Workflow], entries: list[_Entry]) -> list[Workflow]:
    """One workflow per capability: iFlows with several endpoints share their graph."""
    expanded: list[Workflow] = []
    by_first = {w.capability: w for w in workflows}
    for entry in entries:
        graph = by_first.get(entry.capabilities[0].id) if entry.capabilities else None
        if graph is None:
            continue
        expanded.extend(
            graph.model_copy(update={"id": c.id, "capability": c.id}) for c in entry.capabilities
        )
    return expanded


def _slug(text: str) -> str:
    return _UNSAFE.sub("_", text).strip("_") or "endpoint"


__all__ = ["SapCpiAdapter"]
