"""The parts of an OData EDMX document FlowGlyph reads, for both OData V2 and V4."""

from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

from flowglyph.ir import JsonSchema

EDMX_V2 = "http://schemas.microsoft.com/ado/2007/06/edmx"
EDMX_V4 = "http://docs.oasis-open.org/odata/ns/edmx"
METADATA_V2 = "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"
SAP = "http://www.sap.com/Protocols/SAPData"

_EDM_TYPES: dict[str, JsonSchema] = {
    "Edm.String": {"type": "string"},
    "Edm.Boolean": {"type": "boolean"},
    "Edm.Byte": {"type": "integer"},
    "Edm.SByte": {"type": "integer"},
    "Edm.Int16": {"type": "integer"},
    "Edm.Int32": {"type": "integer"},
    "Edm.Int64": {"type": "integer"},
    "Edm.Decimal": {"type": "number"},
    "Edm.Double": {"type": "number"},
    "Edm.Single": {"type": "number"},
    "Edm.Guid": {"type": "string", "format": "uuid"},
    "Edm.DateTime": {"type": "string", "format": "date-time"},
    "Edm.DateTimeOffset": {"type": "string", "format": "date-time"},
    "Edm.Date": {"type": "string", "format": "date"},
    "Edm.Time": {"type": "string", "format": "time"},
    "Edm.TimeOfDay": {"type": "string", "format": "time"},
    "Edm.Binary": {"type": "string", "contentEncoding": "base64"},
}


@dataclass(frozen=True)
class Property:
    """One property of an entity type."""

    name: str
    type: str
    nullable: bool
    label: str | None
    creatable: bool
    updatable: bool
    max_length: str | None


@dataclass(frozen=True)
class EntityType:
    """An OData entity type: its key and properties."""

    name: str
    label: str | None
    keys: tuple[str, ...]
    properties: tuple[Property, ...]

    def property(self, name: str) -> Property | None:
        """The property called `name`, if any."""
        return next((p for p in self.properties if p.name == name), None)


@dataclass(frozen=True)
class EntitySet:
    """An entity set and the operations the service allows on it."""

    name: str
    entity_type: str
    creatable: bool
    updatable: bool
    deletable: bool


@dataclass(frozen=True)
class Parameter:
    """An input of a function import, function or action."""

    name: str
    type: str
    nullable: bool


@dataclass(frozen=True)
class Operation:
    """A function import (V2), or a function or action (V4)."""

    name: str
    safe: bool
    parameters: tuple[Parameter, ...]
    return_type: str | None
    label: str | None
    bound_to: str | None = None
    namespace: str = ""


@dataclass
class Service:
    """Everything FlowGlyph needs from one OData metadata document."""

    name: str
    version: str
    entity_types: dict[str, EntityType] = field(default_factory=dict[str, EntityType])
    entity_sets: list[EntitySet] = field(default_factory=list[EntitySet])
    operations: list[Operation] = field(default_factory=list[Operation])

    def entity_type(self, qualified: str) -> EntityType | None:
        """The entity type named `qualified`, with or without its namespace."""
        return self.entity_types.get(qualified.rsplit(".", 1)[-1])

    def set_for(self, entity_type: str) -> EntitySet | None:
        """The first entity set holding entities of `entity_type`."""
        short = entity_type.rsplit(".", 1)[-1]
        return next((s for s in self.entity_sets if s.entity_type.endswith(short)), None)


def is_edmx(root: ET.Element) -> bool:
    """Whether `root` is the root of an OData metadata document."""
    return root.tag in {f"{{{EDMX_V2}}}Edmx", f"{{{EDMX_V4}}}Edmx"}


def parse_service(root: ET.Element, fallback_name: str) -> Service:
    """Read the schemas of an OData V2 or V4 metadata document."""
    version = "4.0" if root.tag == f"{{{EDMX_V4}}}Edmx" else "2.0"
    schemas = [element for element in root.iter() if _local(element.tag) == "Schema"]
    container_schema = next((s for s in schemas if _child(s, "EntityContainer") is not None), None)
    name = (
        container_schema.get("Namespace", fallback_name)
        if container_schema is not None
        else fallback_name
    )
    service = Service(name=name or fallback_name, version=version)
    restrictions = _restrictions(schemas)
    for schema in schemas:
        for element in schema:
            local = _local(element.tag)
            if local == "EntityType":
                entity = _entity_type(element)
                service.entity_types[entity.name] = entity
            elif local in {"Action", "Function"}:
                service.operations.append(
                    _v4_operation(
                        element, safe=local == "Function", namespace=schema.get("Namespace", "")
                    )
                )
            elif local == "EntityContainer":
                _container(element, service, restrictions)
    return service


def json_schema_for(edm_type: str, service: Service) -> JsonSchema:
    """JSON Schema for an EDM type, entity types and collections included."""
    if edm_type.startswith("Collection(") and edm_type.endswith(")"):
        return {"type": "array", "items": json_schema_for(edm_type[11:-1], service)}
    if edm_type in _EDM_TYPES:
        return dict(_EDM_TYPES[edm_type])
    entity = service.entity_type(edm_type)
    if entity is None:
        return {"type": "object", "x-edm-type": edm_type}
    return entity_schema(entity)


def entity_schema(entity: EntityType, names: set[str] | None = None) -> JsonSchema:
    """JSON Schema of an entity, optionally restricted to some property names."""
    properties: dict[str, JsonSchema] = {}
    for prop in entity.properties:
        if names is not None and prop.name not in names:
            continue
        properties[prop.name] = property_schema(prop)
    return {"type": "object", "properties": properties}


def property_schema(prop: Property) -> JsonSchema:
    """JSON Schema of one property, with its label and length limit."""
    schema = dict(_EDM_TYPES.get(prop.type, {"type": "object"}))
    schema["x-edm-type"] = prop.type
    if prop.label:
        schema["description"] = prop.label
    if prop.max_length and prop.max_length.isdigit() and schema.get("type") == "string":
        schema["maxLength"] = int(prop.max_length)
    return schema


def _entity_type(element: ET.Element) -> EntityType:
    key = _child(element, "Key")
    keys = tuple(ref.get("Name", "") for ref in key) if key is not None else ()
    properties = tuple(
        Property(
            name=prop.get("Name", ""),
            type=prop.get("Type", "Edm.String"),
            nullable=prop.get("Nullable", "true") != "false",
            label=prop.get(f"{{{SAP}}}label"),
            creatable=prop.get(f"{{{SAP}}}creatable", "true") != "false",
            updatable=prop.get(f"{{{SAP}}}updatable", "true") != "false",
            max_length=prop.get("MaxLength"),
        )
        for prop in element
        if _local(prop.tag) == "Property"
    )
    return EntityType(
        name=element.get("Name", ""),
        label=element.get(f"{{{SAP}}}label"),
        keys=keys,
        properties=properties,
    )


def _container(
    element: ET.Element, service: Service, restrictions: dict[str, dict[str, bool]]
) -> None:
    for child in element:
        local = _local(child.tag)
        if local == "EntitySet":
            name = child.get("Name", "")
            allowed = restrictions.get(name, {})
            service.entity_sets.append(
                EntitySet(
                    name=name,
                    entity_type=child.get("EntityType", ""),
                    creatable=allowed.get("Insertable", _sap_flag(child, "creatable")),
                    updatable=allowed.get("Updatable", _sap_flag(child, "updatable")),
                    deletable=allowed.get("Deletable", _sap_flag(child, "deletable")),
                )
            )
        elif local == "FunctionImport" and child.get("Function") is None:
            method = (child.get(f"{{{METADATA_V2}}}HttpMethod") or "POST").upper()
            service.operations.append(
                Operation(
                    name=child.get("Name", ""),
                    safe=method == "GET",
                    parameters=_parameters(child),
                    return_type=child.get("ReturnType"),
                    label=child.get(f"{{{SAP}}}label"),
                )
            )


def _v4_operation(element: ET.Element, *, safe: bool, namespace: str) -> Operation:
    parameters = _parameters(element)
    bound_to = None
    if element.get("IsBound") == "true" and parameters:
        bound_to, parameters = parameters[0].type, parameters[1:]
    returns = _child(element, "ReturnType")
    return Operation(
        name=element.get("Name", ""),
        safe=safe,
        parameters=parameters,
        return_type=returns.get("Type") if returns is not None else None,
        label=None,
        bound_to=bound_to,
        namespace=namespace,
    )


def _parameters(element: ET.Element) -> tuple[Parameter, ...]:
    return tuple(
        Parameter(
            name=child.get("Name", ""),
            type=child.get("Type", "Edm.String"),
            nullable=child.get("Nullable", "true") != "false",
        )
        for child in element
        if _local(child.tag) == "Parameter" and child.get("Mode", "In") != "Out"
    )


def _restrictions(schemas: list[ET.Element]) -> dict[str, dict[str, bool]]:
    """Capabilities vocabulary restrictions (V4) keyed by entity set name."""
    found: dict[str, dict[str, bool]] = {}
    for schema in schemas:
        for annotations in schema:
            if _local(annotations.tag) != "Annotations":
                continue
            target = annotations.get("Target", "").rsplit("/", 1)[-1]
            for annotation in annotations:
                term = annotation.get("Term", "")
                if not term.endswith(
                    ("InsertRestrictions", "UpdateRestrictions", "DeleteRestrictions")
                ):
                    continue
                for value in annotation.iter():
                    if _local(value.tag) == "PropertyValue" and value.get("Bool") is not None:
                        found.setdefault(target, {})[value.get("Property", "")] = (
                            value.get("Bool") == "true"
                        )
    return found


def _sap_flag(element: ET.Element, name: str) -> bool:
    return element.get(f"{{{SAP}}}{name}", "true") != "false"


def _child(element: ET.Element, local: str) -> ET.Element | None:
    return next((child for child in element if _local(child.tag) == local), None)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
