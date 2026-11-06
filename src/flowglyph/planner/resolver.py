"""Checking a proposed plan against the catalog: the deterministic half of planning."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from flowglyph._internal.hashing import fingerprint
from flowglyph.catalog import Catalog
from flowglyph.ir import (
    Capability,
    Edge,
    Effects,
    Idempotency,
    JsonSchema,
    Node,
    Source,
    Workflow,
)
from flowglyph.planner.model import Plan, PlannedStep

_SLUG = re.compile(r"[^a-z0-9]+")


@dataclass
class PlanReport:
    """A plan checked against the catalog and turned into IR.

    `problems` are errors that make the workflow invalid as written. `unresolved` lists the
    steps no catalog capability could serve; they appear as opaque nodes so a person can see
    what is missing, never as invented capabilities.
    """

    plan: Plan
    workflow: Workflow
    capability: Capability
    problems: list[str] = field(default_factory=list[str])
    unresolved: list[str] = field(default_factory=list[str])
    warnings: list[str] = field(default_factory=list[str])

    @property
    def ok(self) -> bool:
        """Whether every step resolved and no problem was found."""
        return not self.problems and not self.unresolved

    def save(self, directory: str | Path) -> tuple[Path, Path]:
        """Write `workflow.plan.yaml` (the proposal) and `workflow.ir.yaml` (the result)."""
        target = Path(directory)
        target.mkdir(parents=True, exist_ok=True)
        proposal = target / "workflow.plan.yaml"
        result = target / "workflow.ir.yaml"
        proposal.write_text(
            _yaml(self.plan.model_dump(mode="json")), encoding="utf-8", newline="\n"
        )
        document = {
            "status": "ok" if self.ok else "needs attention",
            "problems": self.problems,
            "unresolved": self.unresolved,
            "warnings": self.warnings,
            "capability": self.capability.model_dump(mode="json"),
            "workflow": self.workflow.model_dump(mode="json"),
        }
        result.write_text(_yaml(document), encoding="utf-8", newline="\n")
        return proposal, result


def resolve(plan: Plan, catalog: Catalog) -> PlanReport:
    """Check `plan` against `catalog` and build the workflow IR it describes."""
    workflow_id = "plan/" + (_SLUG.sub("-", plan.goal.lower()).strip("-") or "workflow")
    report = _Resolution(plan, catalog)
    report.check()
    nodes = tuple(report.node(step) for step in plan.steps)
    workflow = Workflow(
        id=workflow_id,
        capability=workflow_id,
        nodes=nodes,
        edges=tuple(report.edges()),
        calls=tuple(dict.fromkeys(n.capability for n in nodes if n.capability)),
        unresolved_calls=tuple(step.intent for step in plan.steps if step.id in report.unresolved),
    )
    used = [catalog.capabilities[c] for c in workflow.calls]
    effects = Effects.combine([capability.effects for capability in used])
    capability = Capability(
        id=workflow_id,
        kind="workflow",
        title=plan.goal,
        description="\n".join(step.intent for step in plan.steps),
        category="workflow",
        input_schema=_input_schema(plan),
        effects=effects,
        idempotency=Idempotency(mode="natural" if not effects.has_side_effects else "none"),
        notes=tuple(plan.assumptions),
        source=Source(
            provider="planner",
            artifact=plan.goal,
            location="workflow.plan.yaml",
            source_hash=fingerprint(plan.model_dump(mode="json")),
        ),
    )
    return PlanReport(
        plan=plan,
        workflow=workflow,
        capability=capability,
        problems=report.problems,
        unresolved=report.unresolved,
        warnings=report.warnings,
    )


class _Resolution:
    def __init__(self, plan: Plan, catalog: Catalog) -> None:
        self.plan = plan
        self.catalog = catalog
        self.problems: list[str] = []
        self.unresolved: list[str] = []
        self.warnings: list[str] = []
        self.inputs = {planned.name for planned in plan.inputs}
        self.order = [step.id for step in plan.steps]

    def check(self) -> None:
        if len(set(self.order)) != len(self.order):
            self.problems.append("step ids must be unique")
        may_skip: dict[str, bool] = {}
        for position, step in enumerate(self.plan.steps):
            capability = self._capability(step)
            dependencies = self._dependencies(step, position)
            for dependency in dependencies:
                if dependency not in self.order[:position]:
                    self.problems.append(
                        f"{step.id} runs after {dependency}, which is not an earlier step"
                    )
            if capability is not None:
                self._check_arguments(step, capability, position)
            skippable = [may_skip.get(dependency, False) for dependency in dependencies]
            if step.join == "all" and any(skippable) and not all(skippable):
                optional = [d for d, skip in zip(dependencies, skippable, strict=True) if skip]
                self.warnings.append(
                    f"{step.id} is skipped whenever {', '.join(optional)} is skipped; "
                    "set join to any if it should run either way"
                )
            may_skip[step.id] = step.condition is not None or _inherits_skip(step.join, skippable)

    def _capability(self, step: PlannedStep) -> Capability | None:
        if step.capability is None:
            self.unresolved.append(step.id)
            return None
        capability = self.catalog.capabilities.get(step.capability)
        if capability is None:
            self.problems.append(f"{step.id} uses {step.capability}, which is not in the catalog")
            self.unresolved.append(step.id)
            return None
        if not capability.invocable:
            self.problems.append(f"{step.id} uses {capability.id}, which cannot be run on its own")
        return capability

    def _check_arguments(self, step: PlannedStep, capability: Capability, position: int) -> None:
        accepted = {parameter.name: parameter for parameter in capability.inputs}
        given = {argument.name for argument in step.arguments}
        for argument in step.arguments:
            if argument.name not in accepted:
                self.problems.append(f"{step.id}: {capability.id} has no input {argument.name}")
            elif argument.source == "workflow_input" and argument.value not in self.inputs:
                self.problems.append(f"{step.id}.{argument.name}: unknown input {argument.value}")
            elif argument.source == "step_output":
                self._check_reference(step, argument.name, argument.value, position)
            elif argument.source == "literal":
                self._check_literal(step, argument.name, argument.value)
        missing = sorted(name for name, p in accepted.items() if p.required and name not in given)
        if missing:
            self.problems.append(f"{step.id}: missing required inputs {', '.join(missing)}")
        key_fields = capability.idempotency.key_fields
        if capability.effects.has_side_effects and not set(key_fields) & given:
            self.warnings.append(
                f"{step.id} has side effects: run it with an idempotency key so retries are safe"
            )

    def _check_reference(self, step: PlannedStep, name: str, reference: str, position: int) -> None:
        source_step, _, output = reference.partition(".")
        if source_step not in self.order[:position]:
            self.problems.append(f"{step.id}.{name}: {source_step} is not an earlier step")
            return
        producer = self.plan.steps[self.order.index(source_step)]
        capability = self.catalog.capabilities.get(producer.capability or "")
        if capability is not None and output not in {p.name for p in capability.outputs}:
            self.problems.append(f"{step.id}.{name}: {capability.id} has no output {output}")

    def _check_literal(self, step: PlannedStep, name: str, value: str) -> None:
        try:
            json.loads(value)
        except json.JSONDecodeError:
            self.problems.append(f"{step.id}.{name}: literal {value!r} is not valid JSON")

    def _dependencies(self, step: PlannedStep, position: int) -> list[str]:
        if step.after or position == 0:
            return list(step.after)
        return [self.order[position - 1]]

    def node(self, step: PlannedStep) -> Node:
        resolved = step.id not in self.unresolved
        return Node(
            id=step.id,
            kind="invoke" if resolved else "opaque",
            label=step.intent,
            capability=step.capability if resolved else None,
            note=None if resolved else "no capability in the catalog does this yet",
            join=step.join,
        )

    def edges(self) -> list[Edge]:
        edges: list[Edge] = []
        for position, step in enumerate(self.plan.steps):
            for dependency in self._dependencies(step, position):
                if dependency in self.order[:position]:
                    edges.append(Edge(source=dependency, target=step.id, condition=step.condition))
        return edges


def _inherits_skip(join: str, skippable: list[bool]) -> bool:
    if join == "all":
        return any(skippable)
    return bool(skippable) and all(skippable)


def _input_schema(plan: Plan) -> JsonSchema:
    return {
        "type": "object",
        "properties": {
            planned.name: {"type": planned.type, "description": planned.description}
            for planned in plan.inputs
        },
        "required": [planned.name for planned in plan.inputs],
        "additionalProperties": False,
    }


def _yaml(document: object) -> str:
    return yaml.safe_dump(document, sort_keys=False, allow_unicode=True, width=100)
