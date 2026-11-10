"""Workflow IR to BPMN 2.0, for any modeler, or ready to deploy to Camunda 7 or Camunda 8.

Steps become tasks, decisions exclusive gateways, and calls to BPMN processes call activities.
A step that waits for all its predecessors gets a parallel join in front of it. Conditions are
written as the source wrote them: an engine may need them in its own expression language.
"""

import re
from collections import defaultdict
from typing import Literal
from xml.etree import ElementTree as ET

from flowglyph.compilers._layout import Box, place
from flowglyph.errors import CatalogError
from flowglyph.ir import Capability, Workflow

type Engine = Literal["bpmn", "camunda7", "camunda8"]

BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI = "http://www.omg.org/spec/BPMN/20100524/DI"
DC = "http://www.omg.org/spec/DD/20100524/DC"
DI = "http://www.omg.org/spec/DD/20100524/DI"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
CAMUNDA = "http://camunda.org/schema/1.0/bpmn"
ZEEBE = "http://camunda.org/schema/zeebe/1.0"
FLOWGLYPH = "urn:flowglyph:bpmn:1"
_PREFIXES = {
    "bpmn": BPMN,
    "bpmndi": BPMNDI,
    "dc": DC,
    "di": DI,
    "xsi": XSI,
    "camunda": CAMUNDA,
    "zeebe": ZEEBE,
    "flowglyph": FLOWGLYPH,
}
_NCNAME = re.compile(r"[^\w.-]")
_SIZES = {"task": (100, 80), "gateway": (50, 50), "event": (36, 36)}


def to_bpmn(
    workflow: Workflow,
    capability: Capability,
    *,
    called: dict[str, Capability] | None = None,
    engine: Engine = "bpmn",
) -> tuple[str, list[str]]:
    """The BPMN document of `workflow`, and what could not be carried over exactly.

    `called` holds the capabilities the workflow invokes: those that are BPMN processes become
    call activities, the others service tasks that name the capability.
    """
    for prefix, uri in _PREFIXES.items():
        ET.register_namespace(prefix, uri)
    called = called or {}
    process_id = _xml_id(
        capability.source.artifact if capability.source.provider == "bpmn" else workflow.id
    )
    definitions = ET.Element(
        _q(BPMN, "definitions"),
        {"id": "Definitions_" + process_id, "targetNamespace": "urn:flowglyph:compiled"},
    )
    process = ET.SubElement(
        definitions,
        _q(BPMN, "process"),
        {"id": process_id, "name": capability.title, "isExecutable": "true"},
    )
    if capability.description:
        ET.SubElement(process, _q(BPMN, "documentation")).text = capability.description
    builder = _Builder(process, workflow, called, engine)
    builder.build()
    _diagram(definitions, process_id, builder)
    ET.indent(definitions, space="  ")
    text = ET.tostring(definitions, encoding="unicode", xml_declaration=False)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + text + "\n", builder.warnings


class _Builder:
    def __init__(
        self, process: ET.Element, workflow: Workflow, called: dict[str, Capability], engine: Engine
    ) -> None:
        self.process = process
        self.workflow = workflow
        self.called = called
        self.engine = engine
        names = [node.id for node in workflow.nodes]
        repeated = sorted({name for name in names if names.count(name) > 1})
        if repeated:
            raise CatalogError(f"step ids must be unique; repeated: {', '.join(repeated)}")
        loose = sorted(
            {end for edge in workflow.edges for end in (edge.source, edge.target)} - set(names)
        )
        if loose:
            raise CatalogError(f"an edge points to a step that does not exist: {', '.join(loose)}")
        self.ids = _unique_ids(names)
        self.kinds: dict[str, str] = {}
        self.flows: list[tuple[str, str, str]] = []
        self.warnings: list[str] = []

    def build(self) -> None:
        incoming: defaultdict[str, list[str]] = defaultdict(list)
        outgoing: defaultdict[str, list[str]] = defaultdict(list)
        for edge in self.workflow.edges:
            incoming[edge.target].append(edge.source)
            outgoing[edge.source].append(edge.target)
        self._element("start", "startEvent", {"id": "start"}, "event")
        for node in self.workflow.nodes:
            self._node(node.id)
        joins = {
            node.id: f"join_{self.ids[node.id]}"
            for node in self.workflow.nodes
            if node.join == "all" and len(incoming[node.id]) > 1
        }
        for node_id, join in joins.items():
            self._element(join, "parallelGateway", {"id": join, "name": "all done"}, "gateway")
            self._flow(join, self.ids[node_id])
        self._element("end", "endEvent", {"id": "end"}, "event")
        for node in self.workflow.nodes:
            if not incoming[node.id]:
                self._flow("start", self.ids[node.id])
            if not outgoing[node.id]:
                self._flow(self.ids[node.id], "end")
        if not self.workflow.nodes:
            self._flow("start", "end")
        conditions = {edge.condition for edge in self.workflow.edges if edge.condition}
        if conditions - {"otherwise"}:
            self.warnings.append(
                "conditions are copied as written; translate them to the target engine's "
                "expression language before deploying"
            )
        defaults = self._defaults()
        for edge in self.workflow.edges:
            target = joins.get(edge.target, self.ids[edge.target])
            source = self.ids[edge.source]
            if edge.condition == "otherwise" or edge in defaults:
                flow_id = self._flow(source, target)
                self._find(source).set("default", flow_id)
            else:
                self._flow(source, target, edge.condition)

    def _defaults(self) -> set[object]:
        """Plain edges that are a decision's else branch.

        An exclusive gateway may only leave through a condition or its default flow, so the one
        unconditioned edge of a decision that also has conditions becomes the default.
        """
        defaults: set[object] = set()
        for node in self.workflow.nodes:
            if node.kind != "decision":
                continue
            edges = [edge for edge in self.workflow.edges if edge.source == node.id]
            plain = [edge for edge in edges if not edge.condition]
            has_default = any(edge.condition == "otherwise" for edge in edges)
            if len(plain) == 1 and len(edges) > 1 and not has_default:
                defaults.add(plain[0])
            elif len(plain) > 1:
                self.warnings.append(
                    f"decision {node.label!r} has several unconditioned branches; BPMN takes "
                    "only one of them through its default flow"
                )
        return defaults

    def _node(self, node_id: str) -> None:
        node = next(n for n in self.workflow.nodes if n.id == node_id)
        element_id = self.ids[node_id]
        attributes = {"id": element_id, "name": node.label}
        if node.kind == "decision":
            self._element(element_id, "exclusiveGateway", attributes, "gateway")
            return
        target = self.called.get(node.capability or "")
        if target is not None and target.source.provider == "bpmn":
            element = self._element(element_id, "callActivity", attributes, "task")
            element.set("calledElement", target.source.artifact)
            if self.engine == "camunda8":
                extension = ET.SubElement(element, _q(BPMN, "extensionElements"))
                ET.SubElement(
                    extension, _q(ZEEBE, "calledElement"), {"processId": target.source.artifact}
                )
            return
        kind = "serviceTask" if node.capability or self.engine != "bpmn" else "task"
        element = self._element(element_id, kind, attributes, "task")
        if node.capability:
            element.set(_q(FLOWGLYPH, "capability"), node.capability)
        job = node.capability or _xml_id(node.label).lower()
        if self.engine == "camunda7" and kind == "serviceTask":
            element.set(_q(CAMUNDA, "type"), "external")
            element.set(_q(CAMUNDA, "topic"), job)
        elif self.engine == "camunda8" and kind == "serviceTask":
            extension = ET.SubElement(element, _q(BPMN, "extensionElements"))
            ET.SubElement(extension, _q(ZEEBE, "taskDefinition"), {"type": job})

    def _element(
        self, element_id: str, tag: str, attributes: dict[str, str], kind: str
    ) -> ET.Element:
        self.kinds[element_id] = kind
        return ET.SubElement(self.process, _q(BPMN, tag), attributes)

    def _flow(self, source: str, target: str, condition: str | None = None) -> str:
        flow_id = f"flow_{len(self.flows) + 1}"
        self.flows.append((flow_id, source, target))
        flow = ET.SubElement(
            self.process,
            _q(BPMN, "sequenceFlow"),
            {"id": flow_id, "sourceRef": source, "targetRef": target},
        )
        if condition:
            expression = ET.SubElement(
                flow, _q(BPMN, "conditionExpression"), {_q(XSI, "type"): "bpmn:tFormalExpression"}
            )
            expression.text = condition
        return flow_id

    def _find(self, element_id: str) -> ET.Element:
        return next(child for child in self.process if child.get("id") == element_id)


def _diagram(definitions: ET.Element, process_id: str, builder: _Builder) -> None:
    elements = list(builder.kinds)
    edges = [(source, target) for _, source, target in builder.flows]
    sizes = {element: _SIZES[kind] for element, kind in builder.kinds.items()}
    boxes = place(elements, edges, sizes)
    diagram = ET.SubElement(definitions, _q(BPMNDI, "BPMNDiagram"), {"id": "Diagram_1"})
    plane = ET.SubElement(
        diagram, _q(BPMNDI, "BPMNPlane"), {"id": "Plane_1", "bpmnElement": process_id}
    )
    for element in elements:
        shape = ET.SubElement(
            plane, _q(BPMNDI, "BPMNShape"), {"id": f"{element}_di", "bpmnElement": element}
        )
        _bounds(shape, boxes[element])
    for flow_id, source, target in builder.flows:
        edge = ET.SubElement(
            plane, _q(BPMNDI, "BPMNEdge"), {"id": f"{flow_id}_di", "bpmnElement": flow_id}
        )
        for x, y in (boxes[source].right, boxes[target].left):
            ET.SubElement(edge, _q(DI, "waypoint"), {"x": str(x), "y": str(y)})


def _bounds(shape: ET.Element, box: Box) -> None:
    ET.SubElement(
        shape,
        _q(DC, "Bounds"),
        {"x": str(box.x), "y": str(box.y), "width": str(box.width), "height": str(box.height)},
    )


_GENERATED = re.compile(r"flow_\d+|join_.+")


def _unique_ids(node_ids: list[str]) -> dict[str, str]:
    """Node ids made valid XML ids: no spaces or symbols, never starting with a digit."""
    ids: dict[str, str] = {}
    taken = {"start", "end"}
    for node_id in node_ids:
        base = _xml_id(node_id)
        if _GENERATED.fullmatch(base):  # the names this compiler gives to flows and joins
            base = f"n_{base}"
        candidate, counter = base, 2
        while candidate in taken:
            candidate, counter = f"{base}_{counter}", counter + 1
        taken.add(candidate)
        ids[node_id] = candidate
    return ids


def _xml_id(text: str) -> str:
    cleaned = _NCNAME.sub("_", text).strip("_") or "step"
    return cleaned if cleaned[0].isalpha() or cleaned[0] == "_" else f"n_{cleaned}"


def _q(namespace: str, tag: str) -> str:
    return f"{{{namespace}}}{tag}"
