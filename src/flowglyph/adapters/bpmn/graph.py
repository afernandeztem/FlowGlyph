"""The workflow graph of a BPMN process: its tasks and gateways, and the flows between them.

Events only route, so they are folded away; their flows are followed through and keep their
conditions. A boundary event becomes an edge from the task it is attached to, labelled with
what triggers it.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from flowglyph._internal.graph import follow, with_joins
from flowglyph.adapters.bpmn.model import GATEWAYS, TASKS, Process, Step
from flowglyph.ir import OTHERWISE, Edge, Node, Workflow


@dataclass
class GraphBuilder:
    """Builds the graph of one process, resolving call activities through `processes`."""

    process: Process
    processes: dict[str, str]
    calls: list[str] = field(default_factory=list[str])
    unresolved: list[str] = field(default_factory=list[str])

    def build(self, capability_id: str) -> Workflow:
        """The graph, with call activities resolved to the capabilities they start."""
        kept = [step for step in self.process.steps if step.kind in TASKS or step.kind in GATEWAYS]
        kept_ids = {step.id for step in kept}
        nodes = [self._node(step) for step in kept]
        for step in self.process.all_steps():
            if step.called and step.id not in kept_ids:
                self._resolve(step.called)
        edges = self._edges(kept_ids)
        parallel = {step.id for step in kept if step.kind == "parallelGateway"}
        return Workflow(
            id=capability_id,
            capability=capability_id,
            nodes=tuple(with_joins(nodes, edges, parallel)),
            edges=tuple(edges),
            calls=tuple(dict.fromkeys(self.calls)),
            unresolved_calls=tuple(dict.fromkeys(self.unresolved)),
        )

    def _node(self, step: Step) -> Node:
        if step.kind in GATEWAYS:
            return Node(id=step.id, kind="decision", label=step.name)
        if step.kind in {"subProcess", "transaction"}:
            inner = [child.name for child in step.children if child.kind in TASKS]
            label = f"{step.name}: {', '.join(inner)}" if inner else step.name
            return Node(id=step.id, kind="container", label=label)
        if step.called:
            capability = self._resolve(step.called)
            return Node(
                id=step.id,
                kind="invoke" if capability else "activity",
                label=f"{step.name} (calls {step.called})",
                capability=capability,
            )
        label = f"{step.name} ({step.implementation})" if step.implementation else step.name
        return Node(id=step.id, kind="activity", label=label)

    def _resolve(self, process_id: str) -> str | None:
        target = self.processes.get(process_id)
        if target:
            self.calls.append(target)
        else:
            self.unresolved.append(process_id)
        return target

    def _edges(self, kept: set[str]) -> list[Edge]:
        steps = {step.id: step for step in self.process.steps}
        outgoing: defaultdict[str, list[tuple[str, str | None]]] = defaultdict(list)
        for flow in self.process.flows:
            source = steps.get(flow.source)
            condition = flow.condition
            if source is not None and source.default_flow == flow.id:
                condition = OTHERWISE
            elif condition is None and flow.name and source is not None and source.kind in GATEWAYS:
                condition = flow.name
            outgoing[flow.source].append((flow.target, condition))
        for step in self.process.steps:
            if step.kind == "boundaryEvent" and step.attached_to:
                trigger = f"on {step.event or 'event'}: {step.name}"
                outgoing[step.attached_to].append((step.id, trigger))
        return follow(outgoing, kept)
