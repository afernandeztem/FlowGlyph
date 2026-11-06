import json
import os
import stat
import sys
from pathlib import Path

import pytest

from flowglyph.planner import PlannerError
from flowglyph.planner.claude_code import ClaudeCodePlanModel
from flowglyph.planner.model import Plan

# These tests fake each assistant with a script that starts with a shebang line, which only
# POSIX systems run. The code under test is the same on Windows, where batch-file safety is
# covered by test_batch_files_never_receive_cmd_syntax in test_planner_backends.py.
posix_only = pytest.mark.skipif(os.name == "nt", reason="fake tools are shebang scripts")

PLAN = {
    "goal": "Book invoice",
    "inputs": [{"name": "invoice", "type": "object", "description": "Invoice"}],
    "steps": [
        {
            "id": "book",
            "intent": "Book it",
            "capability": "uipath/Invoices/Steps/BookInvoice",
            "arguments": [{"name": "in_Invoice", "source": "workflow_input", "value": "invoice"}],
            "after": [],
            "condition": None,
        }
    ],
    "assumptions": [],
}


def fake_claude(directory: Path, envelope: object, *, raw: str | None = None) -> Path:
    """An executable that records how it was called and prints a canned CLI result."""
    output = raw if raw is not None else json.dumps(envelope)
    script = directory / "claude"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, sys, pathlib\n"
        "pathlib.Path(sys.argv[0]).with_name('call.json').write_text("
        "json.dumps({'argv': sys.argv[1:], 'stdin': sys.stdin.read()}))\n"
        f"print({output!r})\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def call(directory: Path) -> dict[str, object]:
    return json.loads((directory / "call.json").read_text())


@posix_only
def test_runs_headless_without_tools_and_reads_the_structured_output(tmp_path: Path):
    script = fake_claude(tmp_path, {"type": "result", "is_error": False, "structured_output": PLAN})
    plan = ClaudeCodePlanModel(executable=str(script), effort="medium").propose(
        "Book the invoice.", [{"id": "uipath/Invoices/Steps/BookInvoice"}]
    )
    assert plan == Plan.model_validate(PLAN)
    recorded = call(tmp_path)
    argv = recorded["argv"]
    assert isinstance(argv, list)
    assert "--bare" not in argv, "--bare would ignore the signed-in account"
    assert argv[argv.index("--tools") + 1] == ""
    assert argv[argv.index("--effort") + 1] == "medium"
    assert argv[argv.index("--model") + 1] == "claude-opus-5-5"
    schema = json.loads(argv[argv.index("--json-schema") + 1])
    assert schema["title"] == "Plan"
    assert "<requirements>\nBook the invoice.\n</requirements>" in str(recorded["stdin"])


@posix_only
def test_falls_back_to_a_json_result_text(tmp_path: Path):
    script = fake_claude(tmp_path, {"is_error": False, "result": json.dumps(PLAN)})
    assert ClaudeCodePlanModel(executable=str(script)).propose("x", []).goal == "Book invoice"


@posix_only
@pytest.mark.parametrize(
    ("envelope", "raw", "message"),
    [
        (
            {"is_error": True, "result": "Failed to authenticate: OAuth session expired"},
            None,
            "claude auth login",
        ),
        ({"is_error": False, "result": "Sure, here is a plan!"}, None, "structured plan"),
        ({"is_error": False, "structured_output": {"goal": 1}}, None, "invalid plan"),
        (None, "not json at all", "claude-code failed: not json at all"),
    ],
)
def test_failures_become_planner_errors(
    tmp_path: Path, envelope: object, raw: str | None, message: str
):
    script = fake_claude(tmp_path, envelope, raw=raw)
    with pytest.raises(PlannerError, match=message):
        ClaudeCodePlanModel(executable=str(script)).propose("x", [])


def test_missing_cli_is_explained(tmp_path: Path):
    with pytest.raises(PlannerError, match="not on PATH"):
        ClaudeCodePlanModel(executable=str(tmp_path / "nope")).propose("x", [])


@posix_only
def test_the_cli_can_plan_through_claude_code(
    tmp_path: Path, synthetic: Path, monkeypatch: pytest.MonkeyPatch
):
    from typer.testing import CliRunner  # noqa: PLC0415

    from flowglyph.cli.main import app  # noqa: PLC0415

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_claude(bin_dir, {"is_error": False, "structured_output": PLAN})
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    requirements = tmp_path / "requirements.md"
    requirements.write_text("Book the invoice.")
    result = CliRunner().invoke(
        app,
        [
            "plan",
            str(requirements),
            str(synthetic / "invoices"),
            "-o",
            str(tmp_path / "out"),
            "--via",
            "claude-code",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "out" / "workflow.ir.yaml").is_file()
