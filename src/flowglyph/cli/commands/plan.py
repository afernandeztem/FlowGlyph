"""Designing a workflow from requirements with the planner."""

import importlib
from pathlib import Path
from typing import Annotated

import typer
from rich.markup import escape
from rich.table import Table

from flowglyph.cli._shared import SOURCE_HELP, console, errors, fail, open_catalog
from flowglyph.errors import FlowGlyphError


def plan(
    requirements: Annotated[
        Path,
        typer.Argument(
            help="The requirements: a text, Markdown, PDF, Word, Excel or CSV file, or a "
            "folder of them."
        ),
    ],
    catalog_dir: Annotated[str, typer.Argument(help=SOURCE_HELP)],
    *,
    out: Annotated[Path, typer.Option("--out", "-o", help="Where to write the plan.")] = Path(),
    via: Annotated[
        str,
        typer.Option(
            help="Who proposes the plan: anthropic (API key), claude-code, codex, gemini, "
            "cursor (the signed-in CLI), openai-compatible (OpenAI, Ollama, vLLM...) or an "
            "installed plugin."
        ),
    ] = "anthropic",
    model: Annotated[str | None, typer.Option(help="Model name, if the backend needs one.")] = None,
    effort: Annotated[
        str | None, typer.Option(help="Reasoning effort, for backends that support it.")
    ] = None,
) -> None:
    """Design a workflow from REQUIREMENTS using only capabilities in the catalog."""
    planner = importlib.import_module("flowglyph.planner")
    backends = importlib.import_module("flowglyph.planner.backends")
    try:
        backend = backends.planner_backend(via, model, effort)
    except ModuleNotFoundError as error:
        if error.name != "anthropic":
            raise
        fail("the anthropic planner needs: pip install 'flowglyph[llm]'")
    except FlowGlyphError as error:
        fail(error)
    documents = importlib.import_module("flowglyph.planner.documents")
    try:
        text = documents.read_requirements(requirements)
    except FlowGlyphError as error:
        fail(error)
    catalog = open_catalog(catalog_dir)
    try:
        outcome = planner.plan(text, catalog, backend)
    except FlowGlyphError as error:
        fail(error)
    proposal, result = outcome.save(out)
    table = Table(box=None)
    table.add_column("Step", no_wrap=True)
    table.add_column("Capability", overflow="fold")
    table.add_column("Intent")
    for step in outcome.plan.steps:
        resolved = step.id not in outcome.unresolved and step.capability
        capability = escape(step.capability) if resolved else "[red]missing[/]"
        table.add_row(escape(step.id), capability, escape(step.intent))
    console.print(f"[bold]{escape(outcome.plan.goal)}[/]")
    console.print(table)
    for problem in outcome.problems:
        errors.print(f"  [bold red]problem[/] {escape(problem)}")
    for warning in outcome.warnings:
        errors.print(f"  [yellow]warning[/] {escape(warning)}")
    console.print(f"Wrote {escape(str(proposal))} and {escape(str(result))}")
    if outcome.problems:
        raise typer.Exit(1)
