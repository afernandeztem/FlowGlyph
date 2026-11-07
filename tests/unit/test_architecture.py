"""The dependency rules of docs/architecture.md, checked on the source tree."""

import ast
from pathlib import Path

import pytest

SOURCE = Path(__file__).parents[2] / "src" / "flowglyph"

ALLOWED: dict[str, set[str]] = {
    "ir": set(),
    "errors": set(),
    "views": {"ir"},
    "sources": {"errors"},
    "_internal": {"ir", "views", "errors"},
    "adapters": {"ir", "errors", "_internal"},
    "catalog": {"ir", "errors", "_internal", "adapters", "sources"},
    "report": {"ir", "views", "catalog"},
    "wiki": {"ir", "views", "_internal", "catalog", "report"},
    "gateway": {"ir", "views", "errors", "_internal", "catalog"},
    "planner": {"ir", "views", "errors", "_internal", "catalog"},
    "compilers": {"ir", "errors", "catalog"},
    "enrichment": {"ir", "views", "catalog", "planner"},
    "context": {"ir", "views", "catalog", "report", "adapters"},
}


def _context(module: str) -> str:
    parts = module.split(".")
    return parts[1] if len(parts) > 1 else "flowglyph"


def _runtime_imports(tree: ast.Module) -> set[str]:
    """Modules imported when the file runs, leaving out `if TYPE_CHECKING:` blocks."""
    type_only = {
        id(child)
        for node in ast.walk(tree)
        if isinstance(node, ast.If) and ast.unparse(node.test).endswith("TYPE_CHECKING")
        for statement in node.body
        for child in ast.walk(statement)
    }
    found: set[str] = set()
    for node in ast.walk(tree):
        if id(node) in type_only or not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        if node.module == "flowglyph":
            found.update(f"flowglyph.{alias.name}" for alias in node.names)
        elif node.module.startswith("flowglyph."):
            found.add(node.module)
    return found


def _imports_by_context() -> dict[str, set[str]]:
    contexts: dict[str, set[str]] = {}
    for file in SOURCE.rglob("*.py"):
        module = file.relative_to(SOURCE).with_suffix("")
        context = "flowglyph" if module == Path("__init__") else module.parts[0]
        imported = {_context(module) for module in _runtime_imports(ast.parse(file.read_text()))}
        contexts.setdefault(context, set()).update(imported - {context})
    return contexts


@pytest.mark.parametrize("context", sorted(ALLOWED))
def test_contexts_depend_only_on_what_the_architecture_allows(context: str):
    imported = _imports_by_context().get(context, set())
    assert imported <= ALLOWED[context], f"{context} imports {sorted(imported - ALLOWED[context])}"


def test_only_the_command_line_imports_the_command_line():
    importers = {name for name, imported in _imports_by_context().items() if "cli" in imported}
    assert importers <= {"cli", "__main__"}
