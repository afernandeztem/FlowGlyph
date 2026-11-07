"""Describing what sources left undescribed, with a language model, once."""

import importlib
from pathlib import Path
from typing import Annotated

import typer
from rich.markup import escape
from rich.table import Table

import flowglyph
from flowglyph import enrichment
from flowglyph.cli._shared import console, errors, fail
from flowglyph.errors import FlowGlyphError


def enrich(
    catalog_dir: Annotated[Path, typer.Argument(help="A directory written by `extract`.")],
    *,
    via: Annotated[
        str,
        typer.Option(
            help="Who writes the descriptions: anthropic, claude-code, codex, gemini, cursor, "
            "openai-compatible, as for `flowglyph plan`."
        ),
    ] = "anthropic",
    model: Annotated[str | None, typer.Option(help="Model name, if the backend needs one.")] = None,
    effort: Annotated[
        str | None, typer.Option(help="Reasoning effort, for backends that support it.")
    ] = None,
    limit: Annotated[
        int | None, typer.Option(help="Ask about at most this many capabilities in this run.")
    ] = None,
) -> None:
    """Describe the capabilities sources left without a description or business meaning.

    Answers are cached in flowglyph.enrichment.json next to the catalog and reused by every
    later `extract` into it, so a model is asked about each capability once per source change.
    """
    if not (catalog_dir / "catalog.jsonl").is_file():
        fail(f"{catalog_dir} has no catalog; run `flowglyph extract` first")
    backends = importlib.import_module("flowglyph.planner.backends")
    try:
        backend = backends.planner_backend(via, model, effort)
    except ModuleNotFoundError as error:
        if error.name != "anthropic":
            raise
        fail("the anthropic backend needs: pip install 'flowglyph[llm]'")
    except FlowGlyphError as error:
        fail(error)
    if not hasattr(backend, "answer"):
        fail(f"the {via} backend can plan but not describe; pick a built-in backend")
    catalog = flowglyph.load_catalog(catalog_dir)
    cache_file = catalog_dir / enrichment.ENRICHMENT_FILE
    cache = enrichment.Cache.load(cache_file)
    try:
        result = enrichment.enrich(catalog, backend, cache, model_name=model or via, limit=limit)
    except FlowGlyphError as error:
        fail(error)
    cache.save(cache_file)
    result.catalog.save(catalog_dir)
    table = Table(box=None)
    table.add_column("Capability", overflow="fold")
    table.add_column("Description")
    for capability_id in result.asked:
        written = result.catalog.capabilities[capability_id]
        if "description" in written.generated:
            table.add_row(escape(capability_id), escape(written.description))
    if result.asked:
        console.print(table)
    for capability_id in result.unanswered:
        errors.print(f"  [yellow]warning[/] no answer for {escape(capability_id)}")
    console.print(
        f"[bold green]Enriched[/] {len(result.asked) - len(result.unanswered)} capabilities, "
        f"reused {len(result.reused)} cached answers; written to {escape(str(cache_file))}"
    )
