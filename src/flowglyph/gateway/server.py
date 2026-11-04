import hashlib
import json
import re
from typing import Any, Literal

import mcp_types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from flowglyph._internal.markdown import card_filename, render_index
from flowglyph._internal.text import first_line
from flowglyph.errors import CatalogError
from flowglyph.gateway.service import Gateway
from flowglyph.ir import Capability

type Exposure = Literal["auto", "all", "meta"]

AUTO_EXPOSE_LIMIT = 40
KEY_ARGUMENT = "_idempotency_key"
_TOOL_NAME_UNSAFE = re.compile(r"[^A-Za-z0-9_-]+")
_MAX_TOOL_NAME = 64

INSTRUCTIONS = """\
This server exposes enterprise automations as capabilities.
1. Call catalog_search with what you want to achieve. You get compact L0 cards:
   e = effects (R read, W write, D destructive, X external; lower case = unknown),
   i = idempotency (natural = safe to retry, key/none = pass an idempotency key).
2. Call catalog_card on the few candidates you consider, to read inputs and retry advice.
3. Run one capability, filling only the arguments in its schema. For anything with side
   effects pass a stable business id as the idempotency key, so a retry never runs twice.
A result with status approval_required must be approved by a person before it runs.
"""

_META_TOOLS = [
    types.Tool(
        name="catalog_search",
        description="Find capabilities by what they do. Returns L0 cards, a few dozen bytes each.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What you want to achieve."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        annotations=types.ToolAnnotations(read_only_hint=True, open_world_hint=False),
    ),
    types.Tool(
        name="catalog_card",
        description="Read the L1 card of one capability: inputs, outputs, steps, retry advice.",
        input_schema={
            "type": "object",
            "properties": {"capability": {"type": "string", "description": "Capability id."}},
            "required": ["capability"],
            "additionalProperties": False,
        },
        annotations=types.ToolAnnotations(read_only_hint=True, open_world_hint=False),
    ),
    types.Tool(
        name="catalog_contract",
        description="Read the full L2 contract of one capability: schemas, effects, idempotency.",
        input_schema={
            "type": "object",
            "properties": {"capability": {"type": "string"}},
            "required": ["capability"],
            "additionalProperties": False,
        },
        annotations=types.ToolAnnotations(read_only_hint=True, open_world_hint=False),
    ),
    types.Tool(
        name="run_capability",
        description=(
            "Run a capability by id. Pass idempotency_key with a stable business id for "
            "anything with side effects; repeating a call with the same key returns the "
            "first result instead of running again."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "capability": {"type": "string"},
                "arguments": {"type": "object"},
                "idempotency_key": {"type": "string"},
            },
            "required": ["capability", "arguments"],
            "additionalProperties": False,
        },
        annotations=types.ToolAnnotations(
            read_only_hint=False, destructive_hint=True, idempotent_hint=True
        ),
    ),
    types.Tool(
        name="run_status",
        description="Status of an earlier run, by the idempotency key it returned.",
        input_schema={
            "type": "object",
            "properties": {"idempotency_key": {"type": "string"}},
            "required": ["idempotency_key"],
            "additionalProperties": False,
        },
        annotations=types.ToolAnnotations(read_only_hint=True, open_world_hint=False),
    ),
]


def tool_name(capability: Capability) -> str:
    """A valid MCP tool name for `capability`, stable across restarts."""
    name = _TOOL_NAME_UNSAFE.sub("_", capability.id).strip("_")
    if len(name) <= _MAX_TOOL_NAME:
        return name
    suffix = hashlib.sha256(capability.id.encode()).hexdigest()[:8]
    return f"{name[: _MAX_TOOL_NAME - 9]}_{suffix}"


def capability_tool(capability: Capability) -> types.Tool:
    """The MCP tool that runs `capability` directly."""
    schema = json.loads(json.dumps(capability.input_schema))
    if capability.effects.has_side_effects:
        schema.setdefault("properties", {})[KEY_ARGUMENT] = {
            "type": "string",
            "description": "Stable business id; a retry with the same key never runs twice.",
        }
    summary = first_line(capability.description, 300) or capability.title
    hints = (
        f"effects {capability.effects.code() or 'none'}, idempotency {capability.idempotency.mode}"
    )
    return types.Tool(
        name=tool_name(capability),
        title=capability.title,
        description=f"{summary}\n\n{capability.id} v{capability.version} ({hints}).",
        input_schema=schema,
        annotations=types.ToolAnnotations(
            read_only_hint=not capability.effects.has_side_effects,
            destructive_hint=capability.effects.destructive.possible,
            idempotent_hint=True,
            open_world_hint=capability.effects.external.possible,
        ),
    )


def build_server(gateway: Gateway, expose: Exposure = "auto") -> Server[Any]:
    """An MCP server that routes every tool call through `gateway`."""

    def direct_tools() -> dict[str, Capability]:
        invocable = [c for c in gateway.catalog if c.invocable]
        if expose == "meta" or (expose == "auto" and len(invocable) > AUTO_EXPOSE_LIMIT):
            return {}
        return {tool_name(capability): capability for capability in invocable}

    async def list_tools(
        _context: Any, _params: types.PaginatedRequestParams | None
    ) -> types.ListToolsResult:
        tools = [*_META_TOOLS, *map(capability_tool, direct_tools().values())]
        return types.ListToolsResult(tools=tools)

    async def call_tool(_context: Any, params: types.CallToolRequestParams) -> types.CallToolResult:
        arguments = dict(params.arguments or {})
        try:
            return _dispatch(gateway, params.name, arguments, direct_tools())
        except CatalogError as error:
            return _json({"error": str(error), "hint": "use catalog_search"}, error=True)

    async def list_resources(
        _context: Any, _params: types.PaginatedRequestParams | None
    ) -> types.ListResourcesResult:
        resources = [
            types.Resource(
                uri="flowglyph://index",
                name="index",
                mime_type="text/markdown",
                description="Every capability in the catalog at a glance.",
            )
        ]
        resources.extend(
            types.Resource(
                uri=f"flowglyph://cards/{card_filename(capability).removesuffix('.md')}",
                name=capability.id,
                mime_type="text/markdown",
            )
            for capability in gateway.catalog
        )
        return types.ListResourcesResult(resources=resources)

    async def read_resource(
        _context: Any, params: types.ReadResourceRequestParams
    ) -> types.ReadResourceResult:
        uri = str(params.uri)
        catalog = gateway.catalog
        if uri == "flowglyph://index":
            text = render_index(catalog)
        else:
            stem = uri.removeprefix("flowglyph://cards/")
            matches = [c for c in catalog if card_filename(c).removesuffix(".md") == stem]
            if not matches:
                raise CatalogError(f"unknown resource {uri}")
            text = gateway.describe(matches[0].id)
        return types.ReadResourceResult(
            contents=[types.TextResourceContents(uri=uri, mime_type="text/markdown", text=text)]
        )

    return Server(
        "flowglyph",
        instructions=INSTRUCTIONS,
        on_list_tools=list_tools,
        on_call_tool=call_tool,
        on_list_resources=list_resources,
        on_read_resource=read_resource,
    )


def _dispatch(
    gateway: Gateway, name: str, arguments: dict[str, Any], direct: dict[str, Capability]
) -> types.CallToolResult:
    read = _read_tool(gateway, name, arguments)
    if read is not None:
        return read
    if name == "run_capability":
        result = gateway.run(
            str(arguments["capability"]),
            dict(arguments.get("arguments") or {}),
            idempotency_key=arguments.get("idempotency_key"),
        )
    elif name in direct:
        key = arguments.pop(KEY_ARGUMENT, None)
        result = gateway.run(direct[name].id, arguments, idempotency_key=key)
    else:
        return _json({"error": f"unknown tool {name}"}, error=True)
    failed = result.status in {"invalid", "denied", "failed", "conflict"}
    return _json(result.to_dict(), error=failed)


def _read_tool(
    gateway: Gateway, name: str, arguments: dict[str, Any]
) -> types.CallToolResult | None:
    if name == "catalog_search":
        cards = gateway.search(str(arguments["query"]), limit=int(arguments.get("limit", 20)))
        return _json({"results": cards})
    if name == "catalog_card":
        text = gateway.describe(str(arguments["capability"]))
        return types.CallToolResult(content=[types.TextContent(type="text", text=text)])
    if name == "catalog_contract":
        return _json(gateway.contract(str(arguments["capability"])))
    if name == "run_status":
        run = gateway.status(str(arguments["idempotency_key"]))
        if run is None:
            return _json({"error": "unknown idempotency key"}, error=True)
        return _json({"status": run.status, "capability": run.capability, "result": run.result})
    return None


def _json(payload: dict[str, Any], *, error: bool = False) -> types.CallToolResult:
    text = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=text)],
        structured_content=payload,
        is_error=error,
    )


async def serve_stdio(gateway: Gateway, expose: Exposure = "auto") -> None:
    """Serve `gateway` over standard input and output until the client disconnects."""
    server = build_server(gateway, expose)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
