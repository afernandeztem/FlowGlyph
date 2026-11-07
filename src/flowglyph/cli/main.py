"""The `flowglyph` Typer application: global options and command registration."""

from typing import Annotated

import typer

import flowglyph
from flowglyph.cli._shared import console
from flowglyph.cli.commands import catalog, compile, explore, gateway, plan, wiki

app = typer.Typer(
    name="flowglyph",
    help="Turn enterprise automations into a vendor-neutral IR that agents can use safely.",
    no_args_is_help=True,
    add_completion=False,
)

for command in (
    catalog.extract,
    catalog.validate,
    catalog.diff,
    explore.inspect,
    explore.search,
    gateway.serve,
    gateway.approve,
    gateway.approvals,
    plan.plan,
    compile.compile,
    catalog.adapters,
    explore.idempotency,
):
    app.command()(command)
app.add_typer(wiki.app, name="wiki")


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
