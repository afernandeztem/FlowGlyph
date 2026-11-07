"""What each kind of BPMN step does to the world, and what makes a process fragile."""

from typing import Literal

from flowglyph.adapters.bpmn.model import GATEWAYS, Process, Step
from flowglyph.ir import Effects, Tri

type Finding = tuple[Literal["info", "warning", "error"], str]

_UNKNOWN_EXTERNAL = Effects(
    reads=Tri.UNKNOWN, mutates_state=Tri.UNKNOWN, destructive=Tri.UNKNOWN, external=Tri.YES
)
_UNKNOWN = Effects(
    reads=Tri.UNKNOWN, mutates_state=Tri.UNKNOWN, destructive=Tri.UNKNOWN, external=Tri.UNKNOWN
)
_SEND = Effects(reads=Tri.NO, mutates_state=Tri.YES, destructive=Tri.NO, external=Tri.YES)
_RECEIVE = Effects(reads=Tri.YES, mutates_state=Tri.NO, destructive=Tri.NO, external=Tri.YES)
_PERSON = Effects(reads=Tri.NO, mutates_state=Tri.NO, destructive=Tri.NO, external=Tri.YES)
_DECISION = Effects(reads=Tri.YES, mutates_state=Tri.NO, destructive=Tri.NO, external=Tri.NO)
INSTANCE = Effects(reads=Tri.NO, mutates_state=Tri.YES, destructive=Tri.NO, external=Tri.YES)
"""Starting a process creates an instance in the engine, whatever its steps do."""

_EFFECTS = {
    "serviceTask": _UNKNOWN_EXTERNAL,
    "sendTask": _SEND,
    "receiveTask": _RECEIVE,
    "userTask": _PERSON,
    "manualTask": _PERSON,
    "scriptTask": _UNKNOWN,
    "businessRuleTask": _DECISION,
    "task": _UNKNOWN,
}


def step_effects(step: Step) -> Effects | None:
    """Effects of a step on its own; None for steps that only route or wait."""
    if step.kind in _EFFECTS:
        return _EFFECTS[step.kind]
    if step.kind == "intermediateThrowEvent" and step.event in {"message", "signal", "escalation"}:
        return _SEND
    return None


def design_findings(process: Process) -> list[Finding]:
    """Problems that make a process fail at runtime or behave in ways nobody chose."""
    findings: list[Finding] = []
    outgoing: dict[str, int] = {}
    conditional: dict[str, int] = {}
    for flow in process.flows:
        outgoing[flow.source] = outgoing.get(flow.source, 0) + 1
        if flow.condition:
            conditional[flow.source] = conditional.get(flow.source, 0) + 1
    for step in process.all_steps():
        if step.kind == "serviceTask" and step.implementation is None:
            findings.append(
                (
                    "warning",
                    (
                        f"service task {step.name!r} has no implementation (class, expression, "
                        "external topic or job type), so the engine cannot run it"
                    ),
                )
            )
        branches = outgoing.get(step.id, 0)
        exclusive = step.kind in GATEWAYS - {"parallelGateway", "eventBasedGateway"}
        if exclusive and branches > 1 and not step.default_flow and conditional.get(step.id):
            findings.append(
                (
                    "warning",
                    (
                        f"gateway {step.name!r} has no default flow: when no condition holds, "
                        "the process stops with an incident"
                    ),
                )
            )
    if not process.executable:
        findings.append(("info", f"process {process.id} is not marked executable"))
    return findings
