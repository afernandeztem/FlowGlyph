"""Compiling a workflow back into BPMN or a UiPath workflow."""

from pathlib import Path
from typing import Annotated, Literal

import typer
from rich.markup import escape

from flowglyph.catalog import Catalog
from flowglyph.cli._shared import SOURCE_HELP, console, errors, fail, open_catalog
from flowglyph.compilers import compile_workflow, load_planned
from flowglyph.errors import FlowGlyphError
from flowglyph.ir import Capability, Workflow


def compile(
    source: Annotated[
        str,
        typer.Argument(help=f"A workflow.ir.yaml written by `flowglyph plan`, or {SOURCE_HELP}"),
    ],
    capability: Annotated[
        str | None, typer.Argument(help="With a catalog: the workflow to compile.")
    ] = None,
    *,
    to: Annotated[Literal["bpmn", "xaml"], typer.Option("--to", help="What to compile into.")],
    engine: Annotated[
        Literal["bpmn", "camunda7", "camunda8"],
        typer.Option(help="For BPMN: plain, or with the extensions a Camunda engine needs."),
    ] = "bpmn",
    catalog_dir: Annotated[
        str | None,
        typer.Option(
            "--catalog", help="The catalog a planned workflow uses, to resolve its calls."
        ),
    ] = None,
    out: Annotated[
        Path | None, typer.Option("--out", "-o", help="Where to write it. Default: print it.")
    ] = None,
) -> None:
    """Compile a workflow into BPMN 2.0 or a UiPath workflow (.xaml)."""
    target, workflow, catalog = _load(source, capability, catalog_dir)
    compiled = compile_workflow(workflow, target, to=to, catalog=catalog, engine=engine)
    for warning in compiled.warnings:
        errors.print(f"  [yellow]warning[/] {escape(warning)}")
    if out is None:
        typer.echo(compiled.text, nl=False)
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(compiled.text, encoding="utf-8", newline="\n")
    console.print(f"[bold green]Compiled[/] {escape(target.id)} into {escape(str(out))}")


def _load(
    source: str, capability: str | None, catalog_dir: str | None
) -> tuple[Capability, Workflow, Catalog | None]:
    path = Path(source)
    if path.suffix.lower() in {".yaml", ".yml"} and path.is_file():
        try:
            target, workflow = load_planned(path)
        except FlowGlyphError as error:
            fail(error)
        catalog = open_catalog(catalog_dir) if catalog_dir else None
        return target, workflow, catalog
    if capability is None:
        fail("name the workflow to compile: flowglyph compile CATALOG CAPABILITY --to bpmn")
    catalog = open_catalog(source)
    try:
        target = catalog.get(capability)
        workflow = catalog.workflow(capability)
    except FlowGlyphError as error:
        fail(error)
    return target, workflow, catalog
