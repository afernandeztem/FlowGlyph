"""Writing context files for coding agents into UiPath projects."""

from pathlib import Path
from typing import Annotated

import typer
from rich.markup import escape

import flowglyph
from flowglyph import context as agent_context
from flowglyph.cli._shared import console, fail
from flowglyph.errors import FlowGlyphError


def context(
    source: Annotated[Path, typer.Argument(help="A folder holding one or more UiPath projects.")],
    *,
    catalog_dir: Annotated[
        Path | None,
        typer.Option(
            "--catalog",
            help="Use this saved catalog, with its overrides and enrichment, instead of "
            "extracting SOURCE again.",
        ),
    ] = None,
    out: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Write here instead of into each project."),
    ] = None,
    force: Annotated[
        bool, typer.Option(help="Replace context files that FlowGlyph did not write.")
    ] = False,
) -> None:
    """Write AGENTS.md, .claude/rules/project-context.md and activity cards for coding agents.

    Every fact is read from the project: arguments and their types, entry points, the call tree,
    what each workflow does to the world and whether it is safe to retry. Notes written at the
    end of a generated file are kept.
    """
    found = agent_context.projects(source)
    if not found:
        fail(f"no UiPath project under {source}")
    try:
        catalog = flowglyph.load_catalog(catalog_dir) if catalog_dir else flowglyph.extract(source)
    except FlowGlyphError as error:
        fail(error)
    for project in found:
        files = agent_context.project_files(catalog, project)
        target = project.root
        if out is not None:
            relative = project.root.resolve().relative_to(source.resolve())
            target = out / relative
        written = agent_context.write(target, files, force=force)
        changed = [item for item in written if item.action in {"created", "updated"}]
        kept = [item for item in written if item.action.startswith("kept")]
        console.print(
            f"[bold green]Context[/] {escape(project.name)}: {len(changed)} files written, "
            f"{len(written) - len(changed) - len(kept)} unchanged, in {escape(str(target))}"
        )
        for item in kept:
            console.print(
                f"  [yellow]kept[/] {escape(str(item.path))}: not written by flowglyph; "
                "use --force to replace it"
            )
