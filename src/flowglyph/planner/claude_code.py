import json
import shutil
import subprocess
from collections.abc import Sequence
from typing import Any, Literal

from pydantic import ValidationError

from flowglyph.planner import PlannerError
from flowglyph.planner.model import Plan
from flowglyph.planner.prompt import SYSTEM_PROMPT, request_text

DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_TIMEOUT_SECONDS = 600

type Effort = Literal["low", "medium", "high", "xhigh", "max"]


class ClaudeCodePlanModel:
    """Proposes plans through the Claude Code CLI in headless mode.

    The request runs as `claude -p` with structured output, no tools and no MCP servers, so it
    uses whatever account Claude Code is signed in with, a subscription included, instead of
    an API key. It needs Claude Code installed and signed in on the machine running the
    planner, which makes it a fit for local use rather than servers or CI.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        *,
        effort: Effort = "high",
        executable: str = "claude",
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Configure the CLI call."""
        self.model = model
        self.effort: Effort = effort
        self.executable = executable
        self.timeout_seconds = timeout_seconds

    def command(self) -> list[str]:
        """The command line that is run, without the prompt, which goes through stdin."""
        return [
            self.executable,
            "--print",
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(Plan.model_json_schema()),
            "--model",
            self.model,
            "--effort",
            self.effort,
            "--system-prompt",
            SYSTEM_PROMPT,
            "--tools",
            "",
            "--strict-mcp-config",
            "--no-session-persistence",
        ]

    def propose(self, requirements: str, candidates: Sequence[dict[str, Any]]) -> Plan:
        """Ask Claude Code for a plan.

        Raises:
            PlannerError: If Claude Code is missing, not signed in, fails or returns no plan.
        """
        executable = shutil.which(self.executable)
        if executable is None:
            raise PlannerError(f"Claude Code CLI not found: {self.executable!r} is not on PATH")
        try:
            completed = subprocess.run(
                [executable, *self.command()[1:]],
                input=request_text(requirements, candidates),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise PlannerError(f"Claude Code did not answer in {self.timeout_seconds}s") from error
        return _parse(completed.stdout, completed.stderr)


def _parse(stdout: str, stderr: str) -> Plan:
    try:
        envelope: dict[str, Any] = json.loads(stdout)
    except json.JSONDecodeError as error:
        detail = (stderr or stdout).strip()[:300]
        raise PlannerError(f"Claude Code returned no JSON result: {detail}") from error
    if envelope.get("is_error"):
        message = str(envelope.get("result") or envelope.get("subtype") or "unknown error")
        if "authenticate" in message.lower() or "login" in message.lower():
            message += "; sign in with `claude auth login`"
        raise PlannerError(f"Claude Code failed: {message}")
    structured = envelope.get("structured_output")
    if structured is None:
        try:
            structured = json.loads(str(envelope.get("result", "")))
        except json.JSONDecodeError as error:
            raise PlannerError("Claude Code did not return a structured plan") from error
    try:
        return Plan.model_validate(structured)
    except ValidationError as error:
        raise PlannerError(f"Claude Code returned an invalid plan: {error}") from error
