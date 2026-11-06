"""What only shows when iFlows are read together: ids, ProcessDirect links and shared effects."""

import re
from collections import defaultdict
from dataclasses import dataclass, field

from flowglyph._internal.paths import distinguishing_names
from flowglyph.adapters.sap_cpi.bundle import Bundle
from flowglyph.adapters.sap_cpi.iflow import IFlow
from flowglyph.ir import Capability, Effects, Idempotency, Workflow

_UNSAFE = re.compile(r"[^A-Za-z0-9.-]+")


@dataclass
class Entry:
    """One parsed iFlow and the capabilities made from it."""

    bundle: Bundle
    artifact: str
    source_hash: str
    iflow: IFlow
    key: str = ""
    capabilities: list[Capability] = field(default_factory=list[Capability])


def assign_keys(entries: list[Entry]) -> None:
    """Give each iFlow a unique id key, telling apart copies by version or by location."""
    groups: defaultdict[str, list[Entry]] = defaultdict(list)
    for entry in entries:
        groups[slug(entry.bundle.symbolic_name)].append(entry)
    for key, group in groups.items():
        if len(group) == 1:
            group[0].key = key
            continue
        versions = [entry.bundle.version or "" for entry in group]
        suffixes = (
            [slug(version) for version in versions]
            if len(set(versions)) == len(versions) and all(versions)
            else distinguishing_names([entry.artifact for entry in group])
        )
        for entry, suffix in zip(group, suffixes, strict=True):
            entry.key = f"{key}.{suffix}"


def process_direct_endpoints(entries: list[Entry]) -> dict[str, str]:
    """ProcessDirect addresses mapped to the capability listening on each."""
    endpoints: dict[str, str] = {}
    for entry in entries:
        for sender, capability in zip(entry.iflow.senders, entry.capabilities, strict=False):
            if sender.component.upper() == "PROCESSDIRECT" and sender.address:
                endpoints[sender.address] = capability.id
    return endpoints


def propagate_effects(entries: list[Entry], workflows: list[Workflow]) -> None:
    """Give each iFlow the effects of the iFlows it calls through ProcessDirect."""
    by_id = {c.id: c for entry in entries for c in entry.capabilities}
    graph = {w.capability: w.calls for w in workflows}
    changed = True
    while changed:
        changed = False
        for entry in entries:
            calls = graph.get(entry.capabilities[0].id, ())
            callees = [by_id[callee].effects for callee in calls if callee in by_id]
            for index, capability in enumerate(entry.capabilities):
                combined = Effects.combine([capability.effects, *callees])
                if combined == capability.effects:
                    continue
                updated = capability.model_copy(
                    update={"effects": combined, "idempotency": _recheck(capability, combined)}
                )
                entry.capabilities[index] = updated
                by_id[updated.id] = updated
                changed = True


def _recheck(capability: Capability, effects: Effects) -> Idempotency:
    idempotency = capability.idempotency
    inferred_safe = idempotency.provenance == "inferred" and idempotency.mode == "natural"
    if inferred_safe and effects.has_side_effects:
        return Idempotency(mode="none", confidence=0.7)
    return idempotency


def expand_workflows(workflows: list[Workflow], entries: list[Entry]) -> list[Workflow]:
    """One workflow per capability: iFlows with several endpoints share their graph."""
    expanded: list[Workflow] = []
    by_first = {w.capability: w for w in workflows}
    for entry in entries:
        graph = by_first.get(entry.capabilities[0].id) if entry.capabilities else None
        if graph is None:
            continue
        expanded.extend(
            graph.model_copy(update={"id": c.id, "capability": c.id}) for c in entry.capabilities
        )
    return expanded


def slug(text: str) -> str:
    """`text` reduced to characters safe in a capability id."""
    return _UNSAFE.sub("_", text).strip("_") or "endpoint"
