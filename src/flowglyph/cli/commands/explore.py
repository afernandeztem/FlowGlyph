"""Reading a catalog: inspect call trees and cards, search, and the idempotency report."""

import sys
from pathlib import Path
from typing import Annotated, Literal, cast

import typer
from rich.markdown import Markdown
from rich.markup import escape
from rich.table import Table
from rich.tree import Tree

from flowglyph import report
from flowglyph._internal import markdown
from flowglyph.catalog import Catalog
from flowglyph.cli._shared import SOURCE_HELP, console, fail, open_catalog
from flowglyph.errors import FlowGlyphError
from flowglyph.ir import Capability, CapabilityKind
from flowglyph.views import effects_code

_STATUS_STYLE = {
    "safe": "green",
    "keyed": "cyan",
    "declared": "blue",
    "review": "bold yellow",
    "n/a": "dim",
}


def inspect(
    source: Annotated[str, typer.Argument(help=SOURCE_HELP)],
    capability: Annotated[
        str | None, typer.Argument(help="Show this capability's card instead of the call tree.")
    ] = None,
) -> None:
    """Show the call tree of every entry point, or the card of one capability."""
    catalog = open_catalog(source)
    if capability:
        try:
            target = catalog.get(capability)
        except FlowGlyphError as error:
            fail(error)
        console.print(
            Markdown(markdown.render_capability(target, catalog.workflows, catalog.capabilities))
        )
        return
    for root in _roots(catalog):
        tree = Tree(_label(root))
        _grow(tree, root, catalog, frozenset({root.id}))
        console.print(tree)


def search(
    source: Annotated[str, typer.Argument(help=SOURCE_HELP)],
    query: Annotated[str, typer.Argument(help="What you are looking for, in plain words.")],
    limit: Annotated[int, typer.Option("--limit", "-n", help="Maximum results.")] = 10,
    invocable: Annotated[
        bool, typer.Option("--invocable", help="Only capabilities that can be run.")
    ] = False,
) -> None:
    """Find capabilities by what they do."""
    catalog = open_catalog(source)
    results = catalog.search(query, limit=limit, invocable=True if invocable else None)
    table = Table(box=None)
    table.add_column("Capability", overflow="fold")
    for header in ("Kind", "Effects", "Idempotency"):
        table.add_column(header, no_wrap=True)
    table.add_column("Description")
    for capability in results:
        table.add_row(
            escape(capability.id),
            capability.kind,
            effects_code(capability.effects) or "pure",
            capability.idempotency.mode,
            escape(capability.description.split("\n", 1)[0][:70]),
        )
    console.print(table if results else "No matches.")


def idempotency(
    source: Annotated[str, typer.Argument(help=SOURCE_HELP)],
    *,
    output_format: Annotated[
        Literal["table", "markdown", "csv", "json"],
        typer.Option("--format", "-f", help="How to print the report."),
    ] = "table",
    out: Annotated[
        Path | None, typer.Option("--out", "-o", help="Write the report to a file.")
    ] = None,
    adapter: Annotated[
        str, typer.Option("--adapter", "-a", help="Only read this kind of source.")
    ] = "auto",
    kind: Annotated[
        list[str] | None,
        typer.Option(help="Only these kinds: workflow, operation, activity. Repeatable."),
    ] = None,
    provider: Annotated[
        list[str] | None,
        typer.Option(help="Only these providers: uipath, openapi, sap, sap-cpi. Repeatable."),
    ] = None,
    side_effects: Annotated[
        bool, typer.Option("--side-effects", help="Only capabilities that change state.")
    ] = False,
    review: Annotated[
        bool, typer.Option("--review", help="Only what still needs a person to decide.")
    ] = False,
) -> None:
    """Every function with its effects and idempotency: the catalog and nothing else.

    Rows marked review have side effects and no retry guarantee. Declare what you know in
    flowglyph.overrides.yaml next to the sources and run the command again.
    """
    catalog = open_catalog(source, adapter=adapter)
    selected = report.rows(
        catalog,
        kinds=cast("list[CapabilityKind] | None", kind),
        providers=provider,
        side_effects_only=side_effects,
        statuses=["review"] if review else None,
    )
    if output_format != "table":
        text = report.render(selected, output_format)
        if out:
            out.write_text(text, encoding="utf-8", newline="\n")
            console.print(f"Wrote {len(selected)} rows to {escape(str(out))}")
        else:
            sys.stdout.write(text)
        return
    table = Table(box=None)
    table.add_column("Capability", overflow="fold")
    for header in ("Kind", "Effects", "Idempotency", "Status"):
        table.add_column(header, no_wrap=True)
    for row in selected:
        style = _STATUS_STYLE[row.status]
        table.add_row(
            escape(row.id), row.kind, row.effects, row.idempotency, f"[{style}]{row.status}[/]"
        )
    console.print(table)
    pending = sum(1 for row in selected if row.status == "review")
    console.print(f"{len(selected)} capabilities, {pending} to review.")


def _roots(catalog: Catalog) -> list[Capability]:
    called = {callee for workflow in catalog.workflows.values() for callee in workflow.calls}
    workflows = [catalog.capabilities[w.capability] for w in catalog.workflows.values()]
    entry_points = [c for c in workflows if c.entry_point]
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
        tree.add(f"[red]? {escape(unresolved)}[/]")


def _label(capability: Capability) -> str:
    effects = effects_code(capability.effects) or "pure"
    style = "yellow" if capability.effects.has_side_effects else "green"
    return (
        f"[bold]{escape(capability.title)}[/] [{style}]{effects}[/] "
        f"[dim]{capability.idempotency.mode}[/]"
    )
