"""Turning sources into a catalog: discover, run adapters, apply overrides, version."""

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from flowglyph import sources
from flowglyph.adapters import Adapter, Diagnostic, available_adapters, discover, get_adapter
from flowglyph.catalog.lock import Lock
from flowglyph.catalog.model import Catalog
from flowglyph.catalog.overrides import OVERRIDES_FILE, apply_overrides
from flowglyph.catalog.versioning import assign_versions
from flowglyph.errors import AdapterNotFoundError
from flowglyph.ir import Capability, Workflow


def extract(
    path: str | Path,
    *,
    adapter: str | Adapter = "auto",
    previous: Lock | str | Path | None = None,
    ref: str | None = None,
    refine: Callable[[list[Capability]], list[Capability]] | None = None,
) -> Catalog:
    """Extract a catalog from a folder, a file or a git repository URL.

    Every source found under `path` is extracted, so a repository holding many UiPath projects,
    OpenAPI documents and SAP OData metadata files becomes one catalog.

    Args:
        path: A folder, a file, or a git URL such as a GitHub link to a repository or folder.
        adapter: `"auto"` to use every adapter that finds something, or one adapter by name
            (`"uipath"`, `"sap"`, `"sap-cpi"`, `"sbpa"`, `"openapi"`, `"bpmn"`, `"n8n"`, a
            plugin) or instance.
        previous: The lock of an earlier extraction, used to version capabilities. When
            omitted, capabilities start at 1.0.0.
        ref: Branch, tag or commit to read when `path` is a repository URL.
        refine: Applied after overrides and before versioning, such as cached enrichment, so
            what it adds is versioned like the rest of the capability.

    Returns:
        The catalog, with `changes` describing what moved since `previous`.

    Raises:
        AdapterNotFoundError: If no adapter finds anything to extract.
    """
    source = sources.resolve(path, ref=ref)
    root = source.path if source.path.is_dir() else source.path.parent
    jobs = _jobs(source.path, adapter)
    capabilities: dict[str, Capability] = {}
    workflows: dict[str, Workflow] = {}
    artifacts: dict[str, str] = {}
    diagnostics: list[Diagnostic] = []
    for job_adapter, target in jobs:
        extraction = job_adapter.extract(target)
        prefix = _prefix(target, root)
        artifacts.update({prefix + name: digest for name, digest in extraction.artifacts.items()})
        diagnostics.extend(
            replace(diagnostic, artifact=prefix + diagnostic.artifact)
            for diagnostic in extraction.diagnostics
        )
        for capability in extraction.capabilities:
            if capability.id in capabilities and capability.kind != "activity":
                diagnostics.append(
                    Diagnostic("warning", prefix, f"{capability.id} is defined more than once")
                )
            capabilities[capability.id] = capability
        workflows.update({workflow.id: workflow for workflow in extraction.workflows})
    overridden = apply_overrides(capabilities.values(), root / OVERRIDES_FILE)
    if refine is not None:
        overridden = refine(overridden)
    old_lock = Lock.read(previous) if isinstance(previous, str | Path) else previous
    versioned, entries, changes = assign_versions(overridden, old_lock)
    return Catalog(
        capabilities={capability.id: capability for capability in versioned},
        workflows=workflows,
        lock=Lock(
            origin=source.origin,
            revision=source.revision,
            adapters={job_adapter.name: job_adapter.version for job_adapter, _ in jobs},
            artifacts=dict(sorted(artifacts.items())),
            capabilities=entries,
        ),
        diagnostics=tuple(diagnostics),
        changes=tuple(changes),
    )


def _jobs(path: Path, adapter: str | Adapter) -> list[tuple[Adapter, Path]]:
    if isinstance(adapter, str):
        chosen = (
            [cls() for cls in available_adapters().values()]
            if adapter == "auto"
            else [get_adapter(adapter)]
        )
    else:
        chosen = [adapter]
    jobs = [(each, target) for each in chosen for target in discover(each, path)]
    if not jobs:
        names = ", ".join(each.name for each in chosen)
        raise AdapterNotFoundError(f"nothing to extract in {path} (looked for: {names})")
    return jobs


def _prefix(target: Path, root: Path) -> str:
    base = target if target.is_dir() else target.parent
    relative = base.resolve().relative_to(root.resolve()).as_posix()
    return "" if relative == "." else relative + "/"
