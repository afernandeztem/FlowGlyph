"""Every command and option the guide and the Agent Skill show exists in the command line."""

import re
from pathlib import Path
from typing import Any

import pytest
import typer

from flowglyph.cli.main import app

ROOT = Path(__file__).parents[2]
DOCUMENTS = (
    ROOT / "HOWTO.md",
    ROOT / "docs" / "guide.md",
    ROOT / "src" / "flowglyph" / "skill" / "SKILL.md",
)
_COMMAND = re.compile(r"(?<!import )(?<!from )flowglyph ((?:wiki )?[a-z]+)((?: [^\s`|]+)*)")


def _commands() -> dict[str, Any]:
    """Every command and subcommand, by the name a user types."""
    group: Any = typer.main.get_command(app)
    found: dict[str, Any] = {}
    for name, command in group.commands.items():
        if hasattr(command, "commands"):
            found.update({f"{name} {sub}": cmd for sub, cmd in command.commands.items()})
        else:
            found[name] = command
    return found


def _uses() -> list[tuple[str, list[str]]]:
    uses: list[tuple[str, list[str]]] = []
    for document in DOCUMENTS:
        for match in _COMMAND.finditer(document.read_text(encoding="utf-8")):
            words = match.group(2).split()
            options = [word.split("=")[0] for word in words if word.startswith("--")]
            uses.append((match.group(1), options))
    return uses


def test_the_guide_shows_commands():
    assert len(_uses()) > 20


@pytest.mark.parametrize(("command", "options"), _uses())
def test_guide_commands_exist(command: str, options: list[str]):
    commands = _commands()
    assert command in commands, f"the guide uses `flowglyph {command}`, which does not exist"
    declared = {option for parameter in commands[command].params for option in parameter.opts}
    missing = [option for option in options if option not in declared]
    assert not missing, f"`flowglyph {command}` has no {missing}"
