"""Running the MCP gateway and deciding on the runs its policy holds back."""

import asyncio
import getpass
import importlib
import json
import os
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Annotated, Any, Literal

import typer
from rich.markup import escape
from rich.table import Table

from flowglyph.cli._shared import console, errors, fail
from flowglyph.errors import FlowGlyphError

if TYPE_CHECKING:
    from flowglyph.gateway.executors import Executor
    from flowglyph.gateway.ledger import Ledger

_VALUE_WIDTH = 40


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
    connections: Annotated[
        Path | None,
        typer.Option(
            help="Run capabilities for real against the systems in this connections file. "
            "Without it, every run is a dry run."
        ),
    ] = None,
) -> None:
    """Serve the catalog to agents as an MCP server over stdio."""
    gateway = _gateway_module()
    server = _import("flowglyph.gateway.server")
    if not (catalog_dir / "catalog.jsonl").is_file():
        fail(f"{catalog_dir} has no catalog; run `flowglyph extract`")
    rules = gateway.Policy.load(policy) if policy else gateway.DEFAULT_POLICY
    executor = _executor(connections)
    instance = gateway.Gateway(catalog_dir, policy=rules, state_dir=state, executor=executor)
    how = "dry runs" if connections is None else f"connections in {escape(str(connections))}"
    errors.print(f"flowglyph gateway serving {escape(str(catalog_dir))} over stdio, {how}")
    asyncio.run(server.serve_stdio(instance, expose))


def approve(
    catalog_dir: Annotated[Path, typer.Argument(help="The catalog the gateway serves.")],
    key: Annotated[str, typer.Argument(help="Idempotency key of the run to approve.")],
    state: Annotated[Path | None, typer.Option(help="The gateway's state directory.")] = None,
) -> None:
    """Approve a run that a policy held back, so the agent's next attempt executes it."""
    gateway = _gateway_module().Gateway(catalog_dir, state_dir=state)
    run = gateway.approve(key, actor=getpass.getuser())
    if run is None:
        fail(f"no run is waiting for approval under {key!r}", code=1)
    console.print(f"[bold green]Approved[/] {escape(key)}: {escape(run.capability)}")


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
    table.add_column("Arguments", no_wrap=True, overflow="ellipsis")
    for run in pending:
        arguments = _arguments_line(run.arguments)
        table.add_row(escape(run.key), escape(run.capability), run.version, escape(arguments))
    console.print(table)


def _arguments_line(arguments: dict[str, Any] | None) -> str:
    """The arguments of a run on one line, each value cut so a person can scan the table."""
    if arguments is None:
        return "(not recorded)"
    parts: list[str] = []
    for name, value in arguments.items():
        text = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        if len(text) > _VALUE_WIDTH:
            text = text[: _VALUE_WIDTH - 3] + "..."
        parts.append(f"{name}={text}")
    return ", ".join(parts)


def _executor(connections: Path | None) -> "Executor | None":
    """The connected executor for `connections`, after checking its credentials are present."""
    if connections is None:
        return None
    executors = importlib.import_module("flowglyph.gateway.executors")
    try:
        loaded = executors.Connections.load(connections)
    except FlowGlyphError as error:
        fail(error)
    missing = sorted(
        variable
        for variables in loaded.variables().values()
        for variable in variables
        if not os.environ.get(variable)
    )
    if missing:
        fail(f"set these environment variables before serving: {', '.join(missing)}")
    return executors.ConnectedExecutor(loaded)


def _gateway_module() -> ModuleType:
    """The gateway package, imported late so the CLI works without the `[mcp]` extra."""
    return _import("flowglyph.gateway")


def _import(name: str) -> ModuleType:
    try:
        return importlib.import_module(name)
    except FlowGlyphError as error:
        fail(error)
    except ModuleNotFoundError as error:
        if error.name not in {"mcp", "mcp_types", "jsonschema"}:
            raise
        fail("the gateway needs extra packages: pip install 'flowglyph[mcp]'")


def _ledger(catalog_dir: Path, state: Path | None) -> "Ledger":
    gateway = _gateway_module()
    return gateway.Ledger((state or catalog_dir / ".flowglyph") / "ledger.sqlite")
