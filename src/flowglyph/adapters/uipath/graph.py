"""The workflow graph of a XAML workflow: invocations, steps with effects and decisions."""

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

from flowglyph._internal.graph import with_joins
from flowglyph.adapters.uipath.taxonomy import Category
from flowglyph.adapters.uipath.xaml import (
    XAML_NS,
    annotation,
    child_activities,
    display_name,
    is_activity,
    is_designer_noise,
    split_tag,
    view_state_id,
)
from flowglyph.ir import OTHERWISE, Edge, Node, NodeKind, Workflow

OPAQUE_CONTAINERS = frozenset({"StateMachine", "Flowchart", "Parallel", "ParallelForEach", "Pick"})
INVOKE_ACTIVITY = "InvokeWorkflowFile"

type Classifier = Callable[[ET.Element], tuple[str, Category]]
type InvokeResolver = Callable[[str], str | None]
type Exit = tuple[str, str | None]
type Branch = tuple[str | None, Iterable[ET.Element]]


@dataclass(frozen=True)
class _Segment:
    entries: tuple[str, ...] = ()
    exits: tuple[Exit, ...] = ()

    @property
    def empty(self) -> bool:
        return not self.entries

    @classmethod
    def node(cls, node_id: str) -> "_Segment":
        return cls((node_id,), ((node_id, None),))


@dataclass
class GraphBuilder:
    """Builds the IR graph of one workflow from its activity tree.

    Pure activities (assignments, logging, control without branching) are folded away so the
    graph only shows what an agent needs to reason about: invocations, decisions and steps
    that touch other systems. An If, a Switch and a TryCatch become decisions whose guarded
    edges lead into their branches; a branch with nothing left in it becomes a guarded edge
    to whatever follows. State machines, flowcharts and parallel blocks are kept as one
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
            nodes=tuple(with_joins(self.nodes, self.edges)),
            edges=tuple(self.edges),
            calls=tuple(dict.fromkeys(self.calls)),
            unresolved_calls=tuple(dict.fromkeys(self.unresolved_calls)),
        )

    def _segment(self, element: ET.Element) -> _Segment:
        local = split_tag(element.tag)[1]
        if local == "If":
            return self._if(element)
        if local == "Switch":
            return self._switch(element)
        if local == "TryCatch":
            return self._try_catch(element)
        if local == INVOKE_ACTIVITY:
            return self._invoke(element)
        children = list(child_activities(element))
        if local in OPAQUE_CONTAINERS:
            head = self._add(element, "opaque")
            return self._chain([_Segment.node(head), *map(self._segment, children)])
        return self._activity(element, children)

    def _activity(self, element: ET.Element, children: list[ET.Element]) -> _Segment:
        capability, category = self.classify(element)
        touches_world = category.effects.has_side_effects or category.effects.external.possible
        if children:
            body = self._chain(map(self._segment, children))
            if not touches_world:
                return body
            head = self._add(element, "container", capability)
            return self._chain([_Segment.node(head), body])
        if not touches_world:
            return _Segment()
        return _Segment.node(self._add(element, "activity", capability))

    def _if(self, element: ET.Element) -> _Segment:
        condition = _condition_text(element)
        branches: list[Branch] = [
            (condition, _property(element, "If.Then")),
            (OTHERWISE, _property(element, "If.Else")),
        ]
        return self._decision(element, f"If {condition}", branches)

    def _switch(self, element: ET.Element) -> _Segment:
        expression = _expression_text(element.get("Expression"))
        cases: list[Branch] = []
        default: list[Branch] = []
        for child in element:
            local = split_tag(child.tag)[1]
            if local == "Switch.Default":
                default.append((OTHERWISE, list(child_activities(child))))
            elif is_activity(child) and not is_designer_noise(child):
                key = child.get(f"{{{XAML_NS}}}Key", "")
                cases.append((f"{expression} = {key}", [child]))
        return self._decision(element, f"Switch {expression}", cases + default)

    def _try_catch(self, element: ET.Element) -> _Segment:
        position = len(self.nodes)
        body = self._chain(map(self._segment, _property(element, "TryCatch.Try")))
        handlers = [
            (f"on {exception}", self._chain(map(self._segment, child_activities(catch))))
            for exception, catch in _catches(element)
        ]
        handlers = [(guard, handler) for guard, handler in handlers if not handler.empty]
        cleanup = self._chain(map(self._segment, _property(element, "TryCatch.Finally")))
        if not handlers:
            return self._chain([body, cleanup])
        head = self._add(element, "decision", position=position)
        exits: list[Exit] = []
        for guard, branch in [(None, body), *handlers]:
            if branch.empty:
                exits.append((head, guard))
            else:
                self._connect([(head, guard)], branch.entries)
                exits.extend(branch.exits)
        return self._chain([_Segment((head,), tuple(dict.fromkeys(exits))), cleanup])

    def _decision(self, element: ET.Element, label: str, branches: Iterable[Branch]) -> _Segment:
        position = len(self.nodes)
        bodies = [
            (guard, self._chain(map(self._segment, activities))) for guard, activities in branches
        ]
        if all(body.empty for _, body in bodies):
            return _Segment()
        head = self._add(element, "decision", label=label, position=position)
        exits: list[Exit] = []
        for guard, body in bodies:
            if body.empty:
                exits.append((head, guard))
            else:
                self._connect([(head, guard)], body.entries)
                exits.extend(body.exits)
        return _Segment((head,), tuple(dict.fromkeys(exits)))

    def _invoke(self, element: ET.Element) -> _Segment:
        target = (element.get("WorkflowFileName") or "").replace("\\", "/")
        capability = self.resolve_invoke(target) if target else None
        if capability:
            self.calls.append(capability)
        elif target:
            self.unresolved_calls.append(target)
        return _Segment.node(self._add(element, "invoke", capability))

    def _chain(self, segments: Iterable[_Segment]) -> _Segment:
        entries: tuple[str, ...] = ()
        exits: tuple[Exit, ...] = ()
        for segment in segments:
            if segment.empty:
                continue
            if entries:
                self._connect(exits, segment.entries)
            else:
                entries = segment.entries
            exits = segment.exits
        return _Segment(entries, exits)

    def _connect(self, sources: Iterable[Exit], targets: Iterable[str]) -> None:
        for source, condition in sources:
            for target in targets:
                self.edges.append(Edge(source=source, target=target, condition=condition))

    def _add(
        self,
        element: ET.Element,
        kind: NodeKind,
        capability: str | None = None,
        label: str | None = None,
        position: int | None = None,
    ) -> str:
        # A decision is added after its branches were walked, so it is inserted where it
        # belongs: nodes stay in document order, which is what `Workflow.simulate` relies on.
        node_id = self._unique_id(view_state_id(element) or f"node_{len(self.nodes) + 1}")
        node = Node(
            id=node_id,
            kind=kind,
            label=label or display_name(element),
            capability=capability,
            note=annotation(element),
        )
        self.nodes.insert(len(self.nodes) if position is None else position, node)
        return node_id

    def _unique_id(self, candidate: str) -> str:
        node_id = candidate
        suffix = 2
        while node_id in self._ids:
            node_id = f"{candidate}_{suffix}"
            suffix += 1
        self._ids.add(node_id)
        return node_id


def _property(element: ET.Element, name: str) -> list[ET.Element]:
    """The activities under a property element such as `<If.Then>`."""
    return [
        activity
        for child in element
        if split_tag(child.tag)[1] == name
        for activity in child_activities(child)
    ]


def _catches(element: ET.Element) -> Iterator[tuple[str, ET.Element]]:
    """Each `<Catch>` of a TryCatch with the exception type it handles."""
    for catches in element:
        if split_tag(catches.tag)[1] != "TryCatch.Catches":
            continue
        for catch in catches:
            if split_tag(catch.tag)[1] == "Catch":
                exception = catch.get(f"{{{XAML_NS}}}TypeArguments", "Exception")
                yield exception.split(":")[-1], catch


def _condition_text(element: ET.Element) -> str:
    raw = element.get("Condition")
    if raw is None:
        condition_elements = [
            child for child in element if split_tag(child.tag)[1] == "If.Condition"
        ]
        raw = "".join(condition_elements[0].itertext()) if condition_elements else None
    return _expression_text(raw) or "condition"


def _expression_text(raw: str | None) -> str:
    return (raw or "").strip().removeprefix("[").removesuffix("]").strip()
