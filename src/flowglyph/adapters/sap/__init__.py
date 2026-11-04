"""Adapter for SAP OData services, read from their `$metadata` (EDMX, OData V2 and V4).

Every SAP S/4HANA, SAP Gateway and SAP BTP OData service publishes this XML document. It lists
the entity sets, which operations each one allows (`sap:creatable`, `sap:updatable`,
`sap:deletable`, or the V4 Capabilities vocabulary), their typed properties and the function
imports, functions and actions of the service.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from flowglyph._internal.hashing import digest
from flowglyph._internal.xml import load_xml
from flowglyph.adapters import Diagnostic, Extraction
from flowglyph.adapters.sap.edmx import (
    EntitySet,
    EntityType,
    Operation,
    Service,
    entity_schema,
    is_edmx,
    json_schema_for,
    parse_service,
    property_schema,
)
from flowglyph.errors import AdapterError
from flowglyph.ir import Capability, Effects, Idempotency, JsonSchema, Source, Tri

_SUFFIXES = frozenset({".xml", ".edmx"})
_EDMX_MARKER = re.compile(rb"<(?:[\w-]+:)?Edmx\b")
_QUERY_OPTIONS: JsonSchema = {
    "$filter": {"type": "string", "description": "OData filter expression."},
    "$select": {"type": "string", "description": "Comma-separated properties to return."},
    "$orderby": {"type": "string"},
    "$top": {"type": "integer", "minimum": 0},
    "$skip": {"type": "integer", "minimum": 0},
}
_READ = Effects(reads=Tri.YES, mutates_state=Tri.NO, destructive=Tri.NO, external=Tri.YES)
_CREATE = Effects(reads=Tri.NO, mutates_state=Tri.YES, destructive=Tri.NO, external=Tri.YES)
_UPDATE = Effects(reads=Tri.NO, mutates_state=Tri.YES, destructive=Tri.UNKNOWN, external=Tri.YES)
_DELETE = Effects(reads=Tri.NO, mutates_state=Tri.YES, destructive=Tri.YES, external=Tri.YES)
_ACTION = Effects(
    reads=Tri.UNKNOWN, mutates_state=Tri.UNKNOWN, destructive=Tri.UNKNOWN, external=Tri.YES
)
_CREATE_NOTE = (
    "OData has no standard idempotency key for creation: declare one, such as an external "
    "reference field, in flowglyph.overrides.yaml"
)


class SapODataAdapter:
    """Turns an SAP OData service's metadata into one capability per allowed operation.

    Reads are idempotent and side-effect free; updates and deletes are idempotent by OData
    semantics; creations and actions are not, unless an override declares a key. Operations
    the service forbids are not generated at all.
    """

    name: ClassVar[str] = "sap"
    version: ClassVar[str] = "0.1.0"

    def detect(self, path: Path) -> bool:
        """Whether `path` is an OData metadata document or a folder containing one."""
        return bool(self.discover(path))

    def discover(self, root: Path) -> list[Path]:
        """Every OData metadata document under `root`, one source per file."""
        if root.is_file():
            return [root] if _is_metadata(root) else []
        if not root.is_dir():
            return []
        return sorted(file for file in root.rglob("*") if file.is_file() and _is_metadata(file))

    def extract(self, path: Path) -> Extraction:
        """Extract every metadata document at `path`."""
        root = path if path.is_dir() else path.parent
        capabilities: list[Capability] = []
        artifacts: dict[str, str] = {}
        diagnostics: list[Diagnostic] = []
        for file in self.discover(path):
            artifact = file.relative_to(root).as_posix()
            artifacts[artifact] = digest(file.read_bytes())
            try:
                document = load_xml(file)
            except AdapterError as error:
                diagnostics.append(Diagnostic("error", artifact, str(error)))
                continue
            service = parse_service(document, file.stem)
            reader = _ServiceReader(service, artifact, artifacts[artifact])
            capabilities.extend(reader.capabilities())
            diagnostics.extend(reader.diagnostics)
        return Extraction(capabilities=capabilities, artifacts=artifacts, diagnostics=diagnostics)


class _ServiceReader:
    def __init__(self, service: Service, artifact: str, source_hash: str) -> None:
        self.service = service
        self.artifact = artifact
        self.source_hash = source_hash
        self.diagnostics: list[Diagnostic] = []

    def capabilities(self) -> list[Capability]:
        found: list[Capability] = []
        for entity_set in self.service.entity_sets:
            entity = self.service.entity_type(entity_set.entity_type)
            if entity is None:
                self.diagnostics.append(
                    Diagnostic(
                        "warning",
                        self.artifact,
                        f"{entity_set.name} uses unknown type {entity_set.entity_type}",
                    )
                )
                continue
            found.extend(self._entity_operations(entity_set, entity))
        found.extend(self._operation(operation) for operation in self.service.operations)
        return found

    def _entity_operations(self, entity_set: EntitySet, entity: EntityType) -> list[Capability]:
        label = entity.label or entity_set.name
        keys = self._keys(entity)
        record = entity_schema(entity)
        empty: JsonSchema = {"type": "object", "properties": {}}
        operations = [
            _Operation(
                name=f"{entity_set.name}/query",
                description=f"List {label} records",
                request=f"GET {entity_set.name}",
                inputs=_object(_QUERY_OPTIONS, []),
                outputs={
                    "type": "object",
                    "properties": {"value": {"type": "array", "items": record}},
                },
                effects=_READ,
                idempotency=Idempotency(mode="natural", confidence=0.9),
            ),
            _Operation(
                name=f"{entity_set.name}/read",
                description=f"Read one {label} by its key",
                request=f"GET {entity_set.name}(key)",
                inputs=_object(keys, list(keys)),
                outputs=record,
                effects=_READ,
                idempotency=Idempotency(mode="natural", confidence=0.9),
            ),
        ]
        if entity_set.creatable:
            creatable = {p.name for p in entity.properties if p.creatable}
            body = entity_schema(entity, creatable)
            body["required"] = [p.name for p in entity.properties if p.creatable and not p.nullable]
            operations.append(
                _Operation(
                    name=f"{entity_set.name}/create",
                    description=f"Create a {label}",
                    request=f"POST {entity_set.name}",
                    inputs=_object({"body": body}, ["body"]),
                    outputs=record,
                    effects=_CREATE,
                    idempotency=Idempotency(mode="none", confidence=0.7),
                    notes=(_CREATE_NOTE,),
                )
            )
        if entity_set.updatable:
            updatable = {p.name for p in entity.properties if p.updatable and p.name not in keys}
            operations.append(
                _Operation(
                    name=f"{entity_set.name}/update",
                    description=f"Change fields of a {label}",
                    request=f"PATCH {entity_set.name}(key)",
                    inputs=_object(
                        {**keys, "body": entity_schema(entity, updatable)}, [*keys, "body"]
                    ),
                    outputs=empty,
                    effects=_UPDATE,
                    idempotency=Idempotency(mode="natural", confidence=0.6),
                )
            )
        if entity_set.deletable:
            operations.append(
                _Operation(
                    name=f"{entity_set.name}/delete",
                    description=f"Delete a {label}",
                    request=f"DELETE {entity_set.name}(key)",
                    inputs=_object(keys, list(keys)),
                    outputs=empty,
                    effects=_DELETE,
                    idempotency=Idempotency(mode="natural", confidence=0.8),
                )
            )
        return [self._capability(operation) for operation in operations]

    def _operation(self, operation: Operation) -> Capability:
        inputs: dict[str, JsonSchema] = {}
        required: list[str] = []
        prefix = ""
        if operation.bound_to:
            entity = self.service.entity_type(operation.bound_to)
            entity_set = self.service.set_for(operation.bound_to)
            prefix = f"{entity_set.name}/" if entity_set else ""
            if entity is not None:
                inputs.update(self._keys(entity))
                required.extend(entity.keys)
        for parameter in operation.parameters:
            inputs[parameter.name] = json_schema_for(parameter.type, self.service)
            if not parameter.nullable:
                required.append(parameter.name)
        returns: JsonSchema = {"type": "object", "properties": {}}
        if operation.return_type:
            returns = {
                "type": "object",
                "properties": {"value": json_schema_for(operation.return_type, self.service)},
            }
        safe = operation.safe
        return self._capability(
            _Operation(
                name=f"{prefix}{operation.name}",
                description=operation.label or operation.name,
                request=f"{'GET' if safe else 'POST'} {operation.name}",
                inputs=_object(inputs, required),
                outputs=returns,
                effects=_READ if safe else _ACTION,
                idempotency=Idempotency(mode="natural", confidence=0.8)
                if safe
                else Idempotency(mode="none", confidence=0.6),
                tag="function" if safe else "action",
            )
        )

    def _keys(self, entity: EntityType) -> dict[str, JsonSchema]:
        keys: dict[str, JsonSchema] = {}
        for name in entity.keys:
            prop = entity.property(name)
            keys[name] = property_schema(prop) if prop else {"type": "string"}
        return keys

    def _capability(self, operation: "_Operation") -> Capability:
        tags = [f"odata-v{self.service.version.split('.')[0]}"]
        if operation.tag:
            tags.append(operation.tag)
        return Capability(
            id=f"sap/{self.service.name}/{operation.name}",
            kind="operation",
            title=operation.name,
            description=operation.description,
            category=self.service.name,
            input_schema=operation.inputs,
            output_schema=operation.outputs,
            effects=operation.effects,
            idempotency=operation.idempotency,
            tags=tuple(tags),
            notes=operation.notes,
            source=Source(
                provider="sap",
                artifact=operation.request,
                location=f"{self.artifact}#{operation.name}",
                source_hash=self.source_hash,
                artifact_version=self.service.version,
            ),
        )


@dataclass(frozen=True)
class _Operation:
    name: str
    description: str
    request: str
    inputs: JsonSchema
    outputs: JsonSchema
    effects: Effects
    idempotency: Idempotency
    notes: tuple[str, ...] = ()
    tag: str | None = None


def _object(properties: JsonSchema, required: list[str]) -> JsonSchema:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _is_metadata(file: Path) -> bool:
    if file.suffix.lower() not in _SUFFIXES and "$metadata" not in file.name:
        return False
    with file.open("rb") as handle:
        head = handle.read(4096)
    if _EDMX_MARKER.search(head) is None:
        return False
    try:
        return is_edmx(load_xml(file))
    except AdapterError:
        return True


__all__ = ["SapODataAdapter"]
