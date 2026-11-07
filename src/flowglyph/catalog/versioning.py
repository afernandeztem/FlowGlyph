"""Semantic versions for capabilities, computed by comparing an extraction with the last lock."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal, cast

from flowglyph._internal.hashing import fingerprint
from flowglyph.catalog.lock import Bump, Lock, LockEntry, Signature
from flowglyph.ir import Capability, JsonSchema

_DOCUMENTATION_KEYS = frozenset(
    {"description", "examples", "x-seen", "x-default-expression", "x-xaml-template"}
)
_METADATA_FIELDS = frozenset({"effects", "idempotency", "security", "errors", "kind", "invocable"})


@dataclass(frozen=True)
class Change:
    """One capability that differs between two locks."""

    capability: str
    kind: Literal["added", "removed", "changed"]
    bump: Bump
    old_version: str | None
    new_version: str | None


def assign_versions(
    capabilities: Iterable[Capability], previous: Lock | None
) -> tuple[list[Capability], dict[str, LockEntry], list[Change]]:
    """Give each capability the version its changes since `previous` call for.

    Returns:
        The versioned capabilities sorted by id, their lock entries, and what changed.
    """
    versioned: list[Capability] = []
    entries: dict[str, LockEntry] = {}
    changes: list[Change] = []
    for capability in sorted(capabilities, key=lambda c: c.id):
        entry = lock_entry(capability, "1.0.0")
        before = previous.capabilities.get(capability.id) if previous else None
        if before is None:
            if previous is not None:
                changes.append(Change(capability.id, "added", Bump.MINOR, None, entry.version))
        else:
            bump = _bump(before, entry)
            version = _increment(before.version, bump)
            entry = entry.model_copy(update={"version": version})
            if bump is not Bump.NONE:
                changes.append(Change(capability.id, "changed", bump, before.version, version))
        versioned.append(capability.model_copy(update={"version": entry.version}))
        entries[capability.id] = entry
    if previous is not None:
        changes.extend(
            Change(capability_id, "removed", Bump.MAJOR, before.version, None)
            for capability_id, before in sorted(previous.capabilities.items())
            if capability_id not in entries
        )
    return versioned, entries, changes


def diff_locks(old: Lock, new: Lock) -> list[Change]:
    """Capabilities added, removed or changed between two locks."""
    changes: list[Change] = []
    for capability_id in sorted(old.capabilities.keys() | new.capabilities.keys()):
        before = old.capabilities.get(capability_id)
        after = new.capabilities.get(capability_id)
        if before is None and after is not None:
            changes.append(Change(capability_id, "added", Bump.MINOR, None, after.version))
        elif after is None and before is not None:
            changes.append(Change(capability_id, "removed", Bump.MAJOR, before.version, None))
        elif before is not None and after is not None:
            bump = _bump(before, after)
            if bump is not Bump.NONE:
                changes.append(
                    Change(capability_id, "changed", bump, before.version, after.version)
                )
    return changes


def lock_entry(capability: Capability, version: str) -> LockEntry:
    """The lock entry of `capability` at `version`: hashes of its contract, metadata and docs."""
    contract = {
        "input": _strip_documentation(capability.input_schema),
        "output": _strip_documentation(capability.output_schema),
    }
    metadata: dict[str, Any] = capability.model_dump(mode="json", include=set(_METADATA_FIELDS))
    if capability.deprecated:
        # Only when set, so locks written before the field existed keep their hashes.
        metadata["deprecated"] = True
    documentation = {
        "title": capability.title,
        "description": capability.description,
        "parameters": [(p.name, p.description) for p in capability.inputs + capability.outputs],
    }
    return LockEntry(
        version=version,
        source_hash=capability.source.source_hash,
        contract_hash=fingerprint(contract),
        metadata_hash=fingerprint(metadata),
        documentation_hash=fingerprint(documentation),
        signature=Signature.of(capability),
    )


def _bump(before: LockEntry, after: LockEntry) -> Bump:
    if before.contract_hash != after.contract_hash:
        return max(before.signature.bump_to(after.signature), Bump.MINOR)
    if before.metadata_hash != after.metadata_hash:
        return Bump.MINOR
    if before.documentation_hash != after.documentation_hash:
        return Bump.PATCH
    return Bump.NONE


def _increment(version: str, bump: Bump) -> str:
    major, minor, patch = (int(part) for part in version.split("."))
    if bump is Bump.MAJOR:
        return f"{major + 1}.0.0"
    if bump is Bump.MINOR:
        return f"{major}.{minor + 1}.0"
    if bump is Bump.PATCH:
        return f"{major}.{minor}.{patch + 1}"
    return version


def _strip_documentation(schema: JsonSchema) -> JsonSchema:
    stripped: JsonSchema = {}
    for key, value in schema.items():
        if key in _DOCUMENTATION_KEYS:
            continue
        if isinstance(value, Mapping):
            stripped[key] = _strip_documentation(cast("JsonSchema", value))
        else:
            stripped[key] = value
    return stripped
