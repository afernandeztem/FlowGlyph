"""Workflow IR to a UiPath Studio workflow (`.xaml`).

A straight line of steps becomes a Sequence; anything with branches becomes a Flowchart of
FlowSteps and FlowDecisions. Calls to UiPath workflows become Invoke Workflow File activities
with their arguments listed, ready to bind in Studio. Calls to anything else become Comments
naming the capability, since FlowGlyph cannot know which activity a team uses to reach it.
"""

import re
from collections import defaultdict
from pathlib import PurePosixPath
from typing import Any, cast
from xml.etree import ElementTree as ET

from flowglyph.ir import Capability, Edge, Node, Workflow

ACTIVITIES = "http://schemas.microsoft.com/netfx/2009/xaml/activities"
UI = "http://schemas.uipath.com/workflow/activities"
X = "http://schemas.microsoft.com/winfx/2006/xaml"
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
SAP2010 = "http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
_PREFIXES = {
    "": ACTIVITIES,
    "ui": UI,
    "x": X,
    "mc": MC,
    "sap2010": SAP2010,
    "s": "clr-namespace:System;assembly=mscorlib",
    "scg": "clr-namespace:System.Collections.Generic;assembly=mscorlib",
    "sd": "clr-namespace:System.Data;assembly=System.Data",
}
_JSON_TO_CLR = {
    "string": "x:String",
    "integer": "x:Int32",
    "number": "x:Double",
    "boolean": "x:Boolean",
    "array": "s:Object[]",
}
_ARGUMENT = re.compile(r"^(?P<direction>In|Out|InOut)Argument\((?P<inner>.*)\)$")
_TYPE_PREFIX = re.compile(r"\b([A-Za-z]\w*):")
_CLASS = re.compile(r"[^\w]")


def to_xaml(
    workflow: Workflow,
    capability: Capability,
    *,
    called: dict[str, Capability] | None = None,
) -> tuple[str, list[str]]:
    """The XAML of `workflow`, and what could not be carried over exactly."""
    for prefix, uri in _PREFIXES.items():
        ET.register_namespace(prefix, uri)
    builder = _Builder(workflow, called or {})
    root = ET.Element(
        _q(ACTIVITIES, "Activity"),
        {_q(MC, "Ignorable"): "sap2010", _q(X, "Class"): _class_name(capability.title)},
    )
    members = _members(capability, builder.warnings)
    if len(members):
        root.append(members)
    root.append(builder.body(capability.title))
    ET.indent(root, space="  ")
    text = _declare(ET.tostring(root, encoding="unicode"), ("sap2010", "s", "scg", "sd"))
    return '<?xml version="1.0" encoding="utf-8"?>\n' + text + "\n", builder.warnings


def _declare(text: str, prefixes: tuple[str, ...]) -> str:
    """Declare namespaces that only appear inside attribute values, such as argument types.

    ElementTree declares a namespace only where a tag or attribute name uses it, but XAML also
    names types in values (`x:TypeArguments="scg:Dictionary(...)"`) and in `mc:Ignorable`.
    """
    end = text.index(">")
    head = text[:end]
    missing = "".join(
        f' xmlns:{prefix}="{_PREFIXES[prefix]}"'
        for prefix in prefixes
        if f"xmlns:{prefix}=" not in head
    )
    return head + missing + text[end:]


class _Builder:
    def __init__(self, workflow: Workflow, called: dict[str, Capability]) -> None:
        self.workflow = workflow
        self.called = called
        self.warnings: list[str] = []
        self.incoming: defaultdict[str, list[Edge]] = defaultdict(list)
        self.outgoing: defaultdict[str, list[Edge]] = defaultdict(list)
        for edge in workflow.edges:
            self.incoming[edge.target].append(edge)
            self.outgoing[edge.source].append(edge)
        self.references: dict[str, str] = {}

    def body(self, title: str) -> ET.Element:
        if self._linear():
            sequence = ET.Element(_q(ACTIVITIES, "Sequence"), {"DisplayName": title})
            for node in self._chain():
                sequence.append(self._activity(node))
            return sequence
        return self._flowchart(title)

    def _linear(self) -> bool:
        roots = [node for node in self.workflow.nodes if not self.incoming[node.id]]
        return len(roots) <= 1 and all(
            len(self.outgoing[node.id]) <= 1
            and len(self.incoming[node.id]) <= 1
            and not any(edge.condition for edge in self.outgoing[node.id])
            and node.kind != "decision"
            for node in self.workflow.nodes
        )

    def _chain(self) -> list[Node]:
        nodes = {node.id: node for node in self.workflow.nodes}
        current = next((n for n in self.workflow.nodes if not self.incoming[n.id]), None)
        ordered: list[Node] = []
        while current is not None and current not in ordered:
            ordered.append(current)
            following = self.outgoing[current.id]
            current = nodes.get(following[0].target) if following else None
        return ordered

    def _flowchart(self, title: str) -> ET.Element:
        chart = ET.Element(_q(ACTIVITIES, "Flowchart"), {"DisplayName": title})
        roots = [node for node in self.workflow.nodes if not self.incoming[node.id]]
        if len(roots) > 1:
            self.warnings.append(
                "several steps start in parallel; a Flowchart has one start, so only "
                f"{roots[0].label!r} is connected to it"
            )
        start = ET.SubElement(chart, _q(ACTIVITIES, "Flowchart.StartNode"))
        if roots:
            start.append(self._reference(roots[0].id))
        for node in self.workflow.nodes:
            chart.extend(self._flow_nodes(node))
        if any(n.join == "all" and len(self.incoming[n.id]) > 1 for n in self.workflow.nodes):
            self.warnings.append(
                "a Flowchart cannot wait for several branches; steps that joined them run when "
                "the first branch arrives"
            )
        return chart

    def _flow_nodes(self, node: Node) -> list[ET.Element]:
        """The FlowStep of `node`, or the FlowDecisions that test its conditions."""
        edges = sorted(self.outgoing[node.id], key=lambda edge: edge.target)
        conditional = [edge for edge in edges if edge.condition and edge.condition != "otherwise"]
        fallback = next((edge for edge in edges if edge.condition == "otherwise"), None)
        plain = [edge for edge in edges if not edge.condition]
        if len(plain) > 1:
            self.warnings.append(
                f"{node.label!r} continues on several branches at once; a Flowchart follows one, "
                "so only the first is connected"
            )
        otherwise = fallback or (plain[0] if plain and conditional else None)
        if node.kind == "decision" and conditional:
            return self._decisions(node.id, conditional, otherwise, node.label)
        step = ET.Element(_q(ACTIVITIES, "FlowStep"), {_q(X, "Name"): self._name(node.id)})
        step.append(self._activity(node))
        if conditional:
            test = f"{node.id}#test"
            step.append(self._next(test))
            return [step, *self._decisions(test, conditional, otherwise, f"{node.label}?")]
        following = plain[0] if plain else fallback
        if following is not None:
            step.append(self._next(following.target))
        return [step]

    def _decisions(
        self, owner: str, conditional: list[Edge], fallback: Edge | None, label: str
    ) -> list[ET.Element]:
        """A chain of FlowDecisions: the first condition, else the next, else the fallback."""
        chain: list[ET.Element] = []
        for index, edge in enumerate(conditional):
            decision = ET.Element(
                _q(ACTIVITIES, "FlowDecision"),
                {
                    _q(X, "Name"): self._name(owner if index == 0 else f"{owner}#{index}"),
                    "Condition": _condition(edge.condition or "", self.warnings),
                    "DisplayName": label if index == 0 else f"{label} ({index + 1})",
                },
            )
            ET.SubElement(decision, _q(ACTIVITIES, "FlowDecision.True")).append(
                self._reference(edge.target)
            )
            if chain:
                ET.SubElement(chain[-1], _q(ACTIVITIES, "FlowDecision.False")).append(
                    self._reference(f"{owner}#{index}")
                )
            chain.append(decision)
        if chain and fallback is not None:
            ET.SubElement(chain[-1], _q(ACTIVITIES, "FlowDecision.False")).append(
                self._reference(fallback.target)
            )
        return chain

    def _activity(self, node: Node) -> ET.Element:
        target = self.called.get(node.capability or "")
        if target is not None and target.source.provider == "uipath" and target.kind == "workflow":
            return _invoke(node, target, self.warnings)
        what = f"call {node.capability}" if node.capability else node.label
        detail = (
            f"{what}: FlowGlyph cannot write this call; use the activity your team uses to reach it"
            if node.capability
            else f"{what}: no capability does this yet"
        )
        return ET.Element(_q(UI, "Comment"), {"DisplayName": node.label, "Text": detail})

    def _next(self, target: str) -> ET.Element:
        following = ET.Element(_q(ACTIVITIES, "FlowStep.Next"))
        following.append(self._reference(target))
        return following

    def _reference(self, target: str) -> ET.Element:
        reference = ET.Element(_q(X, "Reference"))
        reference.text = self._name(target)
        return reference

    def _name(self, key: str) -> str:
        if key not in self.references:
            self.references[key] = f"__ReferenceID{len(self.references)}"
        return self.references[key]


def _invoke(node: Node, target: Capability, warnings: list[str]) -> ET.Element:
    path = PurePosixPath(target.source.location)
    invoke = ET.Element(
        _q(UI, "InvokeWorkflowFile"),
        {"DisplayName": node.label, "WorkflowFileName": "\\".join(path.parts)},
    )
    arguments = ET.SubElement(invoke, _q(UI, "InvokeWorkflowFile.Arguments"))
    dictionary = ET.SubElement(
        arguments,
        _q(_PREFIXES["scg"], "Dictionary"),
        {_q(X, "TypeArguments"): "x:String, Argument"},
    )
    properties: dict[str, Any] = target.input_schema.get("properties", {})
    for name, spec in properties.items():
        direction, clr = _argument_type(spec, warnings)
        ET.SubElement(
            dictionary,
            _q(ACTIVITIES, f"{direction}Argument"),
            {_q(X, "TypeArguments"): clr, _q(X, "Key"): name},
        )
    return invoke


def _members(capability: Capability, warnings: list[str]) -> ET.Element:
    members = ET.Element(_q(X, "Members"))
    for schema, default_direction in (
        (capability.input_schema, "In"),
        (capability.output_schema, "Out"),
    ):
        properties: dict[str, Any] = schema.get("properties", {})
        for name, spec in properties.items():
            direction, clr = _argument_type(spec, warnings, default_direction)
            ET.SubElement(
                members, _q(X, "Property"), {"Name": name, "Type": f"{direction}Argument({clr})"}
            )
    return members


def _argument_type(
    spec: dict[str, Any], warnings: list[str], direction: str = "In"
) -> tuple[str, str]:
    """The direction and .NET type of an argument, from its `x-clr-type` or its JSON type."""
    match = _ARGUMENT.match(str(spec.get("x-clr-type", "")))
    if match:
        inner = match["inner"]
        unknown = set(_TYPE_PREFIX.findall(inner)) - set(_PREFIXES)
        if not unknown:
            return match["direction"], inner
        warnings.append(f"type {inner} needs namespaces {sorted(unknown)}; it is written as Object")
        return match["direction"], "x:Object"
    declared: Any = spec.get("type")
    types = (
        [str(each) for each in cast("list[Any]", declared)]
        if isinstance(declared, list)
        else [str(declared)]
    )
    json_type = next((each for each in types if each != "null"), "object")
    return direction, _JSON_TO_CLR.get(json_type, "x:Object")


def _condition(condition: str, warnings: list[str]) -> str:
    text = condition.strip()
    if text.startswith("[") and text.endswith("]"):
        return text
    message = "conditions are copied as written; rewrite them as Visual Basic expressions in Studio"
    if message not in warnings:
        warnings.append(message)
    return f"[{text}]"


def _class_name(title: str) -> str:
    cleaned = _CLASS.sub("_", title).strip("_") or "Main"
    return cleaned if cleaned[0].isalpha() else f"W_{cleaned}"


def _q(namespace: str, tag: str) -> str:
    return f"{{{namespace}}}{tag}" if namespace else tag
