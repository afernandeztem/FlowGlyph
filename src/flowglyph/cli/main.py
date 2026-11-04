import asyncio
import importlib
from pathlib import Path
from types import ModuleType
from typing import Annotated, Literal

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from rich.tree import Tree

import flowglyph
from flowglyph._internal import markdown
from flowglyph.catalog import LOCK_FILE, Bump, Catalog, Change, Lock, diff_locks
from flowglyph.errors import FlowGlyphError
from flowglyph.ir import Capability

app = typer.Typer(
    name="flowglyph",
    help="Turn enterprise automations into a vendor-neutral IR that agents can use safely.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console(soft_wrap=True)
errors = Console(stderr=True, soft_wrap=True)

_BUMP_STYLE = {Bump.MAJOR: "bold red", Bump.MINOR: "yellow", Bump.PATCH: "cyan"}
_LEVEL_STYLE = {"error": "bold red", "warning": "yellow", "info": "dim"}


def _version(value: bool) -> None:
    if value:
        console.print(f"flowglyph {flowglyph.__version__} (IR {flowglyph.IR_VERSION})")
        raise typer.Exit


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version, is_eager=True, help="Show the version."),
    ] = False,
) -> None:
    """Turn enterprise automations into a vendor-neutral IR that agents can use safely."""


def _open(source: Path) -> Catalog:
    """A saved catalog directory, or a catalog extracted on the fly from sources."""
    try:
        if (source / "catalog.jsonl").is_file():
            return flowglyph.load_catalog(source)
        return flowglyph.extract(source)
    except FlowGlyphError as error:
        errors.print(f"[bold red]error:[/] {error}")
        raise typer.Exit(2) from error


def _print_changes(changes: list[Change] | tuple[Change, ...]) -> None:
    table = Table(box=None, pad_edge=False)
    table.add_column("Capability", overflow="fold")
    for header in ("Change", "Bump", "Version"):
        table.add_column(header, no_wrap=True)
    for change in changes:
        version = f"{change.old_version or '-'} -> {change.new_version or '-'}"
        style = _BUMP_STYLE.get(change.bump, "")
        table.add_row(
            change.capability, change.kind, f"[{style}]{change.bump.name.lower()}[/]", version
        )
    console.print(table)


@app.command()
def extract(
    source: Annotated[Path, typer.Argument(help="Project directory or file to read.")],
    out: Annotated[Path, typer.Option("--out", "-o", help="Where to write the catalog.")] = Path(
        "flowglyph-out"
    ),
    adapter: Annotated[str, typer.Option(help="Adapter name, or `auto` to detect it.")] = "auto",
    strict: Annotated[
        bool, typer.Option(help="Exit with an error when any artifact fails to parse.")
    ] = False,
) -> None:
    """Extract a catalog from SOURCE and save it, versioned against the previous run."""
    previous_lock = out / LOCK_FILE
    try:
        catalog = flowglyph.extract(
            source,
            adapter=adapter,
            previous=previous_lock if previous_lock.is_file() else None,
        )
    except FlowGlyphError as error:
        errors.print(f"[bold red]error:[/] {error}")
        raise typer.Exit(2) from error
    catalog.save(out)
    invocable = sum(1 for capability in catalog if capability.invocable)
    console.print(
        f"[bold green]Extracted[/] {invocable} invocable capabilities and "
        f"{len(catalog) - invocable} activity types into [bold]{out}[/]"
    )
    for diagnostic in catalog.diagnostics:
        style = _LEVEL_STYLE[diagnostic.level]
        errors.print(
            f"  [{style}]{diagnostic.level}[/] {diagnostic.artifact}: {diagnostic.message}"
        )
    if catalog.changes:
        _print_changes(catalog.changes)
    if strict and any(diagnostic.level == "error" for diagnostic in catalog.diagnostics):
        raise typer.Exit(1)


@app.command()
def validate(
    catalog_dir: Annotated[Path, typer.Argument(help="A directory written by `extract`.")],
) -> None:
    """Check a saved catalog against the IR schema and for broken references."""
    catalog = _open(catalog_dir)
    problems = catalog.problems()
    for problem in problems:
        errors.print(f"  [bold red]invalid[/] {problem}")
    if problems:
        raise typer.Exit(1)
    console.print(
        f"[bold green]Valid[/] {len(catalog)} capabilities, {len(catalog.workflows)} graphs"
    )


@app.command()
def diff(
    old: Annotated[Path, typer.Argument(help="Old lock file or catalog directory.")],
    new: Annotated[Path, typer.Argument(help="New lock file or catalog directory.")],
    fail_on: Annotated[
        Literal["major", "minor", "patch", "never"],
        typer.Option(help="Exit with an error when a change of this size or larger is found."),
    ] = "never",
) -> None:
    """Compare two extractions and show which capabilities changed and how much."""
    changes = diff_locks(_lock(old), _lock(new))
    if not changes:
        console.print("No changes.")
        return
    _print_changes(changes)
    threshold = {"major": Bump.MAJOR, "minor": Bump.MINOR, "patch": Bump.PATCH}.get(fail_on)
    if threshold is not None and max(change.bump for change in changes) >= threshold:
        raise typer.Exit(1)


def _lock(path: Path) -> Lock:
    return Lock.read(path / LOCK_FILE if path.is_dir() else path)


@app.command()
def inspect(
    source: Annotated[Path, typer.Argument(help="Catalog directory or project to read.")],
    capability: Annotated[
        str | None, typer.Argument(help="Show this capability's card instead of the call tree.")
    ] = None,
) -> None:
    """Show the call tree of every entry point, or the card of one capability."""
    catalog = _open(source)
    if capability:
        try:
            target = catalog.get(capability)
        except FlowGlyphError as error:
            errors.print(f"[bold red]error:[/] {error}")
            raise typer.Exit(2) from error
        console.print(
            Markdown(markdown.render_capability(target, catalog.workflows, catalog.capabilities))
        )
        return
    for root in _roots(catalog):
        tree = Tree(_label(root))
        _grow(tree, root, catalog, frozenset({root.id}))
        console.print(tree)


def _roots(catalog: Catalog) -> list[Capability]:
    called = {callee for workflow in catalog.workflows.values() for callee in workflow.calls}
    workflows = [catalog.capabilities[w.capability] for w in catalog.workflows.values()]
    entry_points = [c for c in workflows if "entry-point" in c.tags]
    return sorted(entry_points or [c for c in workflows if c.id not in called], key=lambda c: c.id)


def _grow(tree: Tree, capability: Capability, catalog: Catalog, seen: frozenset[str]) -> None:
    workflow = catalog.workflows.get(capability.id)
    if workflow is None:
        return
    for callee_id in workflow.calls:
        callee = catalog.capabilities.get(callee_id)
        if callee is None:
            continue
        if callee_id in seen:
            tree.add(f"{_label(callee)} [dim](recursive)[/]")
            continue
        _grow(tree.add(_label(callee)), callee, catalog, seen | {callee_id})
    for unresolved in workflow.unresolved_calls:
        tree.add(f"[red]? {unresolved}[/]")


def _label(capability: Capability) -> str:
    effects = capability.effects.code() or "pure"
    style = "yellow" if capability.effects.has_side_effects else "green"
    return (
        f"[bold]{capability.title}[/] [{style}]{effects}[/] [dim]{capability.idempotency.mode}[/]"
    )


@app.command()
def search(
    source: Annotated[Path, typer.Argument(help="Catalog directory or project to read.")],
    query: Annotated[str, typer.Argument(help="What you are looking for, in plain words.")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results.")] = 10,
    invocable: Annotated[
        bool, typer.Option("--invocable", help="Only capabilities that can be run.")
    ] = False,
) -> None:
    """Find capabilities by what they do."""
    catalog = _open(source)
    results = catalog.search(query, limit=limit, invocable=True if invocable else None)
    table = Table(box=None)
    table.add_column("Capability", overflow="fold")
    for header in ("Kind", "Effects", "Idempotency"):
        table.add_column(header, no_wrap=True)
    table.add_column("Description")
    for capability in results:
        table.add_row(
            capability.id,
            capability.kind,
            capability.effects.code() or "pure",
            capability.idempotency.mode,
            capability.description.split("\n", 1)[0][:70],
        )
    console.print(table if results else "No matches.")


def _gateway_module() -> ModuleType:
    try:
        return importlib.import_module("flowglyph.gateway")
    except ModuleNotFoundError as error:
        if error.name not in {"mcp", "mcp_types", "jsonschema"}:
            raise
        errors.print("[bold red]error:[/] the gateway needs: pip install 'flowglyph\\[mcp]'")
        raise typer.Exit(2) from error


@app.command()
def serve(
    catalog_dir: Annotated[Path, typer.Argument(help="A directory written by `extract`.")],
    policy: Annotated[
        Path | None, typer.Option(help="Policy YAML. Defaults to approval for destructive steps.")
    ] = None,
    state: Annotated[
        Path | None, typer.Option(help="Where to keep the ledger and audit log.")
    ] = None,
    expose: Annotated[
        Literal["auto", "all", "meta"],
        typer.Option(help="One MCP tool per capability (`all`), search tools only (`meta`)."),
    ] = "auto",
) -> None:
    """Serve the catalog to agents as an MCP server over stdio, with dry-run execution."""
    gateway = _gateway_module()
    server = importlib.import_module("flowglyph.gateway.server")
    if not (catalog_dir / "catalog.jsonl").is_file():
        errors.print(f"[bold red]error:[/] {catalog_dir} has no catalog; run `flowglyph extract`")
        raise typer.Exit(2)
    rules = gateway.Policy.load(policy) if policy else gateway.DEFAULT_POLICY
    instance = gateway.Gateway(catalog_dir, policy=rules, state_dir=state)
    errors.print(f"flowglyph gateway serving {catalog_dir} over stdio (dry-run executor)")
    asyncio.run(server.serve_stdio(instance, expose))


@app.command()
def approve(
    catalog_dir: Annotated[Path, typer.Argument(help="The catalog the gateway serves.")],
    key: Annotated[str, typer.Argument(help="Idempotency key of the run to approve.")],
    state: Annotated[Path | None, typer.Option(help="The gateway's state directory.")] = None,
) -> None:
    """Approve a run that a policy held back, so the agent's next attempt executes it."""
    gateway = _gateway_module()
    ledger = gateway.Ledger((state or catalog_dir / ".flowglyph") / "ledger.sqlite")
    if not ledger.approve(key):
        errors.print(f"[bold red]error:[/] no run is waiting for approval under {key!r}")
        raise typer.Exit(1)
    console.print(f"[bold green]Approved[/] {key}")


@app.command()
def approvals(
    catalog_dir: Annotated[Path, typer.Argument(help="The catalog the gateway serves.")],
    state: Annotated[Path | None, typer.Option(help="The gateway's state directory.")] = None,
) -> None:
    """List runs waiting for a person to approve them."""
    gateway = _gateway_module()
    ledger = gateway.Ledger((state or catalog_dir / ".flowglyph") / "ledger.sqlite")
    pending = ledger.pending_approvals()
    if not pending:
        console.print("Nothing is waiting for approval.")
        return
    table = Table(box=None)
    table.add_column("Key", overflow="fold")
    table.add_column("Capability", overflow="fold")
    table.add_column("Version", no_wrap=True)
    for run in pending:
        table.add_row(run.key, run.capability, run.version)
    console.print(table)


@app.command()
def plan(
    requirements: Annotated[
        Path, typer.Argument(help="Requirements in plain language (text or Markdown).")
    ],
    catalog_dir: Annotated[Path, typer.Argument(help="Catalog directory or project to plan with.")],
    out: Annotated[Path, typer.Option("--out", "-o", help="Where to write the plan.")] = Path(),
    model: Annotated[
        str, typer.Option(help="Claude model that proposes the plan.")
    ] = "claude-opus-5-5",
    effort: Annotated[
        Literal["low", "medium", "high", "xhigh", "max"], typer.Option(help="Reasoning effort.")
    ] = "high",
) -> None:
    """Design a workflow from REQUIREMENTS using only capabilities in the catalog."""
    try:
        planner = importlib.import_module("flowglyph.planner")
        claude = importlib.import_module("flowglyph.planner.claude")
    except ModuleNotFoundError as error:
        if error.name != "anthropic":
            raise
        errors.print("[bold red]error:[/] the planner needs: pip install 'flowglyph\\[llm]'")
        raise typer.Exit(2) from error
    catalog = _open(catalog_dir)
    try:
        report = planner.plan(
            requirements.read_text(encoding="utf-8"),
            catalog,
            claude.ClaudePlanModel(model, effort=effort),
        )
    except FlowGlyphError as error:
        errors.print(f"[bold red]error:[/] {error}")
        raise typer.Exit(2) from error
    proposal, result = report.save(out)
    table = Table(box=None)
    table.add_column("Step", no_wrap=True)
    table.add_column("Capability", overflow="fold")
    table.add_column("Intent")
    for step in report.plan.steps:
        resolved = step.id not in report.unresolved
        capability = step.capability if resolved else "[red]missing[/]"
        table.add_row(step.id, capability or "[red]missing[/]", step.intent)
    console.print(f"[bold]{report.plan.goal}[/]")
    console.print(table)
    for problem in report.problems:
        errors.print(f"  [bold red]problem[/] {problem}")
    for warning in report.warnings:
        errors.print(f"  [yellow]warning[/] {warning}")
    console.print(f"Wrote {proposal} and {result}")
    if report.problems:
        raise typer.Exit(1)
