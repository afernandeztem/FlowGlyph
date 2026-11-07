"""Turn requirements written in plain language into a workflow over catalog capabilities.

The language model only proposes a `Plan`. A deterministic resolver then checks every
capability, argument, reference and type against the catalog, so a capability the model invents
or a string bound to an integer is reported, never accepted. Backends for the Claude API, coding
assistants' command lines and OpenAI-compatible servers are in `flowglyph.planner.backends`; any
object implementing `PlanModel` can be used instead.
"""

import re
from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from flowglyph.catalog import Catalog
from flowglyph.errors import FlowGlyphError
from flowglyph.ir import Capability
from flowglyph.planner.model import Plan, PlannedArgument, PlannedInput, PlannedStep
from flowglyph.planner.resolver import PlanReport, resolve
from flowglyph.views import effects_code

DEFAULT_CANDIDATES = 20
_SENTENCE = re.compile(r"(?<=[.!?;:])\s+|\n+")


class PlannerError(FlowGlyphError):
    """The language model could not produce a plan."""


class PlanModel(Protocol):
    """Something that proposes a plan from requirements and candidate capabilities."""

    def propose(self, requirements: str, candidates: Sequence[dict[str, Any]]) -> Plan:
        """Return a plan that uses only the given candidates."""
        ...


@runtime_checkable
class StructuredModel(Protocol):
    """A model that answers a prompt with JSON matching a pydantic model.

    Every built-in backend is one, so planning and enrichment share them.
    """

    def answer[T: BaseModel](self, system: str, prompt: str, shape: type[T]) -> T:
        """Answer `prompt`, following `system`, with a value that validates as `shape`."""
        ...


def candidate_card(capability: Capability) -> dict[str, Any]:
    """What the model sees of a candidate: more than an L0 card, far less than a contract."""
    return {
        "id": capability.id,
        "description": capability.description.split("\n", 1)[0][:200] or capability.title,
        "inputs": [
            {"name": p.name, "type": p.type, "required": p.required} for p in capability.inputs
        ],
        "outputs": [p.name for p in capability.outputs],
        "effects": effects_code(capability.effects) or "none",
        "idempotency": capability.idempotency.mode,
    }


def candidates_for(
    requirements: str, catalog: Catalog, limit: int = DEFAULT_CANDIDATES
) -> list[Capability]:
    """Invocable capabilities relevant to `requirements`.

    The whole text is searched first, then every sentence, so a step mentioned once in a long
    document still brings its capability into the shortlist.
    """
    found: dict[str, Capability] = {}
    queries = [requirements, *(part for part in _SENTENCE.split(requirements) if part.strip())]
    for position, query in enumerate(queries):
        per_query = limit if position == 0 else 3
        for capability in catalog.search(query, limit=per_query, invocable=True):
            found.setdefault(capability.id, capability)
    return list(found.values())[: limit + 10]


def plan(
    requirements: str,
    catalog: Catalog,
    model: PlanModel | None = None,
    *,
    candidates: int = DEFAULT_CANDIDATES,
) -> PlanReport:
    """Plan a workflow that meets `requirements` with capabilities from `catalog`."""
    if model is None:
        from flowglyph.planner.claude import ClaudePlanModel  # noqa: PLC0415

        model = ClaudePlanModel()
    shortlist = candidates_for(requirements, catalog, candidates)
    proposal = model.propose(requirements, [candidate_card(c) for c in shortlist])
    return resolve(proposal, catalog)


__all__ = [
    "Plan",
    "PlanModel",
    "PlanReport",
    "PlannedArgument",
    "PlannedInput",
    "PlannedStep",
    "PlannerError",
    "candidate_card",
    "candidates_for",
    "plan",
    "resolve",
]
