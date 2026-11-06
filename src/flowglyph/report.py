"""Idempotency reports: every function in a catalog, what it touches and whether it can be retried.

This is the smallest useful output of FlowGlyph. It needs nothing but a catalog and is meant to
be iterated on: review the rows marked `review`, declare what you know in
`flowglyph.overrides.yaml`, extract again.
"""

import csv
import io
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Literal

from flowglyph.catalog import Catalog
from flowglyph.ir import Capability, CapabilityKind
from flowglyph.views import effects_code, retry_advice

type ReportFormat = Literal["markdown", "csv", "json"]
type Status = Literal["safe", "keyed", "declared", "review"]

_STATUS_HELP = {
    "safe": "no side effects, or naturally idempotent",
    "keyed": "retry-safe when called with its idempotency key",
    "declared": "idempotency declared by the source or by a person",
    "review": "has side effects and no retry guarantee: declare one in the overrides",
}


@dataclass(frozen=True)
class Row:
    """One capability in an idempotency report."""

    id: str
    kind: str
    provider: str
    category: str
    effects: str
    side_effects: bool
    idempotency: str
    key_fields: str
    provenance: str
    confidence: float
    status: Status
    advice: str


def status(capability: Capability) -> Status:
    """Whether a capability's retry behaviour is settled or still needs a person."""
    idempotency = capability.idempotency
    if idempotency.provenance == "declared":
        return "declared"
    if idempotency.mode == "natural" or not capability.effects.has_side_effects:
        return "safe"
    if idempotency.mode == "key":
        return "keyed"
    return "review"


def rows(
    catalog: Catalog,
    *,
    kinds: Iterable[CapabilityKind] | None = None,
    providers: Iterable[str] | None = None,
    side_effects_only: bool = False,
    statuses: Iterable[Status] | None = None,
) -> list[Row]:
    """One row per capability, filtered and sorted by id."""
    wanted_kinds = set(kinds) if kinds else None
    wanted_providers = set(providers) if providers else None
    wanted_statuses = set(statuses) if statuses else None
    found: list[Row] = []
    for capability in sorted(catalog, key=lambda c: c.id):
        row = _row(capability)
        if wanted_kinds and capability.kind not in wanted_kinds:
            continue
        if wanted_providers and row.provider not in wanted_providers:
            continue
        if side_effects_only and not row.side_effects:
            continue
        if wanted_statuses and row.status not in wanted_statuses:
            continue
        found.append(row)
    return found


def render(report: list[Row], output: ReportFormat) -> str:
    """The report as Markdown, CSV or JSON text."""
    if output == "json":
        return json.dumps([asdict(row) for row in report], indent=2) + "\n"
    if output == "csv":
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list(Row.__dataclass_fields__))
        writer.writeheader()
        writer.writerows(asdict(row) for row in report)
        return buffer.getvalue()
    return _markdown(report)


def _row(capability: Capability) -> Row:
    return Row(
        id=capability.id,
        kind=capability.kind,
        provider=capability.source.provider,
        category=capability.category,
        effects=effects_code(capability.effects) or "none",
        side_effects=capability.effects.has_side_effects,
        idempotency=capability.idempotency.mode,
        key_fields=", ".join(capability.idempotency.key_fields),
        provenance=capability.idempotency.provenance,
        confidence=capability.idempotency.confidence,
        status=status(capability),
        advice=retry_advice(capability.idempotency),
    )


def _markdown(report: list[Row]) -> str:
    counts = {name: sum(1 for row in report if row.status == name) for name in _STATUS_HELP}
    lines = [
        "# Idempotency report",
        "",
        f"{len(report)} capabilities. "
        + ", ".join(f"{counts[name]} {name}" for name in _STATUS_HELP)
        + ".",
        "",
        "| Capability | Kind | Effects | Idempotency | Key | Status | Advice |",
        "|---|---|---|---|---|---|---|",
    ]
    lines.extend(
        f"| `{row.id}` | {row.kind} | {row.effects} | {row.idempotency} "
        f"| {row.key_fields or '-'} | {row.status} | {row.advice} |"
        for row in report
    )
    lines += ["", *(f"- **{name}**: {meaning}" for name, meaning in _STATUS_HELP.items()), ""]
    return "\n".join(lines)
