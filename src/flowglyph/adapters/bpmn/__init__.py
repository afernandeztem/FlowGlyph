"""Adapter for BPMN 2.0 process models, with Camunda 7 and Camunda 8 (Zeebe) extensions.

Every process becomes a workflow capability. Its tasks decide the effects, call activities link
processes across files, and design problems such as a gateway without a default flow are
reported. Starting a process always creates an instance, so no process is naturally idempotent.
"""

import re
from pathlib import Path
from typing import ClassVar

from flowglyph._internal.hashing import digest
from flowglyph._internal.paths import distinguishing_names
from flowglyph._internal.xml import parse_xml
from flowglyph.adapters import Diagnostic, Extraction
from flowglyph.adapters.bpmn.graph import GraphBuilder
from flowglyph.adapters.bpmn.model import Document, FormField, Process, is_bpmn, parse_document
from flowglyph.adapters.bpmn.rules import INSTANCE, Finding, design_findings, step_effects
from flowglyph.errors import AdapterError
from flowglyph.ir import (
    Capability,
    Effects,
    Idempotency,
    JsonSchema,
    Source,
    Trigger,
    Workflow,
)

_SUFFIXES = (".bpmn", ".bpmn2", ".bpmn20.xml")
_UNSAFE = re.compile(r"[^\w.-]+")
_FORM_TYPES = {"long": "integer", "boolean": "boolean", "date": "string", "enum": "string"}
_INSTANCE_NOTE = (
    "each start creates a new process instance; declare a business key in the overrides if "
    "the engine rejects duplicates"
)


class BpmnAdapter:
    """Turns BPMN 2.0 processes into capabilities, with Camunda 7 and Camunda 8 extensions.

    Processes read together resolve their call activities, and effects travel along them.
    """

    name: ClassVar[str] = "bpmn"
    version: ClassVar[str] = "0.1.0"

    def detect(self, path: Path) -> bool:
        """Whether `path` is a BPMN file or a folder holding one."""
        return bool(_files(path))

    def discover(self, root: Path) -> list[Path]:
        """`root` itself when it holds BPMN files: they are read together to resolve calls."""
        return [root] if _files(root) else []

    def extract(self, path: Path) -> Extraction:
        """Extract every process at `path`."""
        root = path if path.is_dir() else path.parent
        artifacts: dict[str, str] = {}
        diagnostics: list[Diagnostic] = []
        documents: list[tuple[str, Document]] = []
        for file in _files(path):
            artifact = file.relative_to(root).as_posix()
            data = file.read_bytes()
            try:
                element = parse_xml(data, artifact)
            except AdapterError as error:
                diagnostics.append(Diagnostic("error", artifact, str(error)))
                continue
            if not is_bpmn(element):
                continue
            artifacts[artifact] = digest(data)
            documents.append((artifact, parse_document(element)))
        entries = [
            (artifact, document, process)
            for artifact, document in documents
            for process in document.processes
        ]
        ids = _capability_ids([(artifact, process) for artifact, _, process in entries])
        by_process = {process.id: ids[artifact, process.id] for artifact, _, process in entries}
        capabilities: dict[str, Capability] = {}
        workflows: list[Workflow] = []
        for artifact, document, process in entries:
            capability_id = ids[artifact, process.id]
            findings = design_findings(process)
            diagnostics.extend(Diagnostic(level, artifact, message) for level, message in findings)
            workflow = GraphBuilder(process, by_process).build(capability_id)
            workflows.append(workflow)
            diagnostics.extend(
                Diagnostic(
                    "warning", artifact, f"calls process {called}, which is not in the sources"
                )
                for called in workflow.unresolved_calls
            )
            capabilities[capability_id] = self._capability(
                process,
                document=document,
                artifact=artifact,
                source_hash=artifacts[artifact],
                capability_id=capability_id,
                findings=findings,
            )
        _propagate(capabilities, workflows)
        return Extraction(
            capabilities=list(capabilities.values()),
            workflows=workflows,
            artifacts=artifacts,
            diagnostics=diagnostics,
        )

    def _capability(
        self,
        process: Process,
        *,
        document: Document,
        artifact: str,
        source_hash: str,
        capability_id: str,
        findings: list[Finding],
    ) -> Capability:
        steps = [effect for step in process.all_steps() if (effect := step_effects(step))]
        trigger, invocable = _trigger(process, document)
        return Capability(
            id=capability_id,
            kind="workflow",
            title=process.name,
            description=process.documentation or f"BPMN process {process.name}.",
            category=document.engine,
            input_schema=_inputs(process.form),
            effects=Effects.combine([INSTANCE, *steps]),
            idempotency=Idempotency(mode="none", confidence=0.8),
            trigger=trigger,
            notes=(_INSTANCE_NOTE, *(f"{level}: {message}" for level, message in findings)),
            source=Source(
                provider=self.name,
                artifact=process.id,
                location=f"{artifact}#{process.id}",
                source_hash=source_hash,
            ),
            invocable=invocable,
        )


def _files(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.name.lower().endswith(_SUFFIXES) else []
    if not path.is_dir():
        return []
    return sorted(
        file
        for file in path.rglob("*")
        if file.is_file() and file.name.lower().endswith(_SUFFIXES) and ".git" not in file.parts
    )


def _capability_ids(entries: list[tuple[str, Process]]) -> dict[tuple[str, str], str]:
    """`bpmn/<process id>`, qualified by file where two files define the same process id."""
    by_id: dict[str, list[str]] = {}
    for artifact, process in entries:
        by_id.setdefault(process.id, []).append(artifact)
    ids: dict[tuple[str, str], str] = {}
    for process_id, artifacts in by_id.items():
        base = f"bpmn/{_UNSAFE.sub('_', process_id)}"
        if len(artifacts) == 1:
            ids[artifacts[0], process_id] = base
            continue
        for artifact, suffix in zip(artifacts, distinguishing_names(artifacts), strict=True):
            ids[artifact, process_id] = f"{base}.{_UNSAFE.sub('_', suffix)}"
    return ids


def _trigger(process: Process, document: Document) -> tuple[Trigger, bool]:
    start = process.start
    if start is None or start.event is None:
        return Trigger(kind="call", channel=document.engine, address=process.id), True
    if start.event == "message":
        message = process.messages.get(start.detail or "", start.detail or "")
        return Trigger(kind="event", channel="message", address=message or None), True
    if start.event == "timer":
        return Trigger(kind="schedule", channel="timer", address=start.detail), False
    return Trigger(kind="event", channel=start.event, address=start.detail), False


def _inputs(form: list[FormField]) -> JsonSchema:
    if not form:
        return {
            "type": "object",
            "properties": {},
            "additionalProperties": True,
            "description": "process variables",
        }
    properties: dict[str, JsonSchema] = {}
    for field in form:
        schema: JsonSchema = {"type": _FORM_TYPES.get(field.type, "string")}
        if field.type == "date":
            schema["format"] = "date"
        if field.label:
            schema["description"] = field.label
        if field.default is not None:
            schema["x-default-expression"] = field.default
        properties[field.name] = schema
    required = [field.name for field in form if field.default is None]
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _propagate(capabilities: dict[str, Capability], workflows: list[Workflow]) -> None:
    """Give each process the effects of the processes it calls, until nothing changes."""
    graph = {workflow.capability: workflow.calls for workflow in workflows}
    changed = True
    while changed:
        changed = False
        for capability_id, calls in graph.items():
            capability = capabilities[capability_id]
            callees = [capabilities[call].effects for call in calls if call in capabilities]
            combined = Effects.combine([capability.effects, *callees])
            if combined != capability.effects:
                capabilities[capability_id] = capability.model_copy(update={"effects": combined})
                changed = True


__all__ = ["BpmnAdapter"]
