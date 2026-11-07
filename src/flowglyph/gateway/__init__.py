"""Run catalog capabilities for agents, with policy, idempotency and an audit trail.

Requires `pip install 'flowglyph[mcp]'`. The `Gateway` class works without MCP; `serve_stdio`
exposes it as an MCP server.
"""

from flowglyph.errors import FlowGlyphError

try:
    from flowglyph.gateway.service import Gateway, RunResult
except ModuleNotFoundError as error:
    if error.name != "jsonschema":
        raise
    raise FlowGlyphError(
        "the gateway needs extra packages: pip install 'flowglyph[mcp]'"
    ) from error

from flowglyph.gateway.executors import DryRunExecutor, Executor
from flowglyph.gateway.ledger import Ledger
from flowglyph.gateway.policy import DEFAULT_POLICY, Policy, Rule

__all__ = [
    "DEFAULT_POLICY",
    "DryRunExecutor",
    "Executor",
    "Gateway",
    "Ledger",
    "Policy",
    "Rule",
    "RunResult",
]
