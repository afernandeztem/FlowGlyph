"""Consoles, error handling and catalog loading shared by every command."""

import functools
from collections.abc import Callable
from pathlib import Path
from typing import NoReturn

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

import flowglyph
from flowglyph.adapters import Diagnostic
from flowglyph.catalog import Bump, Catalog, Change
from flowglyph.errors import FlowGlyphError

console = Console(soft_wrap=True)
errors = Console(stderr=True, soft_wrap=True)

SOURCE_HELP = "A saved catalog, or a folder, file or git URL to extract on the fly."
ADAPTER_HELP = "uipath, sap, sap-cpi, sbpa, openapi, bpmn, n8n, a plugin, or auto to use them all."
REF_HELP = "Branch, tag or commit when SOURCE is a repository."

_BUMP_STYLE = {Bump.MAJOR: "bold red", Bump.MINOR: "yellow", Bump.PATCH: "cyan"}
LEVEL_STYLE = {"error": "bold red", "warning": "yellow", "info": "dim"}


def fail(message: object, code: int = 2) -> NoReturn:
    """Print `message` as an error and stop with exit status `code`."""
    errors.print(f"[bold red]error:[/] {escape(str(message))}")
    raise typer.Exit(code)


def reporting_errors(command: Callable[..., None]) -> Callable[..., None]:
    """Make `command` report a file it cannot read or write like any other error.

    A missing policy file or requirements document is the most likely first mistake, and a
    traceback is the wrong answer to it. Typer still sees the command's own signature.
    """

    @functools.wraps(command)
    def guarded(*args: object, **kwargs: object) -> None:
        try:
            command(*args, **kwargs)
        except OSError as error:
            fail(_describe(error))

    return guarded


def _describe(error: OSError) -> str:
    if error.strerror is None:
        return str(error)
    if error.filename is None:
        return error.strerror
    return f"{error.filename}: {error.strerror}"


def open_catalog(
    source: str | Path,
    *,
    adapter: str = "auto",
    ref: str | None = None,
    previous: Path | None = None,
) -> Catalog:
    """A saved catalog directory, or a catalog extracted on the fly from sources.

    `previous` is a lock file to version against; it is ignored when it does not exist.
    """
    try:
        if (Path(source) / "catalog.jsonl").is_file():
            return flowglyph.load_catalog(source)
        return flowglyph.extract(
            source,
            adapter=adapter,
            ref=ref,
            previous=previous if previous and previous.is_file() else None,
        )
    except FlowGlyphError as error:
        fail(error)


def print_diagnostics(diagnostics: tuple[Diagnostic, ...]) -> None:
    """Print what adapters reported, escaped because messages quote source expressions."""
    for diagnostic in diagnostics:
        style = LEVEL_STYLE[diagnostic.level]
        errors.print(
            f"  [{style}]{diagnostic.level}[/] "
            f"{escape(diagnostic.artifact)}: {escape(diagnostic.message)}"
        )


def print_changes(changes: list[Change] | tuple[Change, ...]) -> None:
    """Print capability changes with their semver bump."""
    table = Table(box=None, pad_edge=False)
    table.add_column("Capability", overflow="fold")
    for header in ("Change", "Bump", "Version"):
        table.add_column(header, no_wrap=True)
    for change in changes:
        version = f"{change.old_version or '-'} -> {change.new_version or '-'}"
        style = _BUMP_STYLE.get(change.bump, "")
        table.add_row(
            escape(change.capability),
            change.kind,
            f"[{style}]{change.bump.name.lower()}[/]",
            version,
        )
    console.print(table)
