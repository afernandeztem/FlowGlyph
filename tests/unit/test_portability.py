"""Files FlowGlyph writes are byte-identical on every platform."""

import ast
from pathlib import Path

SOURCE = Path(__file__).parents[2] / "src" / "flowglyph"


def _text_writes_without_newline() -> list[str]:
    """`write_text(...)` and text-mode `open(...)` calls that leave line endings to the OS."""
    found: list[str] = []
    for file in sorted(SOURCE.rglob("*.py")):
        for node in ast.walk(ast.parse(file.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            keywords = {keyword.arg for keyword in node.keywords}
            name = node.func.attr
            mode = node.args[0] if node.args else None
            text_open = (
                name == "open"
                and isinstance(mode, ast.Constant)
                and isinstance(mode.value, str)
                and "b" not in mode.value
            )
            if (name == "write_text" or text_open) and "newline" not in keywords:
                found.append(f"{file.relative_to(SOURCE)}:{node.lineno}")
    return found


def test_every_text_write_sets_its_line_endings():
    assert _text_writes_without_newline() == []
