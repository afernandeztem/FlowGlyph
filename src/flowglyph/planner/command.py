import json
import re
import shutil
import subprocess
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from pydantic import ValidationError

from flowglyph.planner import PlannerError
from flowglyph.planner.model import Plan, plan_json_schema
from flowglyph.planner.prompt import SYSTEM_PROMPT, request_text

DEFAULT_TIMEOUT_SECONDS = 600
_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)
_LOGIN_WORDS = ("auth", "login", "logged in", "log in", "sign in", "credential", "401")


@dataclass(frozen=True)
class CommandSpec:
    """How to run one coding assistant's command line headlessly.

    `argv` may contain `{schema}` (the JSON Schema text), `{schema_file}`, `{output_file}` and
    `{system}` placeholders. The prompt is written to stdin. The plan is read from
    `{output_file}` when `argv` uses it, otherwise from stdout, at `result_key` when stdout is
    a JSON envelope.
    """

    name: str
    argv: tuple[str, ...]
    model_args: tuple[str, ...] = ()
    effort_args: tuple[str, ...] = ()
    result_key: str | None = None
    error_key: str | None = None
    schema_in_prompt: bool = False
    system_in_prompt: bool = True
    login_hint: str = ""


PRESETS: dict[str, CommandSpec] = {
    "claude-code": CommandSpec(
        name="claude-code",
        argv=(
            "claude", "--print", "--output-format", "json", "--json-schema", "{schema}",
            "--system-prompt", "{system}", "--tools", "", "--strict-mcp-config",
            "--no-session-persistence",
        ),
        model_args=("--model", "{model}"),
        effort_args=("--effort", "{effort}"),
        result_key="structured_output",
        error_key="is_error",
        system_in_prompt=False,
        login_hint="sign in with `claude auth login`",
    ),
    "codex": CommandSpec(
        name="codex",
        argv=(
            "codex", "exec", "--skip-git-repo-check", "--sandbox", "read-only",
            "--output-schema", "{schema_file}", "-o", "{output_file}", "-",
        ),
        model_args=("--model", "{model}"),
        login_hint="sign in with `codex login`",
    ),
    "gemini": CommandSpec(
        name="gemini",
        argv=("gemini", "--output-format", "json"),
        model_args=("--model", "{model}"),
        result_key="response",
        schema_in_prompt=True,
        login_hint="sign in by running `gemini` once",
    ),
    "cursor": CommandSpec(
        name="cursor",
        argv=("cursor-agent", "--print", "--output-format", "json"),
        model_args=("--model", "{model}"),
        result_key="result",
        error_key="is_error",
        schema_in_prompt=True,
        login_hint="sign in with `cursor-agent login`",
    ),
}  # fmt: skip


class CommandPlanModel:
    """Proposes plans through any coding assistant that has a headless command line mode.

    The request uses the account the assistant is signed in with, subscriptions included, so
    no API key is needed. Presets cover Claude Code, Codex, Gemini CLI and Cursor; any other
    tool can be described with a `CommandSpec`.
    """

    def __init__(
        self,
        spec: CommandSpec | str,
        *,
        model: str | None = None,
        effort: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Configure the command; `spec` is a `CommandSpec` or the name of a preset."""
        self.spec = PRESETS[spec] if isinstance(spec, str) else spec
        self.model = model
        self.effort = effort
        self.timeout_seconds = timeout_seconds

    def command(self, schema_file: Path, output_file: Path) -> list[str]:
        """The command line that runs, without the prompt, which goes through stdin."""
        values = {
            "schema": json.dumps(plan_json_schema()),
            "schema_file": str(schema_file),
            "output_file": str(output_file),
            "system": SYSTEM_PROMPT,
            "model": self.model or "",
            "effort": self.effort or "",
        }
        argv = list(self.spec.argv)
        if self.model:
            argv[1:1] = self.spec.model_args
        if self.effort:
            argv[1:1] = self.spec.effort_args
        return [part.format_map(values) if "{" in part else part for part in argv]

    def prompt(self, requirements: str, candidates: Sequence[dict[str, Any]]) -> str:
        """The text written to the command's stdin."""
        parts = [SYSTEM_PROMPT] if self.spec.system_in_prompt else []
        parts.append(request_text(requirements, candidates))
        if self.spec.schema_in_prompt:
            parts.append(
                "Reply with a single JSON object, and nothing else, that validates against "
                f"this JSON Schema:\n{json.dumps(plan_json_schema())}"
            )
        return "\n\n".join(parts)

    def propose(self, requirements: str, candidates: Sequence[dict[str, Any]]) -> Plan:
        """Run the assistant and read back its plan.

        Raises:
            PlannerError: If the tool is missing, not signed in, fails or returns no plan.
        """
        executable = shutil.which(self.spec.argv[0])
        if executable is None:
            raise PlannerError(f"{self.spec.name}: {self.spec.argv[0]!r} is not on PATH")
        with tempfile.TemporaryDirectory(prefix="flowglyph-plan-") as scratch:
            schema_file = Path(scratch) / "plan.schema.json"
            output_file = Path(scratch) / "plan.json"
            schema_file.write_text(json.dumps(plan_json_schema()), encoding="utf-8")
            argv = self.command(schema_file, output_file)
            try:
                completed = subprocess.run(
                    [executable, *argv[1:]],
                    input=self.prompt(requirements, candidates),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    cwd=scratch,
                    check=False,
                )
            except subprocess.TimeoutExpired as error:
                raise PlannerError(
                    f"{self.spec.name} did not answer in {self.timeout_seconds}s"
                ) from error
            uses_file = any("{output_file}" in part for part in self.spec.argv)
            output = output_file.read_text(encoding="utf-8") if output_file.is_file() else ""
            if uses_file and not output:
                raise PlannerError(self._failure(completed.stderr or completed.stdout))
            return self._read(output if uses_file else completed.stdout, completed.stderr)

    def _read(self, stdout: str, stderr: str) -> Plan:
        payload: Any = _loads(stdout)
        if payload is None:
            raise PlannerError(self._failure(stderr or stdout))
        if isinstance(payload, dict):
            envelope = cast("dict[str, Any]", payload)
            if self.spec.error_key and envelope.get(self.spec.error_key):
                raise PlannerError(self._failure(str(envelope.get("result") or envelope)))
            if self.spec.result_key:
                payload = envelope.get(self.spec.result_key, envelope.get("result", envelope))
        if isinstance(payload, str):
            payload = _loads(payload)
        if payload is None:
            raise PlannerError(f"{self.spec.name} did not return a structured plan")
        try:
            return Plan.model_validate(payload)
        except ValidationError as error:
            raise PlannerError(f"{self.spec.name} returned an invalid plan: {error}") from error

    def _failure(self, detail: str) -> str:
        message = f"{self.spec.name} failed: {detail.strip()[:300] or 'no output'}"
        lowered = detail.lower()
        if self.spec.login_hint and any(word in lowered for word in _LOGIN_WORDS):
            message += f"; {self.spec.login_hint}"
        return message


def _loads(text: str) -> Any:
    """Parse JSON, also when a model wrapped it in prose or a Markdown fence."""
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = _JSON_OBJECT.search(stripped)
        if match is None:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
