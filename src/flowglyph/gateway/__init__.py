"""Run catalog capabilities for agents, with policy, idempotency and an audit trail.

Requires `pip install 'flowglyph[mcp]'`. The `Gateway` class works without MCP; `serve_stdio`
exposes it as an MCP server.
"""

from flowglyph.gateway.executors import DryRunExecutor, Executor
from flowglyph.gateway.ledger import Ledger
from flowglyph.gateway.policy import DEFAULT_POLICY, Policy, Rule
from flowglyph.gateway.service import Gateway, RunResult

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
