"""The lock file: what an extraction remembers so the next one can version capabilities."""

import json
from enum import IntEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from flowglyph.ir import IR_VERSION, Capability

LOCK_FILE = "flowglyph.lock"


class Bump(IntEnum):
    """How much a capability changed between two extractions."""

    NONE = 0
    PATCH = 1
    MINOR = 2
    MAJOR = 3


class Signature(BaseModel):
    """The parts of a contract that decide whether a change is breaking."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    inputs: dict[str, tuple[str, bool]] = {}
    outputs: dict[str, str] = {}

    @classmethod
    def of(cls, capability: Capability) -> "Signature":
        """The signature of `capability`."""
        return cls(
            inputs={p.name: (p.type, p.required) for p in capability.inputs},
            outputs={p.name: p.type for p in capability.outputs},
        )

    def bump_to(self, new: "Signature") -> Bump:
        """The semver bump needed to go from this signature to `new`."""
        removed_input = self.inputs.keys() - new.inputs.keys()
        removed_output = self.outputs.keys() - new.outputs.keys()
        retyped = any(
            new.inputs[name][0] != spec[0]
            for name, spec in self.inputs.items()
            if name in new.inputs
        ) or any(
            new.outputs[name] != kind for name, kind in self.outputs.items() if name in new.outputs
        )
        newly_required = any(
            required and not self.inputs.get(name, ("", False))[1]
            for name, (_, required) in new.inputs.items()
        )
        if removed_input or removed_output or retyped or newly_required:
            return Bump.MAJOR
        if new != self:
            return Bump.MINOR
        return Bump.NONE


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
        """Write the lock file with stable formatting, so it diffs cleanly."""
        text = json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True)
        Path(path).write_text(text + "\n", encoding="utf-8", newline="\n")
