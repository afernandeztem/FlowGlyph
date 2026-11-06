"""XAML helpers: loading, tag names, activity detection and argument types."""

import re
from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree as ET

from flowglyph._internal.xml import load_xml
from flowglyph.ir import JsonSchema

XAML_NS = "http://schemas.microsoft.com/winfx/2006/xaml"

DESIGNER_NAMESPACES = frozenset(
    {
        "http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation",
        "http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation",
        "http://schemas.microsoft.com/winfx/2006/xaml/presentation",
        "http://schemas.openxmlformats.org/markup-compatibility/2006",
        XAML_NS,
    }
)

NON_ACTIVITY_TYPES = frozenset(
    {
        "Activity", "Members", "InArgument", "OutArgument", "InOutArgument", "Variable",
        "Literal", "VisualBasicValue", "VisualBasicReference", "CSharpValue", "CSharpReference",
        "AssemblyReference", "Dictionary", "List", "Collection", "ActivityAction",
        "DelegateInArgument", "DelegateOutArgument", "Catch", "FlowStep", "Target", "Selector",
        "String", "Boolean", "Int32", "Object",
    }
)  # fmt: skip

_CLR_TO_JSON = {
    "String": "string",
    "Int32": "integer",
    "Int64": "integer",
    "Double": "number",
    "Decimal": "number",
    "Boolean": "boolean",
    "DateTime": "string",
    "TimeSpan": "string",
}
_ARRAY_TYPES = frozenset({"List", "IEnumerable", "Collection"})
_ARGUMENT_TYPE = re.compile(r"\s*(?P<direction>In|Out|InOut)Argument\((?P<inner>.*)\)\s*$")


def load(path: Path) -> ET.Element:
    """Parse a XAML file, refusing documents that declare a DTD."""
    return load_xml(path)


def split_tag(tag: str) -> tuple[str, str]:
    """Split a Clark-notation tag into namespace and local name."""
    if tag.startswith("{"):
        namespace, local = tag[1:].split("}", 1)
        return namespace, local
    return "", tag


def is_designer_noise(element: ET.Element) -> bool:
    """Whether the element only carries designer layout or assembly metadata."""
    namespace, local = split_tag(element.tag)
    return namespace in DESIGNER_NAMESPACES or local.startswith("TextExpression.")


def is_activity(element: ET.Element) -> bool:
    """Whether the element is an activity rather than a property, value or wrapper."""
    namespace, local = split_tag(element.tag)
    return (
        "." not in local
        and namespace not in DESIGNER_NAMESPACES
        and local not in NON_ACTIVITY_TYPES
    )


def child_activities(element: ET.Element) -> Iterator[ET.Element]:
    """Direct child activities, looking through property elements such as `<If.Then>`."""
    for child in element:
        if is_designer_noise(child):
            continue
        if is_activity(child):
            yield child
        else:
            yield from child_activities(child)


def annotation(element: ET.Element) -> str | None:
    """The designer annotation attached to an element, if any."""
    for key, value in element.attrib.items():
        if key.endswith("AnnotationText"):
            return value.strip() or None
    return None


def display_name(element: ET.Element) -> str:
    """The label shown in Studio, falling back to the activity type."""
    return element.get("DisplayName") or split_tag(element.tag)[1]


def view_state_id(element: ET.Element) -> str | None:
    """The `WorkflowViewState.IdRef` Studio assigns to an activity, stable across saves."""
    for key, value in element.attrib.items():
        if key.endswith("WorkflowViewState.IdRef"):
            return value
    return None


def argument_direction(clr_type: str) -> str:
    """`in`, `out` or `inout` for a XAML argument type such as `InArgument(x:String)`."""
    match = _ARGUMENT_TYPE.match(clr_type)
    return match["direction"].lower() if match else "in"


def json_schema_for(clr_type: str) -> JsonSchema:
    """JSON Schema for a XAML argument type, keeping the original type as `x-clr-type`."""
    match = _ARGUMENT_TYPE.match(clr_type)
    inner = match["inner"] if match else clr_type
    base = inner.split("(")[0].split(":")[-1].split(".")[-1]
    if inner.endswith("[]") or base in _ARRAY_TYPES:
        json_type = "array"
    else:
        json_type = _CLR_TO_JSON.get(base, "object")
    return {"type": json_type, "x-clr-type": clr_type}
