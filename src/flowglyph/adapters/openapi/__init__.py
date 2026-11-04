"""Adapter for OpenAPI 3.0 and 3.1 documents."""

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, ClassVar, cast

import yaml

from flowglyph._internal.hashing import digest
from flowglyph.adapters import Diagnostic, Extraction
from flowglyph.adapters.openapi.refs import RefResolver
from flowglyph.errors import AdapterError
from flowglyph.ir import Capability, Effects, Idempotency, JsonSchema, Security, Source, Tri

HTTP_METHODS = ("get", "put", "post", "delete", "patch", "head", "options", "trace")
_SAFE_METHODS = frozenset({"get", "head", "options", "trace"})
_IDEMPOTENT_METHODS = _SAFE_METHODS | {"put", "delete"}
_IDEMPOTENCY_HEADERS = frozenset({"idempotency-key", "x-idempotency-key"})
_SPEC_SUFFIXES = frozenset({".json", ".yaml", ".yml"})
_MAX_SPEC_BYTES = 50_000_000
_UNSAFE_ID_CHARACTERS = re.compile(r"[^A-Za-z0-9.-]+")
_JSON_MEDIA_TYPE = re.compile(r"^application/([\w.+-]+\+)?json")


class OpenAPIAdapter:
    """Turns every operation of an OpenAPI 3.x document into an invocable capability.

    Effects and idempotency follow HTTP semantics (RFC 9110): safe methods only read, `POST`
    creates without destroying, `PUT` and `PATCH` may overwrite, `DELETE` destroys. `PUT` and
    `DELETE` are idempotent; `POST` and `PATCH` are only retry-safe when the operation accepts
    an `Idempotency-Key` header.
    """

    name: ClassVar[str] = "openapi"
    version: ClassVar[str] = "0.1.0"

    def detect(self, path: Path) -> bool:
        """Whether `path` is an OpenAPI 3.x document or a directory containing one."""
        return bool(_spec_files(path))

    def extract(self, path: Path) -> Extraction:
        """Extract every OpenAPI document at `path`."""
        root = path if path.is_dir() else path.parent
        capabilities: list[Capability] = []
        artifacts: dict[str, str] = {}
        diagnostics: list[Diagnostic] = []
        for file in _spec_files(path):
            artifact = file.relative_to(root).as_posix()
            data = file.read_bytes()
            artifacts[artifact] = digest(data)
            try:
                document = _load(file, data)
            except AdapterError as error:
                diagnostics.append(Diagnostic("error", artifact, str(error)))
                continue
            reader = _DocumentReader(document, artifact, artifacts[artifact])
            capabilities.extend(reader.capabilities())
            diagnostics.extend(reader.diagnostics)
        return Extraction(capabilities=capabilities, artifacts=artifacts, diagnostics=diagnostics)


class _DocumentReader:
    def __init__(self, document: dict[str, Any], artifact: str, source_hash: str) -> None:
        self.document = document
        self.artifact = artifact
        self.source_hash = source_hash
        self.resolver = RefResolver(document)
        self.diagnostics: list[Diagnostic] = []
        info = cast("dict[str, Any]", document.get("info", {}))
        self.api = _slug(str(info.get("title") or Path(artifact).stem))
        self.api_version = str(info["version"]) if "version" in info else None
        self.global_security = cast("list[dict[str, list[str]]]", document.get("security", []))

    def capabilities(self) -> list[Capability]:
        found: list[Capability] = []
        paths = cast("dict[str, dict[str, Any]]", self.document.get("paths") or {})
        for route, item in paths.items():
            path_item = self.resolver.resolve(item)
            shared = cast("list[dict[str, Any]]", path_item.get("parameters", []))
            for method in HTTP_METHODS:
                if method in path_item:
                    operation = cast("dict[str, Any]", path_item[method])
                    found.append(self._capability(route, method, operation, shared))
        self.diagnostics.extend(
            Diagnostic("warning", self.artifact, f"could not resolve {ref}")
            for ref in sorted(self.resolver.unresolved)
        )
        return found

    def _capability(
        self, route: str, method: str, operation: dict[str, Any], shared: list[dict[str, Any]]
    ) -> Capability:
        operation_id = operation.get("operationId")
        if not operation_id:
            operation_id = _slug(f"{method}_{route}")
            self.diagnostics.append(
                Diagnostic(
                    "warning",
                    self.artifact,
                    f"{method.upper()} {route} has no operationId, using {operation_id}",
                )
            )
        input_schema, header_names = self._input_schema(operation, shared)
        tags = [str(tag) for tag in operation.get("tags", [])]
        if operation.get("deprecated"):
            tags.append("deprecated")
        summary = str(operation.get("summary") or "").strip()
        details = str(operation.get("description") or "").strip()
        return Capability(
            id=f"openapi/{self.api}/{operation_id}",
            kind="operation",
            title=str(operation_id),
            description="\n\n".join(part for part in (summary, details) if part),
            category=tags[0] if tags and tags[0] != "deprecated" else "api",
            input_schema=input_schema,
            output_schema=self._output_schema(operation),
            effects=_effects(method),
            idempotency=_idempotency(method, header_names),
            security=Security(scopes=self._scopes(operation)),
            errors=self._errors(operation),
            tags=tuple(tags),
            source=Source(
                provider="openapi",
                artifact=f"{method.upper()} {route}",
                location=f"{self.artifact}#/paths/{_pointer(route)}/{method}",
                source_hash=self.source_hash,
                artifact_version=self.api_version,
            ),
        )

    def _input_schema(
        self, operation: dict[str, Any], shared: list[dict[str, Any]]
    ) -> tuple[JsonSchema, set[str]]:
        parameters: dict[tuple[str, str], dict[str, Any]] = {}
        for raw in [*shared, *cast("list[dict[str, Any]]", operation.get("parameters", []))]:
            parameter = self.resolver.resolve(raw)
            parameters[str(parameter.get("name")), str(parameter.get("in"))] = parameter
        names = [name for name, _ in parameters]
        properties: dict[str, JsonSchema] = {}
        required: list[str] = []
        for (name, location), parameter in parameters.items():
            key = name if names.count(name) == 1 else f"{location}.{name}"
            schema = dict(self.resolver.inline(parameter.get("schema", {})))
            schema["x-in"] = location
            if parameter.get("description"):
                schema["description"] = str(parameter["description"])
            properties[key] = schema
            if parameter.get("required") or location == "path":
                required.append(key)
        body = self._request_body(operation)
        if body is not None:
            schema, body_required = body
            properties["body"] = {**schema, "x-in": "body"}
            if body_required:
                required.append("body")
        header_names = {name for name, location in parameters if location == "header"}
        input_schema: JsonSchema = {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }
        return input_schema, header_names

    def _request_body(self, operation: dict[str, Any]) -> tuple[JsonSchema, bool] | None:
        if "requestBody" not in operation:
            return None
        body = self.resolver.resolve(operation["requestBody"])
        schema = _json_content_schema(cast("dict[str, Any]", body.get("content", {})))
        resolved: JsonSchema = self.resolver.inline(schema) if schema is not None else {}
        if body.get("description") and "description" not in resolved:
            resolved = {**resolved, "description": str(body["description"])}
        return resolved, bool(body.get("required"))

    def _output_schema(self, operation: dict[str, Any]) -> JsonSchema:
        responses = cast("dict[str, Any]", operation.get("responses", {}))
        for status in sorted(code for code in responses if str(code).startswith("2")):
            response = self.resolver.resolve(responses[status])
            schema = _json_content_schema(cast("dict[str, Any]", response.get("content", {})))
            if schema is not None:
                body = self.resolver.inline(schema)
                return {"type": "object", "properties": {"body": body}}
        return {"type": "object", "properties": {}}

    def _scopes(self, operation: dict[str, Any]) -> tuple[str, ...]:
        requirements = cast(
            "list[dict[str, list[str]]]", operation.get("security", self.global_security)
        )
        scopes = {
            scope
            for requirement in requirements
            for values in requirement.values()
            for scope in values
        }
        return tuple(sorted(scopes))

    def _errors(self, operation: dict[str, Any]) -> tuple[str, ...]:
        responses = cast("dict[str, Any]", operation.get("responses", {}))
        errors: list[str] = []
        for status in sorted(str(code) for code in responses):
            if status[0] in "45":
                response = self.resolver.resolve(responses[status])
                description = str(response.get("description", "")).strip()
                errors.append(f"{status}: {description}" if description else status)
        return tuple(errors)


def _effects(method: str) -> Effects:
    if method in _SAFE_METHODS:
        return Effects(reads=Tri.YES, mutates_state=Tri.NO, destructive=Tri.NO, external=Tri.YES)
    if method == "delete":
        return Effects(reads=Tri.NO, mutates_state=Tri.YES, destructive=Tri.YES, external=Tri.YES)
    if method == "post":
        return Effects(
            reads=Tri.UNKNOWN, mutates_state=Tri.YES, destructive=Tri.NO, external=Tri.YES
        )
    return Effects(
        reads=Tri.UNKNOWN, mutates_state=Tri.YES, destructive=Tri.UNKNOWN, external=Tri.YES
    )


def _idempotency(method: str, header_names: set[str]) -> Idempotency:
    if method in _IDEMPOTENT_METHODS:
        return Idempotency(mode="natural", confidence=0.8)
    key_headers = sorted(name for name in header_names if name.lower() in _IDEMPOTENCY_HEADERS)
    if key_headers:
        return Idempotency(mode="key", key_fields=tuple(key_headers), confidence=0.9)
    return Idempotency(mode="none", confidence=0.7)


def _json_content_schema(content: Mapping[str, Any]) -> JsonSchema | None:
    for media_type, media in content.items():
        if _JSON_MEDIA_TYPE.match(media_type) and isinstance(media, Mapping):
            return cast("JsonSchema", cast("Mapping[str, Any]", media).get("schema", {}))
    return None


def _spec_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if _is_spec(path) else []
    if not path.is_dir():
        return []
    return sorted(file for file in path.rglob("*") if file.is_file() and _is_spec(file))


def _is_spec(file: Path) -> bool:
    if file.suffix.lower() not in _SPEC_SUFFIXES or file.stat().st_size > _MAX_SPEC_BYTES:
        return False
    with file.open("rb") as handle:
        head = handle.read(2048)
    return re.search(rb"""["']?openapi["']?\s*:\s*["']?3\.""", head) is not None


def _load(file: Path, data: bytes) -> dict[str, Any]:
    try:
        if file.suffix.lower() == ".json":
            document: object = json.loads(data)
        else:
            document = yaml.safe_load(data)
    except (json.JSONDecodeError, yaml.YAMLError) as error:
        raise AdapterError(f"{file}: {error}") from error
    if not isinstance(document, dict):
        raise AdapterError(f"{file}: not an OpenAPI document")
    return cast("dict[str, Any]", document)


def _slug(text: str) -> str:
    return _UNSAFE_ID_CHARACTERS.sub("_", text).strip("_")


def _pointer(route: str) -> str:
    return route.replace("~", "~0").replace("/", "~1")


__all__ = ["OpenAPIAdapter"]
