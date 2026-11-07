"""Running SAP OData operations, V2 and V4, as SAP Gateway and S/4HANA expect them.

Requests that change data first fetch a CSRF token, as SAP requires, and retry once with a fresh
one when the server says it expired. Updates and deletes send `If-Match: *`: the agent works on
the latest version of the record, which is what a single call means.
"""

import urllib.parse
from dataclasses import dataclass, field
from http import HTTPStatus
from typing import Any, ClassVar, Literal, cast

from flowglyph.errors import ExecutionError
from flowglyph.gateway.executors._http import HttpClient, Response
from flowglyph.gateway.executors.auth import Auth
from flowglyph.ir import Capability

type Version = Literal[2, 4]
_V2: Version = 2
type Shape = Literal["collection", "entity", "call"]

_QUERY_OPTIONS = ("$filter", "$select", "$orderby", "$top", "$skip", "$expand", "$search")
_URL_SAFE = "',="
_V2_SUFFIX = {"Edm.Decimal": "M", "Edm.Int64": "L", "Edm.Double": "d", "Edm.Single": "f"}
_V2_PREFIX = {
    "Edm.Guid": "guid",
    "Edm.DateTime": "datetime",
    "Edm.DateTimeOffset": "datetimeoffset",
    "Edm.Time": "time",
    "Edm.Binary": "binary",
}
_V4_PREFIX = {"Edm.Binary": "binary", "Edm.Duration": "duration"}


@dataclass
class _Request:
    """One OData request, and the shape of the answer to expect."""

    method: str
    path: str
    shape: Shape
    query: list[tuple[str, str]] = field(default_factory=list[tuple[str, str]])
    headers: dict[str, str] = field(default_factory=dict[str, str])
    body: Any = None


class ODataExecutor:
    """Calls the OData service whose root is `service_url`."""

    name: ClassVar[str] = "odata"

    def __init__(self, service_url: str, auth: Auth, *, timeout_seconds: float = 60.0) -> None:
        """Call the service at `service_url`, authenticating with `auth`."""
        self.service_url = service_url.rstrip("/")
        self.auth = auth
        self.client = HttpClient(timeout_seconds=timeout_seconds)
        self._csrf_token: str | None = None

    def execute(self, capability: Capability, arguments: dict[str, Any]) -> dict[str, Any]:
        """Send the request the operation describes and return its result.

        Raises:
            ExecutionError: If the capability is not an OData operation or the service answers
                with an error.
        """
        version, method, target = _operation(capability)
        request = _build(version, method, target, arguments, capability.input_schema)
        response = self._send(request)
        return _result(response.json(), version, request.shape)

    def _send(self, request: _Request) -> Response:
        url = f"{self.service_url}/{request.path}"
        changes = request.method != "GET"
        for retrying in (False, True):
            headers = {**request.headers, **self.auth.headers(self.client)}
            if changes:
                headers["X-CSRF-Token"] = self._token(refresh=retrying)
            response = self.client.request(
                request.method, url, headers=headers, query=request.query, json_body=request.body
            )
            if not (changes and _token_expired(response)):
                break
        if not response.ok:
            raise ExecutionError(
                f"{request.method} {request.path} answered {response.status}: {_message(response)}"
            )
        return response

    def _token(self, *, refresh: bool) -> str:
        if self._csrf_token is None or refresh:
            response = self.client.request(
                "GET",
                f"{self.service_url}/",
                headers={"X-CSRF-Token": "Fetch", **self.auth.headers(self.client)},
            )
            token = response.header("X-CSRF-Token")
            if not response.ok or not token:
                raise ExecutionError(
                    f"could not fetch a CSRF token from {self.service_url} ({response.status})"
                )
            self._csrf_token = token
        return self._csrf_token


def _token_expired(response: Response) -> bool:
    required = (response.header("X-CSRF-Token") or "").lower() == "required"
    return response.status == HTTPStatus.FORBIDDEN and required


def _operation(capability: Capability) -> tuple[Version, str, str]:
    trigger = capability.trigger
    channel = trigger.channel or "" if trigger else ""
    if trigger is None or not channel.startswith("OData V") or not trigger.address:
        raise ExecutionError(f"{capability.id} is not an OData operation")
    method, _, target = trigger.address.partition(" ")
    return (_V2 if channel == "OData V2" else 4), method.upper(), target


def _build(
    version: Version, method: str, target: str, arguments: dict[str, Any], schema: dict[str, Any]
) -> _Request:
    """Where each argument goes: `Set`, `Set(key)`, `Set(key)/Ns.action()` or `Operation()`."""
    properties: dict[str, dict[str, Any]] = schema.get("properties", {})
    edm = {name: str(spec.get("x-edm-type", "Edm.String")) for name, spec in properties.items()}
    is_call = target.endswith("()")
    head, _, action = target.removesuffix("()").partition("/")
    entity_set = head.removesuffix("(key)")
    has_key = head.endswith("(key)")
    keys = {
        name: value
        for name, value in arguments.items()
        if properties.get(name, {}).get("x-odata-key")
    }
    parameters = {
        name: value
        for name, value in arguments.items()
        if name not in keys and name != "body" and name not in _QUERY_OPTIONS
    }
    path = entity_set
    if has_key:
        path += _predicate(
            {name: _literal(value, edm[name], version) for name, value in keys.items()}
        )
    if action:
        path += "/" + action
    reads_many = method == "GET" and not has_key
    shape: Shape = "call" if is_call else "collection" if reads_many else "entity"
    request = _Request(method, path, shape)
    if is_call:
        _place_parameters(request, parameters, edm, version)
    else:
        request.body = arguments.get("body")
        if request.shape == "collection":
            request.query = [
                (name, str(arguments[name])) for name in _QUERY_OPTIONS if name in arguments
            ]
    if version == _V2:
        request.query.append(("$format", "json"))
    if method in {"PATCH", "DELETE"}:
        request.headers["If-Match"] = "*"
    if method == "PATCH" and version == _V2:
        # OData V2 names a partial update MERGE; SAP Gateway accepts it tunnelled in POST.
        request.method, request.headers["X-HTTP-Method"] = "POST", "MERGE"
    return request


def _place_parameters(
    request: _Request, parameters: dict[str, Any], edm: dict[str, str], version: Version
) -> None:
    """V2 passes parameters in the query, V4 functions in the URL and V4 actions in the body."""
    literals = {
        name: _literal(value, edm.get(name, "Edm.String"), version)
        for name, value in parameters.items()
    }
    if version == _V2:
        request.query = list(literals.items())
    elif request.method == "GET":
        request.path += _predicate(literals, named=True)
    else:
        request.body = parameters


def _predicate(literals: dict[str, str], *, named: bool = False) -> str:
    if not literals:
        raise ExecutionError("the entity key is missing")
    if len(literals) == 1 and not named:
        inner = next(iter(literals.values()))
    else:
        inner = ",".join(f"{name}={literal}" for name, literal in literals.items())
    return f"({urllib.parse.quote(inner, safe=_URL_SAFE)})"


def _literal(value: Any, edm_type: str, version: Version) -> str:
    """`value` written as an OData URL literal of `edm_type`."""
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    quoted = "'" + text.replace("'", "''") + "'"
    if version == _V2:
        if edm_type in _V2_PREFIX:
            return _V2_PREFIX[edm_type] + quoted
        if edm_type in _V2_SUFFIX:
            return text + _V2_SUFFIX[edm_type]
        return quoted if edm_type == "Edm.String" or isinstance(value, str) else text
    if edm_type in _V4_PREFIX:
        return _V4_PREFIX[edm_type] + quoted
    return quoted if edm_type == "Edm.String" else text


def _result(payload: Any, version: Version, shape: Shape) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {} if payload is None else {"value": payload}
    data = cast("dict[str, Any]", payload)
    if version == _V2 and "d" in data:
        inner: Any = data["d"]
        if isinstance(inner, dict):
            inner_data = cast("dict[str, Any]", inner)
            data = {"value": inner_data["results"]} if "results" in inner_data else inner_data
        else:
            data = {"value": inner}
    cleaned = _strip_annotations(data)
    if shape == "collection":
        return {"value": cleaned.get("value", [])}
    if shape == "call" and not (len(cleaned) == 1 and "value" in cleaned):
        return {"value": cleaned}
    return cleaned


def _strip_annotations(data: dict[str, Any]) -> dict[str, Any]:
    """Drop `__metadata` (V2) and `@odata.` control information (V4)."""
    cleaned: dict[str, Any] = {}
    for name, value in data.items():
        if name == "__metadata" or name.startswith(("@odata.", "odata.")):
            continue
        cleaned[name] = _clean(value)
    return cleaned


def _clean(value: Any) -> Any:
    if isinstance(value, dict):
        return _strip_annotations(cast("dict[str, Any]", value))
    if isinstance(value, list):
        return [_clean(item) for item in cast("list[Any]", value)]
    return value


def _message(response: Response) -> str:
    """SAP's own error message, V2 or V4, or the start of the body."""
    payload = response.json()
    if isinstance(payload, dict):
        error: Any = cast("dict[str, Any]", payload).get("error")
        message: Any = (
            cast("dict[str, Any]", error).get("message") if isinstance(error, dict) else None
        )
        if isinstance(message, dict):
            message = cast("dict[str, Any]", message).get("value")
        if message:
            return str(message)
    return response.snippet() or "no body"
