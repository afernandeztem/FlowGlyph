"""Descriptions and business semantics written by a language model where sources say nothing.

Adapters only record what a source states. Many sources state little: a template's placeholder
description, an n8n workflow with no notes, a BPMN process without documentation. Enrichment
asks a model, once, to describe those capabilities from what the catalog already knows about
them, and marks every field it writes in `Capability.generated`.

Answers are cached in `flowglyph.enrichment.json` next to the catalog, keyed by capability and
source hash: extracting again reuses them without calling the model, and only capabilities
whose source changed are asked again. Idempotency is never enriched; retry safety is decided
by sources and people.
"""

import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field

from flowglyph.catalog import Catalog, Lock
from flowglyph.catalog.versioning import assign_versions
from flowglyph.ir import Capability, Semantics
from flowglyph.planner import StructuredModel
from flowglyph.views import effects_code

ENRICHMENT_FILE = "flowglyph.enrichment.json"
PROMPT_VERSION = 1
BATCH_SIZE = 20
_MIN_WORDS = 3

SYSTEM_PROMPT = """\
You document enterprise automations for the people and agents who use them.

For every capability you receive, write:
- summary: one sentence, at most 200 characters, saying what it does for the business. Start
  with a verb ("Books a supplier invoice in the ERP"). Use only the facts given: its title,
  description, inputs, outputs, effects and steps. When they do not say enough, write what they
  do say and nothing more.
- verb, entity, domain: the business action (book, approve, notify), the business object it acts
  on (invoice, supplier, order), and the area (finance, procurement, sales). Use "unknown" when
  the facts do not say.

Answer for every capability, with its id copied exactly, and for no other.
"""


class Description(BaseModel):
    """What the model writes for one capability."""

    model_config = ConfigDict(extra="forbid")

    id: str
    summary: str = Field(description="one sentence, at most 200 characters")
    verb: str
    entity: str
    domain: str


class Descriptions(BaseModel):
    """The model's answer for one batch."""

    model_config = ConfigDict(extra="forbid")

    capabilities: list[Description]


@dataclass
class Cache:
    """Answers already given, by capability id, valid while the source hash is the same."""

    entries: dict[str, dict[str, str]] = field(default_factory=dict[str, dict[str, str]])

    @classmethod
    def load(cls, path: str | Path) -> "Cache":
        """The cache at `path`, or an empty one when there is none or it is from another prompt."""
        file = Path(path)
        if not file.is_file():
            return cls()
        try:
            document = cast("dict[str, Any]", json.loads(file.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            return cls()
        if document.get("prompt_version") != PROMPT_VERSION:
            return cls()
        return cls(cast("dict[str, dict[str, str]]", document.get("capabilities") or {}))

    def save(self, path: str | Path) -> None:
        """Write the cache with stable formatting, so it diffs cleanly."""
        document = {"prompt_version": PROMPT_VERSION, "capabilities": self.entries}
        text = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False)
        Path(path).write_text(text + "\n", encoding="utf-8", newline="\n")

    def get(self, capability: Capability) -> dict[str, str] | None:
        """The cached answer for `capability`, if its source has not changed since."""
        entry = self.entries.get(capability.id)
        if entry is None or entry.get("source_hash") != capability.source.source_hash:
            return None
        return entry

    def put(self, capability: Capability, answer: Description, model: str) -> None:
        """Remember `answer` for `capability` as it is now."""
        self.entries[capability.id] = {
            "source_hash": capability.source.source_hash,
            "model": model,
            "summary": answer.summary.strip(),
            "verb": answer.verb.strip(),
            "entity": answer.entity.strip(),
            "domain": answer.domain.strip(),
        }


@dataclass(frozen=True)
class Result:
    """What an enrichment pass did."""

    catalog: Catalog
    asked: tuple[str, ...]
    reused: tuple[str, ...]
    unanswered: tuple[str, ...]


def needs_enrichment(capability: Capability) -> bool:
    """Whether the source left this capability without a description or semantics.

    Activity types are left out: their vendor documents them, and there are many.
    """
    if capability.kind == "activity":
        return False
    return _needs_description(capability) or _needs_semantics(capability)


def refiner(cache: Cache) -> Callable[[list[Capability]], list[Capability]]:
    """A `refine` step for `flowglyph.extract` that applies the cached answers."""

    def refine(capabilities: list[Capability]) -> list[Capability]:
        return [_enriched(capability, cache.get(capability)) for capability in capabilities]

    return refine


def enrich(
    catalog: Catalog,
    model: StructuredModel,
    cache: Cache,
    *,
    model_name: str = "model",
    limit: int | None = None,
) -> Result:
    """Describe what the sources left undescribed, asking `model` only what `cache` lacks.

    `limit` caps how many capabilities are sent to the model in this pass.
    """
    pending = [c for c in catalog if needs_enrichment(c) and cache.get(c) is None]
    pending.sort(key=lambda capability: capability.id)
    if limit is not None:
        pending = pending[:limit]
    answered: set[str] = set()
    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start : start + BATCH_SIZE]
        wanted = {capability.id: capability for capability in batch}
        reply = model.answer(SYSTEM_PROMPT, _request(batch, catalog), Descriptions)
        for answer in reply.capabilities:
            capability = wanted.get(answer.id)
            if capability is not None and answer.summary.strip():
                cache.put(capability, answer, model_name)
                answered.add(answer.id)
    asked = tuple(capability.id for capability in pending)
    reused = tuple(
        c.id for c in catalog if c.id not in answered and needs_enrichment(c) and cache.get(c)
    )
    return Result(
        catalog=apply(catalog, cache),
        asked=asked,
        reused=reused,
        unanswered=tuple(capability_id for capability_id in asked if capability_id not in answered),
    )


def apply(catalog: Catalog, cache: Cache) -> Catalog:
    """`catalog` with every cached answer that still matches its source, versioned again.

    Descriptions change documentation, so a capability enriched for the first time gets a patch
    version; reapplying the same answers after an extraction changes nothing.
    """
    enriched = refiner(cache)(list(catalog))
    if all(new is old for new, old in zip(enriched, catalog, strict=True)):
        return catalog
    versioned, entries, changes = assign_versions(enriched, catalog.lock)
    lock = Lock(
        origin=catalog.lock.origin,
        revision=catalog.lock.revision,
        adapters=catalog.lock.adapters,
        artifacts=catalog.lock.artifacts,
        capabilities=entries,
    )
    return Catalog(
        capabilities={capability.id: capability for capability in versioned},
        workflows=catalog.workflows,
        lock=lock,
        diagnostics=catalog.diagnostics,
        changes=catalog.changes + tuple(changes),
    )


def _enriched(capability: Capability, entry: dict[str, str] | None) -> Capability:
    if entry is None or capability.kind == "activity":
        return capability
    update: dict[str, Any] = {}
    generated = list(capability.generated)
    if _needs_description(capability):
        update["description"] = entry["summary"]
        generated.append("description")
    if _needs_semantics(capability):
        update["semantics"] = Semantics(
            verb=_known(entry.get("verb")),
            entity=_known(entry.get("entity")),
            domain=_known(entry.get("domain")),
        )
        generated.append("semantics")
    if not update:
        return capability
    update["generated"] = tuple(dict.fromkeys(generated))
    return capability.model_copy(update=update)


def _needs_description(capability: Capability) -> bool:
    """No description, a template placeholder, or nothing beyond the title and the kind."""
    if "description" in capability.generated:
        return False
    text = capability.description.strip()
    if not text or text.startswith("["):
        return True
    remainder = text.replace(capability.title, " ")
    return len([word for word in remainder.split() if word.isalnum()]) < _MIN_WORDS


def _needs_semantics(capability: Capability) -> bool:
    semantics = capability.semantics
    return "semantics" not in capability.generated and not (
        semantics.verb or semantics.entity or semantics.domain
    )


def _known(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return None if not cleaned or cleaned.lower() == "unknown" else cleaned


def _request(batch: Iterable[Capability], catalog: Catalog) -> str:
    """One JSON object per capability: what the catalog knows, never sources or configuration."""
    lines: list[str] = []
    for capability in batch:
        workflow = catalog.workflows.get(capability.id)
        card = {
            "id": capability.id,
            "kind": capability.kind,
            "title": capability.title,
            "description": capability.description,
            "source": capability.source.provider,
            "inputs": [p.name for p in capability.inputs],
            "outputs": [p.name for p in capability.outputs],
            "effects": effects_code(capability.effects) or "none",
            "steps": [node.label for node in workflow.nodes][:30] if workflow else [],
        }
        lines.append(json.dumps(card, ensure_ascii=False))
    return "<capabilities>\n" + "\n".join(lines) + "\n</capabilities>"
