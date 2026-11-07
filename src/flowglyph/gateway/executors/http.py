"""Running OpenAPI operations: each argument goes where the API document says it belongs."""

import json
import urllib.parse
from typing import Any, ClassVar, cast

from flowglyph.errors import ExecutionError
from flowglyph.gateway.executors._http import HttpClient
from flowglyph.gateway.executors.auth import Auth
from flowglyph.ir import Capability


class HttpExecutor:
    """Calls an HTTP API at `base_url` for capabilities extracted from its OpenAPI document."""

    name: ClassVar[str] = "http"

    def __init__(self, base_url: str, auth: Auth, *, timeout_seconds: float = 60.0) -> None:
        """Call the API at `base_url`, authenticating with `auth`."""
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.client = HttpClient(timeout_seconds=timeout_seconds)

    def execute(self, capability: Capability, arguments: dict[str, Any]) -> dict[str, Any]:
        """Send the request the operation describes and return its status and body.

        Raises:
            ExecutionError: If the capability is not an HTTP operation or the API answers with
                an error status.
        """
        method, route = _operation(capability)
        path: dict[str, str] = {}
        query: list[tuple[str, str]] = []
        headers: dict[str, str] = {}
        cookies: list[str] = []
        body: Any = None
        properties: dict[str, Any] = capability.input_schema.get("properties", {})
        for key, value in arguments.items():
            spec: dict[str, Any] = properties.get(key, {})
            location = str(spec.get("x-in", "query"))
            name = key.removeprefix(f"{location}.")
            if location == "body":
                body = value
            elif location == "path":
                path[name] = urllib.parse.quote(_text(value), safe="")
            elif location == "header":
                headers[name] = _text(value)
            elif location == "cookie":
                cookies.append(f"{name}={urllib.parse.quote(_text(value))}")
            else:
                values = cast("list[Any]", value) if isinstance(value, list) else [value]
                query.extend((name, _text(each)) for each in values)
        if cookies:
            headers["Cookie"] = "; ".join(cookies)
        url = self.base_url + _fill(route, path)
        response = self.client.request(
            method,
            url,
            headers={**headers, **self.auth.headers(self.client)},
            query=query,
            json_body=body,
        )
        if not response.ok:
            raise ExecutionError(
                f"{method} {route} answered {response.status}: {response.snippet() or 'no body'}"
            )
        return {"status": response.status, "body": response.json()}


def _operation(capability: Capability) -> tuple[str, str]:
    trigger = capability.trigger
    if trigger is None or trigger.channel != "HTTP" or not trigger.address:
        raise ExecutionError(f"{capability.id} is not an HTTP operation")
    method, _, route = trigger.address.partition(" ")
    return method.upper(), route


def _fill(route: str, path: dict[str, str]) -> str:
    filled = route
    for name, value in path.items():
        filled = filled.replace("{" + name + "}", value)
    if "{" in filled:
        raise ExecutionError(f"missing path parameters for {route}")
    return filled


def _text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict | list):
        return json.dumps(value, separators=(",", ":"))
    return str(value)
