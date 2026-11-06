"""Adapter for SAP Cloud Integration (SAP Integration Suite) integration flows.

Reads iFlows exported as `.zip` artifacts or unpacked into folders. Every endpoint an iFlow
exposes becomes a capability; its receivers and steps decide the effects; ProcessDirect links
between iFlows become calls in the workflow graph; and design problems that make an iFlow fragile
are reported, so `flowglyph wiki lint` can point at them.
"""

from collections.abc import Iterable
from pathlib import Path
from typing import ClassVar

from flowglyph._internal.hashing import digest
from flowglyph._internal.xml import parse_xml
from flowglyph.adapters import Diagnostic, Extraction
from flowglyph.adapters.sap_cpi.bundle import read_directory, read_zip
from flowglyph.adapters.sap_cpi.discovery import find_artifacts
from flowglyph.adapters.sap_cpi.graph import build_workflow
from flowglyph.adapters.sap_cpi.iflow import Channel, IFlow, parse_iflow
from flowglyph.adapters.sap_cpi.linking import (
    Entry,
    assign_keys,
    expand_workflows,
    process_direct_endpoints,
    propagate_effects,
    slug,
)
from flowglyph.adapters.sap_cpi.rules import (
    channel_effects,
    declared_idempotency,
    design_findings,
    step_effects,
)
from flowglyph.errors import AdapterError
from flowglyph.ir import Capability, Effects, Idempotency, JsonSchema, Security, Source, Trigger

_INVOCABLE_SENDERS = frozenset(
    {"HTTPS", "HTTP", "SOAP", "PROCESSDIRECT", "ODATA", "HCIODATA", "IDOC", "REST", "AS2", "AS4"}
)


class SapCpiAdapter:
    """Turns SAP Cloud Integration iFlows into capabilities, one per endpoint they expose.

    Receivers and steps decide the effects. Idempotency is taken from what the iFlow itself
    declares (an idempotent process call, an exactly-once adapter) before anything is inferred.
    """

    name: ClassVar[str] = "sap-cpi"
    version: ClassVar[str] = "0.1.0"

    def detect(self, path: Path) -> bool:
        """Whether `path` is an iFlow artifact or a folder containing one."""
        return bool(find_artifacts(path))

    def discover(self, root: Path) -> list[Path]:
        """`root` itself when it holds iFlows: they are read together to resolve their links."""
        return [root] if find_artifacts(root) else []

    def extract(self, path: Path) -> Extraction:
        """Extract every iFlow at `path`."""
        root = path if path.is_dir() else path.parent
        entries: list[Entry] = []
        artifacts: dict[str, str] = {}
        diagnostics: list[Diagnostic] = []
        for artifact_path in find_artifacts(path):
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
                entries.append(Entry(bundle, artifact, artifacts[artifact], parse_iflow(document)))
        assign_keys(entries)
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
        endpoints = process_direct_endpoints(entries)
        workflows = [
            build_workflow(entry.iflow, entry.capabilities[0].id, endpoints)
            for entry in entries
            if entry.capabilities
        ]
        propagate_effects(entries, workflows)
        return Extraction(
            capabilities=[c for entry in entries for c in entry.capabilities],
            workflows=expand_workflows(workflows, entries),
            artifacts=artifacts,
            diagnostics=diagnostics,
        )

    def _capabilities(self, entry: Entry) -> list[Capability]:
        iflow = entry.iflow
        senders = iflow.senders or [None]
        timer = iflow.main is not None and any(s.event == "timer" for s in iflow.main.steps)
        found: list[Capability] = []
        for sender in senders:
            suffix = (
                f"/{slug(sender.component + '_' + sender.address)}"
                if len(senders) > 1 and sender
                else ""
            )
            found.append(
                self._capability(entry, sender, f"sap-cpi/{entry.key}{suffix}", timer=timer)
            )
        return found

    def _capability(
        self, entry: Entry, sender: Channel | None, capability_id: str, *, timer: bool
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


__all__ = ["SapCpiAdapter"]
