from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

from flowglyph.adapters.uipath.taxonomy import Category
from flowglyph.adapters.uipath.xaml import (
    annotation,
    child_activities,
    display_name,
    split_tag,
    view_state_id,
)
from flowglyph.ir import Edge, Node, NodeKind, Workflow

OPAQUE_CONTAINERS = frozenset({"StateMachine", "Flowchart", "Parallel", "ParallelForEach", "Pick"})
INVOKE_ACTIVITY = "InvokeWorkflowFile"

type Classifier = Callable[[ET.Element], tuple[str, Category]]
type InvokeResolver = Callable[[str], str | None]


@dataclass(frozen=True)
class _Segment:
    entries: tuple[str, ...] = ()
    exits: tuple[str, ...] = ()

    @property
    def empty(self) -> bool:
        return not self.entries


@dataclass
class GraphBuilder:
    """Builds the IR graph of one workflow from its activity tree.

    Pure activities (assignments, logging, control without branching) are folded away so the
    graph only shows what an agent needs to reason about: invocations, decisions and steps
    that touch other systems. State machines, flowcharts and parallel blocks are kept as one
    opaque node followed by their flattened children.
    """

    classify: Classifier
    resolve_invoke: InvokeResolver
    nodes: list[Node] = field(default_factory=list[Node])
    edges: list[Edge] = field(default_factory=list[Edge])
    calls: list[str] = field(default_factory=list[str])
    unresolved_calls: list[str] = field(default_factory=list[str])
    _ids: set[str] = field(default_factory=set[str])

    def build(self, workflow_id: str, capability_id: str, root: ET.Element | None) -> Workflow:
        """Walk `root` and return the resulting workflow graph."""
        if root is not None:
            self._segment(root)
        return Workflow(
            id=workflow_id,
            capability=capability_id,
            nodes=tuple(self.nodes),
            edges=tuple(self.edges),
            calls=tuple(dict.fromkeys(self.calls)),
            unresolved_calls=tuple(dict.fromkeys(self.unresolved_calls)),
        )

    def _segment(self, element: ET.Element) -> _Segment:
        local = split_tag(element.tag)[1]
        if local == "If":
            return self._decision(element)
        if local == INVOKE_ACTIVITY:
            return self._invoke(element)
        children = list(child_activities(element))
        if local in OPAQUE_CONTAINERS:
            head = self._add(element, "opaque")
            return self._chain([_Segment((head,), (head,)), *map(self._segment, children)])
        return self._activity(element, children)

    def _activity(self, element: ET.Element, children: list[ET.Element]) -> _Segment:
        capability, category = self.classify(element)
        touches_world = category.effects.has_side_effects or category.effects.external.possible
        if children:
            body = self._chain(map(self._segment, children))
            if not touches_world:
                return body
            head = self._add(element, "container", capability)
            return self._chain([_Segment((head,), (head,)), body])
        if not touches_world:
            return _Segment()
        node = self._add(element, "activity", capability)
        return _Segment((node,), (node,))

    def _decision(self, element: ET.Element) -> _Segment:
        condition = _condition_text(element)
        head = self._add(element, "decision", label=f"If {condition}")
        exits: list[str] = []
        for branch, guard in (("Then", condition), ("Else", f"not ({condition})")):
            branch_elements = [
                child for child in element if split_tag(child.tag)[1] == f"If.{branch}"
            ]
            body = self._chain(
                self._segment(activity)
                for branch_element in branch_elements
                for activity in child_activities(branch_element)
            )
            if body.empty:
                exits.append(head)
                continue
            self._connect((head,), body.entries, guard)
            exits.extend(body.exits)
        return _Segment((head,), tuple(dict.fromkeys(exits)))

    def _invoke(self, element: ET.Element) -> _Segment:
        target = (element.get("WorkflowFileName") or "").replace("\\", "/")
        capability = self.resolve_invoke(target) if target else None
        if capability:
            self.calls.append(capability)
        elif target:
            self.unresolved_calls.append(target)
        node = self._add(element, "invoke", capability)
        return _Segment((node,), (node,))

    def _chain(self, segments: Iterable[_Segment]) -> _Segment:
        entries: tuple[str, ...] = ()
        exits: tuple[str, ...] = ()
        for segment in segments:
            if segment.empty:
                continue
            if entries:
                self._connect(exits, segment.entries)
            else:
                entries = segment.entries
            exits = segment.exits
        return _Segment(entries, exits)

    def _connect(
        self, sources: Iterable[str], targets: Iterable[str], condition: str | None = None
    ) -> None:
        for source in sources:
            for target in targets:
                self.edges.append(Edge(source=source, target=target, condition=condition))

    def _add(
        self,
        element: ET.Element,
        kind: NodeKind,
        capability: str | None = None,
        label: str | None = None,
    ) -> str:
        node_id = self._unique_id(view_state_id(element) or f"node_{len(self.nodes) + 1}")
        self.nodes.append(
            Node(
                id=node_id,
                kind=kind,
                label=label or display_name(element),
                capability=capability,
                note=annotation(element),
            )
        )
        return node_id

    def _unique_id(self, candidate: str) -> str:
        node_id = candidate
        suffix = 2
        while node_id in self._ids:
            node_id = f"{candidate}_{suffix}"
            suffix += 1
        self._ids.add(node_id)
        return node_id


def _condition_text(element: ET.Element) -> str:
    raw = element.get("Condition")
    if raw is None:
        condition_elements = [
            child for child in element if split_tag(child.tag)[1] == "If.Condition"
        ]
        raw = "".join(condition_elements[0].itertext()) if condition_elements else "condition"
    return raw.strip().removeprefix("[").removesuffix("]").strip() or "condition"
