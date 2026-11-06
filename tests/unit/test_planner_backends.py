import json
import stat
import sys
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

from flowglyph.planner import PlannerError
from flowglyph.planner.backends import available_planners, planner_backend
from flowglyph.planner.command import PRESETS, CommandPlanModel, CommandSpec
from flowglyph.planner.model import Plan, plan_json_schema
from flowglyph.planner.openai_compatible import OpenAICompatiblePlanModel

PLAN = {
    "goal": "List invoices",
    "inputs": [],
    "steps": [
        {
            "id": "list",
            "intent": "List draft invoices",
            "capability": "openapi/Payments_API/listInvoices",
            "arguments": [],
            "after": [],
            "condition": None,
            "join": "all",
        }
    ],
    "assumptions": [],
}

RECORDER = """
import json, sys, pathlib
argv = sys.argv[1:]
pathlib.Path(sys.argv[0]).with_name("call.json").write_text(
    json.dumps({"argv": argv, "stdin": sys.stdin.read()})
)
"""


def executable(directory: Path, name: str, body: str) -> Path:
    script = directory / name
    script.write_text(f"#!{sys.executable}\n{RECORDER}\n{body}\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def on_path(monkeypatch: pytest.MonkeyPatch, directory: Path) -> None:
    monkeypatch.setenv("PATH", f"{directory}:{Path(sys.executable).parent}")


def recorded(directory: Path) -> dict[str, Any]:
    return json.loads((directory / "call.json").read_text())


def test_the_schema_is_strict_everywhere():
    def check(node: object) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                assert set(node["required"]) == set(node["properties"])
                assert node["additionalProperties"] is False
            assert "default" not in node
            for value in node.values():
                check(value)
        elif isinstance(node, list):
            for item in node:
                check(item)

    schema = plan_json_schema()
    check(schema)
    assert "join" in schema["$defs"]["PlannedStep"]["required"]


def test_codex_writes_the_plan_to_the_output_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    executable(
        tmp_path,
        "codex",
        "out = argv[argv.index('-o') + 1]\n"
        f"pathlib.Path(out).write_text({json.dumps(json.dumps(PLAN))})\n"
        "print('done')",
    )
    on_path(monkeypatch, tmp_path)
    plan = CommandPlanModel("codex", model="gpt-5-codex").propose("List drafts.", [])
    assert plan == Plan.model_validate(PLAN)
    call = recorded(tmp_path)
    argv = call["argv"]
    assert argv[:4] == ["--model", "gpt-5-codex", "exec", "--skip-git-repo-check"]
    assert argv[argv.index("--sandbox") + 1] == "read-only"
    assert argv[-1] == "-"
    assert "You design automation workflows" in call["stdin"]


def test_gemini_answers_inside_a_markdown_fence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    fenced = "Here is the plan:\n```json\n" + json.dumps(PLAN) + "\n```"
    executable(tmp_path, "gemini", f"print(json.dumps({{'response': {fenced!r}}}))")
    on_path(monkeypatch, tmp_path)
    assert CommandPlanModel("gemini").propose("List drafts.", []).goal == "List invoices"
    assert "validates against this JSON Schema" in recorded(tmp_path)["stdin"]


def test_login_problems_say_how_to_sign_in(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    executable(
        tmp_path,
        "cursor-agent",
        "print(json.dumps({'is_error': True, 'result': 'Not logged in'}))",
    )
    on_path(monkeypatch, tmp_path)
    with pytest.raises(PlannerError, match="cursor-agent login"):
        CommandPlanModel("cursor").propose("x", [])


def test_any_other_tool_can_be_described(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    executable(tmp_path, "my-assistant", f"print({json.dumps(json.dumps(PLAN))})")
    on_path(monkeypatch, tmp_path)
    spec = CommandSpec(name="mine", argv=("my-assistant", "--json"), schema_in_prompt=True)
    assert CommandPlanModel(spec).propose("x", []).steps[0].id == "list"
    assert recorded(tmp_path)["argv"] == ["--json"]


def test_presets_exist_for_common_assistants():
    assert set(PRESETS) == {"claude-code", "codex", "gemini", "cursor"}


class _Server:
    def __init__(self, status: int, reply: dict[str, Any]) -> None:
        self.status = status
        self.reply = reply
        self.requests: list[tuple[dict[str, str], dict[str, Any]]] = []


@pytest.fixture
def server() -> Iterator[tuple[str, _Server]]:
    state = _Server(200, {})

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            state.requests.append((dict(self.headers), json.loads(self.rfile.read(length))))
            body = json.dumps(state.reply).encode()
            self.send_response(state.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            del format, args

    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/v1", state
    httpd.shutdown()


def reply(content: str | None, refusal: str | None = None) -> dict[str, Any]:
    return {"choices": [{"message": {"role": "assistant", "content": content, "refusal": refusal}}]}


def test_openai_compatible_servers(server: tuple[str, _Server]):
    url, state = server
    state.reply = reply(json.dumps(PLAN))
    model = OpenAICompatiblePlanModel("llama3.1", base_url=url, api_key="local-key")
    assert model.propose("List drafts.", [{"id": "x"}]).goal == "List invoices"
    headers, body = state.requests[0]
    assert headers["Authorization"] == "Bearer local-key"
    assert body["model"] == "llama3.1"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert body["messages"][0]["role"] == "system"


@pytest.mark.parametrize(
    ("status", "body", "message"),
    [
        (200, reply(None, refusal="no"), "declined"),
        (200, reply("not a plan"), "invalid plan"),
        (400, {"error": "bad model"}, "rejected the request"),
        (200, {"choices": []}, "no message"),
    ],
)
def test_openai_compatible_failures(
    server: tuple[str, _Server], status: int, body: dict[str, Any], message: str
):
    url, state = server
    state.status, state.reply = status, body
    with pytest.raises(PlannerError, match=message):
        OpenAICompatiblePlanModel("m", base_url=url, api_key="").propose("x", [])


def test_unreachable_servers_are_reported():
    model = OpenAICompatiblePlanModel("m", base_url="http://127.0.0.1:9", api_key="")
    with pytest.raises(PlannerError, match="could not reach"):
        model.propose("x", [])


def test_backends_are_selected_by_name():
    assert {"anthropic", "claude-code", "codex", "gemini", "cursor", "openai-compatible"} <= set(
        available_planners()
    )
    assert isinstance(planner_backend("codex"), CommandPlanModel)
    with pytest.raises(PlannerError, match="needs --model"):
        planner_backend("openai-compatible")
    with pytest.raises(PlannerError, match="unknown planner 'nope'"):
        planner_backend("nope")


def test_plugins_register_through_entry_points(monkeypatch: pytest.MonkeyPatch):
    from flowglyph.planner import backends  # noqa: PLC0415

    def factory(model: str | None, effort: str | None) -> str:
        return f"planner for {model}"

    class EntryPoint:
        name = "my-sdk"

        @staticmethod
        def load() -> object:
            return factory

    def entry_points(group: str) -> list[EntryPoint]:
        return [EntryPoint()] if group == "flowglyph.planners" else []

    monkeypatch.setattr(backends, "entry_points", entry_points)
    assert backends.planner_backend("my-sdk", "x1") == "planner for x1"


@pytest.mark.parametrize("url", ["file:///etc", "ftp://example.com/v1", "localhost:11434/v1"])
def test_openai_compatible_backends_only_speak_http(url: str):
    with pytest.raises(PlannerError, match="http or https"):
        OpenAICompatiblePlanModel("llama3.1", base_url=url)
