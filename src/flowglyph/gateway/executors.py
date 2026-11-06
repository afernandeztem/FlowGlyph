"""What actually runs a capability. The `Executor` protocol and the dry-run executor."""

from typing import Any, ClassVar, Protocol, runtime_checkable

from flowglyph.ir import Capability


@runtime_checkable
class Executor(Protocol):
    """Runs a capability against the real system once the gateway has cleared it."""

    name: ClassVar[str]

    def execute(self, capability: Capability, arguments: dict[str, Any]) -> dict[str, Any]:
        """Run `capability` and return its outputs."""
        ...


class DryRunExecutor:
    """Pretends to run capabilities and reports what would have been sent.

    Every gateway guarantee (validation, policy, idempotency, audit) applies unchanged, which
    makes it the safe default for trying an agent against a catalog.
    """

    name: ClassVar[str] = "dryrun"

    def execute(self, capability: Capability, arguments: dict[str, Any]) -> dict[str, Any]:
        """Describe the call that would be made."""
        return {
            "dry_run": True,
            "would_run": capability.source.location,
            "provider": capability.source.provider,
            "arguments": arguments,
            "outputs": {parameter.name: None for parameter in capability.outputs},
        }


EXECUTORS: dict[str, type[Executor]] = {DryRunExecutor.name: DryRunExecutor}
