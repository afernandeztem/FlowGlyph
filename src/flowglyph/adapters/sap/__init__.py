"""Adapter for SAP OData services, read from their `$metadata` (EDMX, OData V2 and V4).

Every SAP S/4HANA, SAP Gateway and SAP BTP OData service publishes this XML document. It lists
the entity sets, which operations each one allows (`sap:creatable`, `sap:updatable`,
`sap:deletable`, or the V4 Capabilities vocabulary), their typed properties and the function
imports, functions and actions of the service.
"""

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar
from xml.etree import ElementTree as ET

from flowglyph._internal.hashing import digest
from flowglyph._internal.paths import distinguishing_names
from flowglyph._internal.xml import parse_xml
from flowglyph.adapters import Diagnostic, Extraction
from flowglyph.adapters.sap.edmx import (
    METADATA_V2,
    SAP,
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
from flowglyph.ir import Capability, Effects, Idempotency, JsonSchema, Source, Tri, Trigger

_SUFFIXES = frozenset({".xml", ".edmx"})
_EDMX_ROOT = re.compile(rb"<(?:[\w-]+:)?Edmx\b")
_KNOWN_PREFIXES = {"sap": SAP, "m": METADATA_V2}
_COLLISION = 2
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
    "OData defines no idempotency key for creation; services usually reject duplicates on an "
    "external reference field instead"
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
        return bool(_metadata_files(path))

    def discover(self, root: Path) -> list[Path]:
        """`root` itself when it holds metadata documents: they are read together.

        Reading them together lets the adapter notice the same service published twice, for
        instance as OData V2 and V4, and keep both apart.
        """
        return [root] if _metadata_files(root) else []

    def extract(self, path: Path) -> Extraction:
        """Extract every metadata document at `path`."""
        root = path if path.is_dir() else path.parent
        artifacts: dict[str, str] = {}
        diagnostics: list[Diagnostic] = []
        services: list[tuple[Service, str]] = []
        for file in _metadata_files(path):
            artifact = file.relative_to(root).as_posix()
            data = file.read_bytes()
            artifacts[artifact] = digest(data)
            try:
                document, repaired = _parse_lenient(data, artifact)
            except AdapterError as error:
                diagnostics.append(Diagnostic("error", artifact, str(error)))
                continue
            if not is_edmx(document):
                diagnostics.append(Diagnostic("info", artifact, "not OData metadata, skipped"))
                continue
            if repaired:
                diagnostics.append(Diagnostic("info", artifact, repaired))
            services.append((parse_service(document, file.stem), artifact))
        names = _qualified_names(services)
        capabilities: list[Capability] = []
        for (service, artifact), name in zip(services, names, strict=True):
            service.name = name
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
            trigger=Trigger(
                channel=f"OData V{self.service.version.split('.')[0]}", address=operation.request
            ),
            tags=(operation.tag,) if operation.tag else (),
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


def _metadata_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if _is_metadata(path) else []
    if not path.is_dir():
        return []
    return sorted(file for file in path.rglob("*") if file.is_file() and _is_metadata(file))


def _is_metadata(file: Path) -> bool:
    if file.suffix.lower() not in _SUFFIXES and "$metadata" not in file.name:
        return False
    with file.open("rb") as handle:
        head = handle.read(4096)
    return _EDMX_ROOT.search(head) is not None


def _parse_lenient(data: bytes, artifact: str) -> tuple[ET.Element, str | None]:
    """Parse metadata, declaring the SAP namespaces some services use without declaring."""
    try:
        return parse_xml(data, artifact), None
    except AdapterError as error:
        if "unbound prefix" not in str(error):
            raise
        match = _EDMX_ROOT.search(data)
        if match is None:
            raise
        missing = [
            f' xmlns:{prefix}="{uri}"'.encode()
            for prefix, uri in _KNOWN_PREFIXES.items()
            if f"xmlns:{prefix}=".encode() not in data
        ]
        patched = data[: match.end()] + b"".join(missing) + data[match.end() :]
        document = parse_xml(patched, artifact)
        return document, "declared the SAP XML namespaces the document uses without declaring"


def _qualified_names(services: list[tuple[Service, str]]) -> list[str]:
    """Service names, qualified by OData version, or else by path, where documents collide."""
    groups: defaultdict[str, list[int]] = defaultdict(list)
    for index, (service, _) in enumerate(services):
        groups[service.name].append(index)
    names = [service.name for service, _ in services]
    for name, indexes in groups.items():
        if len(indexes) < _COLLISION:
            continue
        versions = [f"v{services[i][0].version.split('.')[0]}" for i in indexes]
        if len(set(versions)) < len(versions):
            versions = distinguishing_names([services[i][1] for i in indexes])
        for index, suffix in zip(indexes, versions, strict=True):
            names[index] = f"{name}.{suffix}"
    return names


__all__ = ["SapODataAdapter"]
