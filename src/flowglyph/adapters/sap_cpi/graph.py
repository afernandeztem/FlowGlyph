"""The workflow graph of an iFlow: the steps that matter and the flows between them.

Steps without effects are folded away; their flows are followed through so the edges between the
steps that remain keep their conditions.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from flowglyph.adapters.sap_cpi.iflow import Channel, IFlow, Process, Step
from flowglyph.adapters.sap_cpi.rules import step_effects
from flowglyph.ir import Edge, Node, Workflow

_KEPT_ACTIVITIES = frozenset({"ExternalCall", "ProcessCallElement", "DBstorage", "Script"})


def build_workflow(iflow: IFlow, capability_id: str, endpoints: dict[str, str]) -> Workflow:
    """The graph of `iflow`'s main process, resolving ProcessDirect calls through `endpoints`."""
    process = iflow.main
    if process is None:
        return Workflow(id=capability_id, capability=capability_id)
    return GraphBuilder(iflow, process, endpoints, iflow.processes).build(capability_id)


@dataclass
class GraphBuilder:
    """Builds the workflow graph of one process, recording ProcessDirect calls on the way."""

    iflow: IFlow
    process: Process
    endpoints: dict[str, str]
    processes: dict[str, Process]
    calls: list[str] = field(default_factory=list[str])
    unresolved: list[str] = field(default_factory=list[str])

    def build(self, capability_id: str) -> Workflow:
        """The graph of the process: steps with effects, decisions, and the flows between them."""
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
