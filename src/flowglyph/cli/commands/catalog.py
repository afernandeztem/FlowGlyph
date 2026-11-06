"""Building catalogs and checking how they change: extract, validate, diff, adapters."""

from inspect import getdoc
from pathlib import Path
from typing import Annotated, Literal

import typer
from rich.markup import escape
from rich.table import Table

import flowglyph
from flowglyph.adapters import available_adapters
from flowglyph.catalog import LOCK_FILE, Bump, Lock, diff_locks
from flowglyph.cli._shared import (
    ADAPTER_HELP,
    REF_HELP,
    console,
    errors,
    fail,
    open_catalog,
    print_changes,
    print_diagnostics,
)
from flowglyph.errors import FlowGlyphError


def extract(
    source: Annotated[
        str,
        typer.Argument(help="A folder, a file, or a git URL (GitHub links to folders work)."),
    ],
    out: Annotated[Path, typer.Option("--out", "-o", help="Where to write the catalog.")] = Path(
        "flowglyph-out"
    ),
    adapter: Annotated[str, typer.Option("--adapter", "-a", help=ADAPTER_HELP)] = "auto",
    ref: Annotated[str | None, typer.Option(help=REF_HELP)] = None,
    strict: Annotated[
        bool, typer.Option(help="Exit with an error when any artifact fails to parse.")
    ] = False,
) -> None:
    """Extract a catalog from SOURCE and save it, versioned against the previous run.

    Every project and document under SOURCE is read: point it at a whole repository.
    """
    previous_lock = out / LOCK_FILE
    try:
        catalog = flowglyph.extract(
            source,
            adapter=adapter,
            previous=previous_lock if previous_lock.is_file() else None,
            ref=ref,
        )
    except FlowGlyphError as error:
        fail(error)
    catalog.save(out)
    invocable = sum(1 for capability in catalog if capability.invocable)
    origin = (
        f" from {catalog.lock.origin} @ {catalog.lock.revision[:10]}"
        if catalog.lock.origin and catalog.lock.revision
        else ""
    )
    console.print(
        f"[bold green]Extracted[/] {invocable} invocable capabilities and "
        f"{len(catalog) - invocable} that cannot be run on their own{escape(origin)} "
        f"into [bold]{escape(str(out))}[/]"
    )
    print_diagnostics(catalog.diagnostics)
    if catalog.changes:
        print_changes(catalog.changes)
    if strict and any(diagnostic.level == "error" for diagnostic in catalog.diagnostics):
        raise typer.Exit(1)


def validate(
    catalog_dir: Annotated[Path, typer.Argument(help="A directory written by `extract`.")],
) -> None:
    """Check a saved catalog against the IR schema and for broken references."""
    catalog = open_catalog(catalog_dir)
    problems = catalog.problems()
    for problem in problems:
        errors.print(f"  [bold red]invalid[/] {escape(problem)}")
    if problems:
        raise typer.Exit(1)
    console.print(
        f"[bold green]Valid[/] {len(catalog)} capabilities, {len(catalog.workflows)} graphs"
    )


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
    print_changes(changes)
    threshold = {"major": Bump.MAJOR, "minor": Bump.MINOR, "patch": Bump.PATCH}.get(fail_on)
    if threshold is not None and max(change.bump for change in changes) >= threshold:
        raise typer.Exit(1)


def adapters() -> None:
    """List the source formats FlowGlyph can read, built in or added by plugins."""
    table = Table(box=None)
    table.add_column("Adapter", no_wrap=True)
    table.add_column("Version", no_wrap=True)
    table.add_column("Reads")
    for name, adapter_class in sorted(available_adapters().items()):
        summary = (getdoc(adapter_class) or "").split("\n", 1)[0]
        table.add_row(name, adapter_class.version, escape(summary))
    console.print(table)
    console.print("Use one with [bold]--adapter <name>[/]; by default every adapter is tried.")


def _lock(path: Path) -> Lock:
    try:
        return Lock.read(path / LOCK_FILE if path.is_dir() else path)
    except (OSError, ValueError) as error:
        fail(f"cannot read a lock from {path}: {error}")
