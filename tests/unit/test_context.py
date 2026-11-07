"""Context files for coding agents: read from the sources, within budget, safe to regenerate."""

import re
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

import flowglyph
from flowglyph import context
from flowglyph.cli.main import app

FIXTURES = Path(__file__).parents[1] / "fixtures"
PLACEHOLDER = re.compile(r"^[a-z][A-Za-z0-9]*$")


@pytest.fixture
def project(tmp_path: Path) -> Path:
    return shutil.copytree(FIXTURES / "reframework", tmp_path / "ReFrameWork")


@pytest.fixture
def files(project: Path) -> dict[str, str]:
    (found,) = context.projects(project.parent)
    return context.project_files(flowglyph.extract(project.parent), found)


def test_the_document_follows_the_project_context_sections(files: dict[str, str]):
    document = files[context.AGENTS_FILE]
    assert document == files[context.RULES_FILE]
    assert document.startswith("<!-- discovery-metadata: cs=0 xaml=13 deps=0 -->\n")
    headings = re.findall(r"^## (.+)$", document, flags=re.MULTILINE)
    assert headings[:4] == ["Overview", "Project Structure", "Entry Points", "Key Workflows"]
    assert {"Effects and Retry Safety", "Call Tree", "Activity Cards", "Quick Reference"} <= set(
        headings
    )
    assert len(document.splitlines()) <= 200


def test_facts_are_exact(files: dict[str, str]):
    document = files[context.AGENTS_FILE]
    assert "| `Main.xaml` | `in_OrchestratorQueueName`: string or null | none |" in document
    assert "| `Framework/GetTransactionData.xaml` | RWX | none | review |" in document
    assert "Robotic Enterprise Framework" in document
    assert "└── SetTransactionStatus (RWdX, none)\n    └── TakeScreenshot" in document


def test_activity_cards_carry_templates_with_placeholders_only(files: dict[str, str]):
    card = files[f"{context.CARDS_DIRECTORY}/GetQueueItem.md"]
    assert 'QueueType="[queueType]"' in card
    assert 'xmlns:ui="http://schemas.uipath.com/workflow/activities"' in card
    templates = [
        capability.input_schema["x-xaml-template"]["xml"]
        for capability in flowglyph.extract(FIXTURES / "reframework")
        if "x-xaml-template" in capability.input_schema
    ]
    assert len(templates) > 30
    for xml in templates:
        for value in re.findall(r'="\[([^\]]*)\]"|>\[([^\]]*)\]<', xml):
            assert PLACEHOLDER.match("".join(value)), xml


def test_notes_are_kept_and_foreign_files_are_not_overwritten(project: Path, files: dict[str, str]):
    written = context.write(project, files)
    assert {item.action for item in written} == {"created"}
    agents = project / context.AGENTS_FILE
    agents.write_text(agents.read_text(encoding="utf-8") + "Runs from the Finance folder.\n")
    assert {item.action for item in context.write(project, files)} == {"unchanged"}
    assert agents.read_text(encoding="utf-8").endswith("Runs from the Finance folder.\n")
    rules = project / context.RULES_FILE
    rules.write_text("# written by a person\n", encoding="utf-8")
    kept = [item for item in context.write(project, files) if item.path == rules]
    assert kept[0].action.startswith("kept")
    assert rules.read_text(encoding="utf-8") == "# written by a person\n"
    context.write(project, files, force=True)
    assert context.MARKER in rules.read_text(encoding="utf-8")


def test_the_command_writes_into_each_project_or_elsewhere(project: Path, tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(app, ["context", str(project.parent)], terminal_width=200)
    assert result.exit_code == 0, result.output
    assert (project / "AGENTS.md").is_file()
    assert (project / ".flowglyph" / "activities" / "GetQueueItem.md").is_file()
    out = tmp_path / "out"
    result = runner.invoke(app, ["context", str(project.parent), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert (out / "ReFrameWork" / ".claude" / "rules" / "project-context.md").is_file()
    empty = tmp_path / "empty"
    empty.mkdir()
    result = runner.invoke(app, ["context", str(empty)])
    assert result.exit_code == 2
    assert "no UiPath project" in result.output
