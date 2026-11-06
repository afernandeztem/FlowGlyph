"""Reading one XAML workflow into its arguments, effects, graph and activity usage."""

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET

from flowglyph.adapters.uipath.graph import GraphBuilder, InvokeResolver
from flowglyph.adapters.uipath.taxonomy import Category, Taxonomy
from flowglyph.adapters.uipath.xaml import (
    XAML_NS,
    annotation,
    argument_direction,
    child_activities,
    display_name,
    is_activity,
    is_designer_noise,
    json_schema_for,
    split_tag,
)
from flowglyph.ir import Effects, JsonSchema, Workflow

_EXPECTED_PREFIX = {"in": "in_", "out": "out_", "inout": "io_"}
_PREFIX = re.compile(r"^(in|out|io)_")
_IGNORED_ATTRIBUTES = frozenset({"DisplayName"})
_MAX_EXAMPLES = 3
_MAX_EXAMPLE_LENGTH = 80


@dataclass
class ActivityStats:
    """What has been observed about one activity type across a project."""

    namespace: str
    name: str
    category: Category
    uses: int = 0
    files: set[str] = field(default_factory=set[str])
    notes: list[str] = field(default_factory=list[str])
    parameter_uses: Counter[str] = field(default_factory=Counter[str])
    parameter_types: dict[str, set[str]] = field(default_factory=dict[str, set[str]])
    parameter_examples: dict[str, list[str]] = field(default_factory=dict[str, list[str]])

    @property
    def capability_id(self) -> str:
        """IR id of the activity type."""
        return f"uipath/activity/{self.name}"

    def observe(self, element: ET.Element, artifact: str) -> None:
        """Record one occurrence of the activity."""
        self.uses += 1
        self.files.add(artifact)
        note = annotation(element)
        if note and len(self.notes) < _MAX_EXAMPLES:
            self.notes.append(note)
        for key, value in element.attrib.items():
            namespace, local = split_tag(key)
            if namespace or local in _IGNORED_ATTRIBUTES or local.endswith("AnnotationText"):
                continue
            self._observe_parameter(local, example=value)
        for child in element:
            _, local = split_tag(child.tag)
            if local.startswith(self.name + "."):
                type_argument = next(
                    (
                        node.get(f"{{{XAML_NS}}}TypeArguments")
                        for node in child.iter()
                        if node.get(f"{{{XAML_NS}}}TypeArguments")
                    ),
                    None,
                )
                self._observe_parameter(local.split(".", 1)[1], clr_type=type_argument)

    def _observe_parameter(
        self, name: str, example: str | None = None, clr_type: str | None = None
    ) -> None:
        self.parameter_uses[name] += 1
        types = self.parameter_types.setdefault(name, set())
        if clr_type:
            types.add(clr_type)
        examples = self.parameter_examples.setdefault(name, [])
        if example is not None and len(examples) < _MAX_EXAMPLES:
            shortened = example[:_MAX_EXAMPLE_LENGTH]
            if shortened not in examples:
                examples.append(shortened)


@dataclass
class ParsedWorkflow:
    """Everything read from one workflow file, before cross-file resolution."""

    artifact: str
    class_name: str
    description: str
    input_schema: JsonSchema
    output_schema: JsonSchema
    activity_types: set[str]
    effects: Effects
    workflow: Workflow
    notes: list[str]


@dataclass
class WorkflowParser:
    """Parses UiPath workflow files of one project into IR building blocks."""

    taxonomy: Taxonomy
    resolve_invoke: InvokeResolver
    activities: dict[tuple[str, str], ActivityStats] = field(
        default_factory=dict[tuple[str, str], ActivityStats]
    )

    def parse(
        self, root: ET.Element, artifact: str, workflow_id: str, capability_id: str
    ) -> ParsedWorkflow:
        """Parse the document `root` read from `artifact`."""
        class_name = root.get(f"{{{XAML_NS}}}Class") or PurePosixPath(artifact).stem
        input_schema, output_schema, notes = _arguments(root, class_name)
        used: dict[tuple[str, str], ActivityStats] = {}
        self._collect_activities(root, artifact, used)
        top = next(child_activities(root), None)
        builder = GraphBuilder(classify=self._classify, resolve_invoke=self.resolve_invoke)
        return ParsedWorkflow(
            artifact=artifact,
            class_name=class_name,
            description=_description(top),
            input_schema=input_schema,
            output_schema=output_schema,
            activity_types={stats.name for stats in used.values()},
            effects=Effects.combine([stats.category.effects for stats in used.values()]),
            workflow=builder.build(workflow_id, capability_id, top),
            notes=notes,
        )

    def _classify(self, element: ET.Element) -> tuple[str, Category]:
        stats = self._stats(element)
        return stats.capability_id, stats.category

    def _stats(self, element: ET.Element) -> ActivityStats:
        namespace, name = split_tag(element.tag)
        key = (namespace, name)
        if key not in self.activities:
            category = self.taxonomy.classify(namespace, name)
            self.activities[key] = ActivityStats(namespace, name, category)
        return self.activities[key]

    def _collect_activities(
        self, element: ET.Element, artifact: str, used: dict[tuple[str, str], ActivityStats]
    ) -> None:
        if is_designer_noise(element):
            return
        if is_activity(element):
            stats = self._stats(element)
            stats.observe(element, artifact)
            used[stats.namespace, stats.name] = stats
        for child in element:
            self._collect_activities(child, artifact, used)


def _arguments(root: ET.Element, class_name: str) -> tuple[JsonSchema, JsonSchema, list[str]]:
    defaults = _default_values(root, class_name)
    inputs: dict[str, JsonSchema] = {}
    outputs: dict[str, JsonSchema] = {}
    required: list[str] = []
    notes: list[str] = []
    for prop in root.iter(f"{{{XAML_NS}}}Property"):
        name = prop.get("Name")
        if not name:
            continue
        clr_type = prop.get("Type", "")
        direction = argument_direction(clr_type)
        schema = json_schema_for(clr_type)
        description = annotation(prop)
        if description:
            schema["description"] = description
        if name in defaults:
            schema["x-default-expression"] = defaults[name]
        if direction == "out":
            outputs[name] = schema
            continue
        schema["x-direction"] = direction
        inputs[name] = schema
        if _is_required(prop) or name not in defaults:
            required.append(name)
        if _PREFIX.match(name) and not name.startswith(_EXPECTED_PREFIX[direction]):
            notes.append(f"argument {name} is named like {name.split('_')[0]}_ but is {direction}")
    input_schema: JsonSchema = {
        "type": "object",
        "properties": inputs,
        "required": required,
        "additionalProperties": False,
    }
    return input_schema, {"type": "object", "properties": outputs}, notes


def _default_values(root: ET.Element, class_name: str) -> dict[str, str]:
    prefix = class_name + "."
    defaults: dict[str, str] = {}
    for key, value in root.attrib.items():
        local = split_tag(key)[1]
        if local.startswith(prefix):
            defaults[local.removeprefix(prefix)] = value
    return defaults


def _is_required(prop: ET.Element) -> bool:
    return any(split_tag(element.tag)[1] == "RequiredArgumentAttribute" for element in prop.iter())


def _description(top: ET.Element | None) -> str:
    if top is None:
        return ""
    note = annotation(top)
    if note:
        return note
    label = display_name(top)
    return "" if label == split_tag(top.tag)[1] else label
