"""What n8n nodes do to the world, from their type and the operation they are set to."""

import re
from typing import Any

from flowglyph.ir import Effects, Tri

_PREFIXES = ("n8n-nodes-base.", "@n8n/n8n-nodes-langchain.")
TRIGGERS = frozenset(
    {"webhook", "formTrigger", "scheduleTrigger", "cron", "manualTrigger", "executeWorkflowTrigger"}
)
DECISIONS = frozenset({"if", "switch", "filter"})
CALL = "executeWorkflow"
_PURE = frozenset(
    {
        "set",
        "noOp",
        "merge",
        "splitOut",
        "splitInBatches",
        "aggregate",
        "sort",
        "limit",
        "removeDuplicates",
        "dateTime",
        "crypto",
        "html",
        "xml",
        "markdown",
        "itemLists",
        "renameKeys",
        "compareDatasets",
        "summarize",
        "wait",
        "respondToWebhook",
        "stopAndError",
        "executionData",
        "stickyNote",
        "if",
        "switch",
        "filter",
        "executeWorkflow",
    }
)
_ARBITRARY = frozenset({"code", "function", "functionItem", "executeCommand", "ssh"})
_READ_WORDS = re.compile(r"^(get|getall|list|search|lookup|read|download|select|find|query)", re.I)
_DELETE_WORDS = re.compile(r"^(delete|remove|clear|purge|drop|cancel|archive)", re.I)
_WRITE_WORDS = re.compile(
    r"^(create|update|upsert|append|send|post|add|insert|upload|reply|move|copy|share|invite|"
    r"set|patch|put|publish|execute)",
    re.I,
)

READ = Effects(reads=Tri.YES, mutates_state=Tri.NO, destructive=Tri.NO, external=Tri.YES)
WRITE = Effects(reads=Tri.NO, mutates_state=Tri.YES, destructive=Tri.NO, external=Tri.YES)
DELETE = Effects(reads=Tri.NO, mutates_state=Tri.YES, destructive=Tri.YES, external=Tri.YES)
UNKNOWN_EXTERNAL = Effects(
    reads=Tri.UNKNOWN, mutates_state=Tri.UNKNOWN, destructive=Tri.UNKNOWN, external=Tri.YES
)
UNKNOWN = Effects(
    reads=Tri.UNKNOWN, mutates_state=Tri.UNKNOWN, destructive=Tri.UNKNOWN, external=Tri.UNKNOWN
)
_METHODS = {"GET": READ, "HEAD": READ, "OPTIONS": READ, "DELETE": DELETE}


def short_type(node: dict[str, Any]) -> str:
    """`n8n-nodes-base.slack` becomes `slack`."""
    node_type = str(node.get("type", ""))
    for prefix in _PREFIXES:
        if node_type.startswith(prefix):
            return node_type.removeprefix(prefix)
    return node_type


def is_trigger(node: dict[str, Any]) -> bool:
    """Whether the node starts the workflow rather than running inside it."""
    kind = short_type(node)
    return kind in TRIGGERS or kind.endswith("Trigger")


def node_effects(node: dict[str, Any]) -> Effects | None:
    """Effects of one node; None for nodes that only shape data, route or start the workflow."""
    kind = short_type(node)
    if node.get("disabled") or kind in _PURE or is_trigger(node):
        return None
    parameters: dict[str, Any] = node.get("parameters") or {}
    if kind in _ARBITRARY:
        effects = UNKNOWN
    elif kind == "httpRequest":
        method = str(parameters.get("method") or parameters.get("requestMethod") or "GET")
        effects = _METHODS.get(method.upper(), WRITE)
    elif str(node.get("type", "")).startswith("@n8n/"):
        effects = UNKNOWN_EXTERNAL
    else:
        effects = operation_effects(str(parameters.get("operation") or ""))
    return effects


def operation_effects(operation: str) -> Effects:
    """Effects of an app node's operation, from its verb: `getAll` reads, `delete` destroys."""
    for words, effects in ((_DELETE_WORDS, DELETE), (_READ_WORDS, READ), (_WRITE_WORDS, WRITE)):
        if words.match(operation):
            return effects
    return UNKNOWN_EXTERNAL
