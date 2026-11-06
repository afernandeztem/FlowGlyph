"""Running the MCP gateway and deciding on the runs its policy holds back."""

import asyncio
import importlib
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Annotated, Literal

import typer
from rich.markup import escape
from rich.table import Table

from flowglyph.cli._shared import console, errors, fail

if TYPE_CHECKING:
    from flowglyph.gateway.ledger import Ledger


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
        fail(f"{catalog_dir} has no catalog; run `flowglyph extract`")
    rules = gateway.Policy.load(policy) if policy else gateway.DEFAULT_POLICY
    instance = gateway.Gateway(catalog_dir, policy=rules, state_dir=state)
    errors.print(
        f"flowglyph gateway serving {escape(str(catalog_dir))} over stdio (dry-run executor)"
    )
    asyncio.run(server.serve_stdio(instance, expose))


def approve(
    catalog_dir: Annotated[Path, typer.Argument(help="The catalog the gateway serves.")],
    key: Annotated[str, typer.Argument(help="Idempotency key of the run to approve.")],
    state: Annotated[Path | None, typer.Option(help="The gateway's state directory.")] = None,
) -> None:
    """Approve a run that a policy held back, so the agent's next attempt executes it."""
    ledger = _ledger(catalog_dir, state)
    if not ledger.approve(key):
        fail(f"no run is waiting for approval under {key!r}", code=1)
    console.print(f"[bold green]Approved[/] {escape(key)}")


def approvals(
    catalog_dir: Annotated[Path, typer.Argument(help="The catalog the gateway serves.")],
    state: Annotated[Path | None, typer.Option(help="The gateway's state directory.")] = None,
) -> None:
    """List runs waiting for a person to approve them."""
    pending = _ledger(catalog_dir, state).pending_approvals()
    if not pending:
        console.print("Nothing is waiting for approval.")
        return
    table = Table(box=None)
    table.add_column("Key", overflow="fold")
    table.add_column("Capability", overflow="fold")
    table.add_column("Version", no_wrap=True)
    for run in pending:
        table.add_row(escape(run.key), escape(run.capability), run.version)
    console.print(table)


def _gateway_module() -> ModuleType:
    """The gateway package, imported late so the CLI works without the `[mcp]` extra."""
    try:
        return importlib.import_module("flowglyph.gateway")
    except ModuleNotFoundError as error:
        if error.name not in {"mcp", "mcp_types", "jsonschema"}:
            raise
        fail("the gateway needs: pip install 'flowglyph[mcp]'")


def _ledger(catalog_dir: Path, state: Path | None) -> "Ledger":
    gateway = _gateway_module()
    return gateway.Ledger((state or catalog_dir / ".flowglyph") / "ledger.sqlite")
