"""The lock file: what an extraction remembers so the next one can version capabilities."""

import json
from collections.abc import Mapping
from enum import IntEnum
from pathlib import Path
from typing import cast

from pydantic import BaseModel, ConfigDict

from flowglyph.ir import IR_VERSION, Capability, JsonSchema

LOCK_FILE = "flowglyph.lock"


class Bump(IntEnum):
    """How much a capability changed between two extractions."""

    NONE = 0
    PATCH = 1
    MINOR = 2
    MAJOR = 3


class Shape(BaseModel):
    """What a JSON Schema accepts, reduced to what decides whether a change is breaking."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    types: tuple[str, ...] = ("any",)
    required: bool = False
    properties: dict[str, "Shape"] = {}
    items: "Shape | None" = None

    @classmethod
    def of(cls, schema: JsonSchema, *, required: bool = False) -> "Shape":
        """The shape of `schema`; a schema without a `type` accepts anything."""
        declared = schema.get("type")
        if isinstance(declared, list):
            types = tuple(sorted(str(each) for each in cast("list[object]", declared)))
        else:
            types = (str(declared),) if declared else ("any",)
        names = set(cast("list[object]", schema.get("required", [])))
        properties = cast("dict[str, JsonSchema]", schema.get("properties", {}))
        items = schema.get("items")
        return cls(
            types=types,
            required=required,
            properties={
                name: cls.of(spec, required=name in names) for name, spec in properties.items()
            },
            items=cls.of(cast("JsonSchema", items)) if isinstance(items, Mapping) else None,
        )


class Signature(BaseModel):
    """The parts of a contract that decide whether a change is breaking."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    inputs: Shape = Shape(types=("object",))
    outputs: Shape = Shape(types=("object",))
    invocable: bool = True

    @classmethod
    def of(cls, capability: Capability) -> "Signature":
        """The signature of `capability`."""
        return cls(
            inputs=Shape.of(capability.input_schema),
            outputs=Shape.of(capability.output_schema),
            invocable=capability.invocable,
        )

    def bump_to(self, new: "Signature") -> Bump:
        """The semver bump needed to go from this signature to `new`.

        A change is breaking when a call that was valid can be rejected, when a result can
        hold something a caller did not expect, or when the capability stops being callable.
        """
        breaking = (
            (self.invocable and not new.invocable)
            or _rejects(new.inputs, self.inputs)
            or _surprises(new.outputs, self.outputs)
        )
        if breaking:
            return Bump.MAJOR
        if new != self:
            return Bump.MINOR
        return Bump.NONE


def _rejects(new: Shape, old: Shape) -> bool:
    """Whether a value `old` accepted can be refused by `new`."""
    if not _covers(new.types, old.types):
        return True
    newly_required = any(
        shape.required and not (name in old.properties and old.properties[name].required)
        for name, shape in new.properties.items()
    )
    narrowed = any(
        name not in new.properties or _rejects(new.properties[name], shape)
        for name, shape in old.properties.items()
    )
    # An array that took anything and now names its items refuses what it used to take.
    items = new.items is not None and (old.items is None or _rejects(new.items, old.items))
    return newly_required or narrowed or items


def _surprises(new: Shape, old: Shape) -> bool:
    """Whether `new` can produce a value a consumer of `old` did not expect."""
    if not _covers(old.types, new.types):
        return True
    changed = any(
        name not in new.properties
        or (shape.required and not new.properties[name].required)
        or _surprises(new.properties[name], shape)
        for name, shape in old.properties.items()
    )
    items = old.items is not None and (new.items is None or _surprises(new.items, old.items))
    return changed or items


def _covers(wide: tuple[str, ...], narrow: tuple[str, ...]) -> bool:
    return "any" in wide or ("any" not in narrow and set(narrow) <= set(wide))


class LockEntry(BaseModel):
    """What the lock file remembers about one capability."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str
    source_hash: str
    contract_hash: str
    metadata_hash: str
    documentation_hash: str
    signature: Signature


class Lock(BaseModel):
    """Reproducibility record of an extraction, used to version capabilities over time."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ir_version: str = IR_VERSION
    origin: str | None = None
    revision: str | None = None
    adapters: dict[str, str] = {}
    artifacts: dict[str, str] = {}
    capabilities: dict[str, LockEntry] = {}

    @classmethod
    def read(cls, path: str | Path) -> "Lock":
        """Load a lock file."""
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))

    def write(self, path: str | Path) -> None:
        """Write the lock file with stable formatting and without defaults, so it diffs cleanly."""
        document = {
            "ir_version": self.ir_version,
            **self.model_dump(mode="json", exclude_defaults=True),
        }
        text = json.dumps(document, indent=2, sort_keys=True)
        Path(path).write_text(text + "\n", encoding="utf-8", newline="\n")
