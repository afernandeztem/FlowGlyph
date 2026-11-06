"""Corrections a person writes in `flowglyph.overrides.yaml`, applied on top of extraction."""

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, cast

import yaml

from flowglyph.ir import Capability

OVERRIDES_FILE = "flowglyph.overrides.yaml"


def apply_overrides(capabilities: Iterable[Capability], path: Path) -> list[Capability]:
    """Deep-merge the overrides file at `path`, if any, into the matching capabilities.

    Idempotency set by a person becomes `declared`, with full confidence.
    """
    if not path.is_file():
        return list(capabilities)
    document = cast("dict[str, Any]", yaml.safe_load(path.read_text(encoding="utf-8")) or {})
    overrides = cast("dict[str, dict[str, Any]]", document.get("capabilities", {}))
    result: list[Capability] = []
    for capability in capabilities:
        patch = overrides.get(capability.id)
        if patch is None:
            result.append(capability)
            continue
        if "idempotency" in patch:
            patch = {
                **patch,
                "idempotency": {
                    **patch["idempotency"],
                    "provenance": "declared",
                    "confidence": 1.0,
                    "inferred_by": None,
                },
            }
        merged = _deep_merge(capability.model_dump(mode="json"), patch)
        result.append(Capability.model_validate(merged))
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
