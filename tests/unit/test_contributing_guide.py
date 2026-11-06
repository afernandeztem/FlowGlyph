"""The code examples in CONTRIBUTING.md work as written."""

import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest

import flowglyph
from flowglyph.adapters import Adapter

GUIDE = Path(__file__).parents[2] / "CONTRIBUTING.md"


def _example(marker: str) -> dict[str, Any]:
    """Run the Python block that follows `<!-- marker -->` and return what it defines."""
    text = GUIDE.read_text(encoding="utf-8")
    block = text.split(f"<!-- {marker} -->\n```python\n", 1)[1].split("```", 1)[0]
    namespace: dict[str, Any] = {}
    exec(compile(block, str(GUIDE), "exec"), namespace)  # noqa: S102
    return namespace


def test_the_example_adapter_extracts_a_catalog(tmp_path: Path):
    (tmp_path / "jobs.yaml").write_text(
        "jobs:\n"
        "  - {name: close-books, schedule: '0 2 * * *', description: Close the ledger}\n"
        "  - {name: broken}\n",
        encoding="utf-8",
    )
    adapter: type[Adapter] = _example("adapter-example")["JobsAdapter"]
    assert isinstance(adapter(), Adapter)
    catalog = flowglyph.extract(tmp_path, adapter=adapter())
    job = catalog.get("jobs/close-books")
    assert job.trigger is not None
    assert job.trigger.kind == "schedule"
    assert [d.message for d in catalog.diagnostics] == ["broken has no schedule"]
    assert flowglyph.extract(tmp_path, adapter=adapter()).lock == catalog.lock


def test_the_example_planner_backend_returns_a_plan(monkeypatch: pytest.MonkeyPatch):
    sent: dict[str, Any] = {}

    def complete(**request: Any) -> str:
        sent.update(request)
        return json.dumps({"goal": "Close the books", "inputs": [], "steps": [], "assumptions": []})

    monkeypatch.setitem(sys.modules, "my_sdk", types.SimpleNamespace(complete=complete))
    namespace = _example("planner-example")
    backend = namespace["my_sdk_planner"](None, None)
    plan = backend.propose("Close the books every night.", [{"id": "jobs/close-books"}])
    assert plan.goal == "Close the books"
    assert sent["model"] == "my-default-model"
    assert "jobs/close-books" in sent["prompt"]
