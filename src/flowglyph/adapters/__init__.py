"""Adapters translate a source format into Automation IR.

An adapter is any class implementing `Adapter`. Built-in adapters and those shipped by other
packages are discovered through the `flowglyph.adapters` entry point group; adapters can also
be registered at runtime with `register_adapter`.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from pathlib import Path
from typing import ClassVar, Literal, Protocol, cast, runtime_checkable

from flowglyph.errors import AdapterNotFoundError
from flowglyph.ir import Capability, Workflow


@dataclass(frozen=True)
class Diagnostic:
    """Something an adapter noticed but could not, or should not, fail on."""

    level: Literal["info", "warning", "error"]
    artifact: str
    message: str


@dataclass(frozen=True)
class Extraction:
    """Everything an adapter produced from one source."""

    capabilities: Sequence[Capability] = ()
    workflows: Sequence[Workflow] = ()
    artifacts: dict[str, str] = field(default_factory=dict[str, str])
    diagnostics: Sequence[Diagnostic] = ()


@runtime_checkable
class Adapter(Protocol):
    """A deterministic translator from one source format to IR.

    Implementations must not access the network or call an LLM: the same input bytes must
    always produce the same `Extraction`.
    """

    name: ClassVar[str]
    version: ClassVar[str]

    def detect(self, path: Path) -> bool:
        """Whether this adapter understands the file or directory at `path`."""
        ...

    def extract(self, path: Path) -> Extraction:
        """Translate the source at `path` into IR."""
        ...


_registry: dict[str, type[Adapter]] = {}


def register_adapter(name: str, adapter: type[Adapter]) -> None:
    """Make `adapter` available under `name`, replacing any adapter with that name."""
    _registry[name] = adapter


def available_adapters() -> dict[str, type[Adapter]]:
    """Every adapter that can be used, from entry points and runtime registration."""
    adapters: dict[str, type[Adapter]] = {}
    for entry_point in entry_points(group="flowglyph.adapters"):
        adapters[entry_point.name] = entry_point.load()
    adapters.update(_registry)
    return adapters


def get_adapter(name: str) -> Adapter:
    """Instantiate the adapter registered under `name`.

    Raises:
        AdapterNotFoundError: If no adapter has that name.
    """
    adapters = available_adapters()
    if name not in adapters:
        known = ", ".join(sorted(adapters)) or "none"
        raise AdapterNotFoundError(f"unknown adapter {name!r}; available: {known}")
    return adapters[name]()


def discover(adapter: Adapter, root: Path) -> list[Path]:
    """The sources under `root` that `adapter` extracts, each one on its own.

    Adapters can define `discover(root)` to find several projects or documents in one tree,
    such as every UiPath project in a repository. Adapters without it are given `root` as a
    whole when they recognise it.
    """
    finder = getattr(adapter, "discover", None)
    if callable(finder):
        found = cast("Iterable[Path]", finder(root))
        return sorted(found)
    return [root] if adapter.detect(root) else []


def detect_adapter(path: Path) -> Adapter:
    """The first available adapter that recognises `path`.

    Raises:
        AdapterNotFoundError: If no adapter recognises it.
    """
    for adapter_class in available_adapters().values():
        adapter = adapter_class()
        if adapter.detect(path):
            return adapter
    raise AdapterNotFoundError(f"no adapter recognises {path}")


__all__ = [
    "Adapter",
    "Diagnostic",
    "Extraction",
    "available_adapters",
    "detect_adapter",
    "discover",
    "get_adapter",
    "register_adapter",
]
