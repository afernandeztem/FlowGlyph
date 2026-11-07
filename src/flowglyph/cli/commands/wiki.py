"""The LLM wiki: build pages from a catalog and lint them."""

from pathlib import Path
from typing import Annotated

import typer
from rich.markup import escape
from rich.table import Table

from flowglyph import wiki
from flowglyph.catalog import LOCK_FILE
from flowglyph.cli._shared import (
    ADAPTER_HELP,
    LEVEL_STYLE,
    REF_HELP,
    SOURCE_HELP,
    console,
    fail,
    open_catalog,
    reporting_errors,
)

app = typer.Typer(
    help="An LLM wiki of the catalog: pages to read, a schema for the LLM that keeps them.",
    no_args_is_help=True,
)


@app.command()
@reporting_errors
def build(
    source: Annotated[str, typer.Argument(help=SOURCE_HELP)],
    *,
    out: Annotated[Path, typer.Option("--out", "-o", help="Wiki directory.")] = Path("wiki"),
    adapter: Annotated[str, typer.Option("--adapter", "-a", help=ADAPTER_HELP)] = "auto",
    ref: Annotated[str | None, typer.Option(help=REF_HELP)] = None,
) -> None:
    """Write or refresh the wiki. Notes written in the pages are kept."""
    catalog = open_catalog(
        source, adapter=adapter, ref=ref, previous=out / wiki.DATA_DIRECTORY / LOCK_FILE
    )
    result = wiki.build_wiki(catalog, out, subject=source)
    console.print(f"[bold green]Wiki[/] {result.pages} pages in [bold]{escape(str(out))}[/]")
    console.print(escape(result.log_entry.rstrip()))
    console.print(
        f"Next: [bold]flowglyph wiki lint {escape(str(out))}[/], "
        f"then read {escape(str(out))}/AGENTS.md"
    )


@app.command()
@reporting_errors
def lint(
    directory: Annotated[Path, typer.Argument(help="Wiki directory.")] = Path("wiki"),
    *,
    strict: Annotated[
        bool, typer.Option(help="Exit with an error when there are warnings or errors.")
    ] = False,
) -> None:
    """Check the wiki: idempotency to review, gaps, orphans, broken links, retired pages."""
    if not (directory / wiki.DATA_DIRECTORY / "catalog.jsonl").is_file():
        fail(f"{directory} is not a wiki; run `flowglyph wiki build`")
    issues = wiki.lint_wiki(directory)
    table = Table(box=None)
    table.add_column("Level", no_wrap=True)
    table.add_column("Page", overflow="fold")
    table.add_column("Issue")
    for issue in issues:
        table.add_row(
            f"[{LEVEL_STYLE[issue.level]}]{issue.level}[/]",
            escape(issue.page),
            escape(issue.message),
        )
    console.print(table if issues else "No issues.")
    if strict and any(issue.level != "info" for issue in issues):
        raise typer.Exit(1)
