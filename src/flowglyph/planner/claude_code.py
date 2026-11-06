"""Planning through the Claude Code CLI with the account it is signed in with."""

from dataclasses import replace

from flowglyph.planner.command import (
    DEFAULT_TIMEOUT_SECONDS,
    PRESETS,
    CommandPlanModel,
)

DEFAULT_MODEL = "claude-opus-5-5"


class ClaudeCodePlanModel(CommandPlanModel):
    """Proposes plans through the Claude Code CLI with the account it is signed in with.

    Runs `claude --print` with the plan's JSON Schema as structured output, no tools and no MCP
    servers. `--bare` is deliberately not used: it would ignore the signed-in account.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        *,
        effort: str = "high",
        executable: str = "claude",
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Configure the CLI call."""
        spec = replace(PRESETS["claude-code"], argv=(executable, *PRESETS["claude-code"].argv[1:]))
        super().__init__(spec, model=model, effort=effort, timeout_seconds=timeout_seconds)
