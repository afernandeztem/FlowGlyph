"""Corrections a person writes in `flowglyph.overrides.yaml`, applied on top of extraction."""

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, cast

import yaml
from pydantic import ValidationError

from flowglyph.errors import CatalogError
from flowglyph.ir import Capability

OVERRIDES_FILE = "flowglyph.overrides.yaml"


def apply_overrides(capabilities: Iterable[Capability], path: Path) -> list[Capability]:
    """Deep-merge the overrides file at `path`, if any, into the matching capabilities.

    Idempotency set by a person becomes `declared`, with full confidence.
    """
    if not path.is_file():
        return list(capabilities)
    try:
        document: object = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as error:
        raise CatalogError(f"{path.name} is not valid YAML: {error}") from error
    if not isinstance(document, dict):
        raise CatalogError(f"{path.name} must be a mapping with a `capabilities` key")
    overrides: object = cast("dict[str, object]", document).get("capabilities") or {}
    if not isinstance(overrides, dict):
        raise CatalogError(f"`capabilities` in {path.name} must map capability ids to changes")
    overrides = cast("dict[str, object]", overrides)
    result: list[Capability] = []
    for capability in capabilities:
        found = overrides.get(capability.id)
        if found is None:
            result.append(capability)
            continue
        if not isinstance(found, dict):
            raise CatalogError(f"{capability.id} in {path.name} must be a mapping of fields")
        patch = cast("dict[str, Any]", found)
        if "idempotency" in patch:
            stated: object = patch["idempotency"]
            if not isinstance(stated, dict):
                raise CatalogError(
                    f"`idempotency` of {capability.id} in {path.name} must be a mapping"
                )
            patch = {
                **patch,
                "idempotency": {
                    **cast("dict[str, Any]", stated),
                    "provenance": "declared",
                    "confidence": 1.0,
                    "inferred_by": None,
                },
            }
        merged = _deep_merge(capability.model_dump(mode="json"), patch)
        try:
            result.append(Capability.model_validate(merged))
        except ValidationError as error:
            raise CatalogError(f"{capability.id} in {path.name} is not valid: {error}") from error
    return result


def _deep_merge(base: dict[str, Any], patch: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in patch.items():
        current = merged.get(key)
        if isinstance(value, Mapping) and isinstance(current, dict):
            merged[key] = _deep_merge(
                cast("dict[str, Any]", current), cast("Mapping[str, Any]", value)
            )
        else:
            merged[key] = value
    return merged
