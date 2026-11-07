"""XAML templates of activities, taken from how a project itself uses them.

A template keeps the structure and the settings of one real use: which properties are set, enum
and boolean values, argument types. Values that are this workflow's data (expressions, text,
paths) become placeholders such as `[body]`, and nested activities become a comment, so a coding
agent can copy the template and fill it in. Prefixes are the project's own.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from xml.etree import ElementTree as ET

from flowglyph.adapters.uipath.xaml import (
    DESIGNER_NAMESPACES,
    XAML_NS,
    is_activity,
    is_designer_noise,
    split_tag,
)

_KEPT_VALUE = re.compile(r"^(True|False|\{x:Null\}|-?\d+(\.\d+)?|[A-Z][A-Za-z0-9]*)$")
_EXPRESSION_TAGS = frozenset(
    {"VisualBasicValue", "VisualBasicReference", "CSharpValue", "CSharpReference", "Literal"}
)
_XMLNS = re.compile(r'\s+xmlns(?::[\w.-]+)?="[^"]*"')
_PREFIX_USE = re.compile(r"(?<![\w.])([A-Za-z_][\w.-]*):(?=[A-Za-z_])")
_MAX_DEPTH = 8


@dataclass(frozen=True)
class Template:
    """A placeholder XAML fragment and the namespace declarations it needs."""

    xml: str
    namespaces: dict[str, str]
    size: int


def template(element: ET.Element, prefixes: Mapping[str, str]) -> Template:
    """The template of `element`, written with the `prefixes` its file declares."""
    copy = _copy(element, owner=split_tag(element.tag)[1], depth=0)
    for prefix, uri in prefixes.items():
        if not re.fullmatch(r"ns\d+", prefix):
            ET.register_namespace(prefix, uri)
    ET.indent(copy, space="  ")
    xml = _XMLNS.sub("", ET.tostring(copy, encoding="unicode"))
    used = set(_PREFIX_USE.findall(xml))
    namespaces = {prefix: uri for prefix, uri in prefixes.items() if prefix in used or prefix == ""}
    size = len(copy.attrib) + len(copy)
    return Template(xml=xml, namespaces=dict(sorted(namespaces.items())), size=size)


def _copy(element: ET.Element, *, owner: str, depth: int) -> ET.Element:
    copy = ET.Element(element.tag)
    local = split_tag(element.tag)[1]
    for key, value in element.attrib.items():
        kept = _attribute(key, value, owner if local in _EXPRESSION_TAGS else local)
        if kept is not None:
            copy.set(key, kept)
    if element.text and element.text.strip():
        copy.text = _placeholder(owner)
    commented = False
    for child in element:
        if is_designer_noise(child):
            continue
        if is_activity(child):
            if not commented:
                copy.append(ET.Comment(" activities "))
                commented = True
            continue
        if depth < _MAX_DEPTH:
            child_local = split_tag(child.tag)[1]
            name = child_local.split(".", 1)[1] if "." in child_local else owner
            copy.append(_copy(child, owner=name, depth=depth + 1))
    return copy


def _attribute(key: str, value: str, element: str) -> str | None:
    """The attribute as a template keeps it: settings stay, data becomes a placeholder."""
    namespace, name = split_tag(key)
    if namespace in DESIGNER_NAMESPACES - {XAML_NS} or name.endswith("AnnotationText"):
        return None
    if namespace == XAML_NS:
        return value if name in {"TypeArguments", "Key"} else None
    if name == "ExpressionText":
        return _placeholder(element)
    if name == "DisplayName" or _KEPT_VALUE.match(value.strip()):
        return value
    return _placeholder(name)


def _placeholder(name: str) -> str:
    return f"[{name[:1].lower()}{name[1:]}]"
