"""Installing FlowGlyph's Agent Skill, so a coding agent knows when and how to use it."""

from importlib.resources import files
from pathlib import Path
from typing import Annotated

import typer
from rich.markup import escape

from flowglyph.cli._shared import console


def skill(
    to: Annotated[
        Path,
        typer.Option(help="Where to install it. Claude Code reads .claude/skills/ in a project."),
    ] = Path(".claude/skills/flowglyph"),
) -> None:
    """Install the FlowGlyph skill for coding agents (Claude Code, Codex, Cursor, Gemini CLI)."""
    text = files("flowglyph.skill").joinpath("SKILL.md").read_text(encoding="utf-8")
    to.mkdir(parents=True, exist_ok=True)
    target = to / "SKILL.md"
    target.write_text(text, encoding="utf-8", newline="\n")
    console.print(f"[bold green]Installed[/] the FlowGlyph skill in {escape(str(target))}")
