"""Where plans come from: built-in backends plus any registered by other packages.

A backend is a factory `(model, effort) -> PlanModel`. Packages add their own under the
`flowglyph.planners` entry point group, so a planner on any SDK or local model plugs in
without changes to FlowGlyph.
"""

from collections.abc import Callable
from importlib.metadata import entry_points
from typing import cast

from flowglyph.planner import PlanModel, PlannerError

type PlannerFactory = Callable[[str | None, str | None], PlanModel]


def _anthropic(model: str | None, effort: str | None) -> PlanModel:
    from flowglyph.planner.claude import DEFAULT_MODEL, ClaudePlanModel, Effort  # noqa: PLC0415

    return ClaudePlanModel(model or DEFAULT_MODEL, effort=cast("Effort", effort or "high"))


def _claude_code(model: str | None, effort: str | None) -> PlanModel:
    from flowglyph.planner.claude_code import DEFAULT_MODEL, ClaudeCodePlanModel  # noqa: PLC0415

    return ClaudeCodePlanModel(model or DEFAULT_MODEL, effort=effort or "high")


def _preset(name: str) -> PlannerFactory:
    def factory(model: str | None, effort: str | None) -> PlanModel:
        from flowglyph.planner.command import CommandPlanModel  # noqa: PLC0415

        del effort
        return CommandPlanModel(name, model=model)

    return factory


def _openai_compatible(model: str | None, effort: str | None) -> PlanModel:
    from flowglyph.planner.openai_compatible import OpenAICompatiblePlanModel  # noqa: PLC0415

    del effort
    if not model:
        raise PlannerError("the openai-compatible backend needs --model, for example llama3.1")
    return OpenAICompatiblePlanModel(model)


BUILT_IN: dict[str, PlannerFactory] = {
    "anthropic": _anthropic,
    "claude-code": _claude_code,
    "codex": _preset("codex"),
    "gemini": _preset("gemini"),
    "cursor": _preset("cursor"),
    "openai-compatible": _openai_compatible,
}
ALIASES = {"api": "anthropic"}


def available_planners() -> dict[str, PlannerFactory]:
    """Every backend that can be selected, built-in first, then installed plugins."""
    planners = dict(BUILT_IN)
    for entry_point in entry_points(group="flowglyph.planners"):
        planners[entry_point.name] = entry_point.load()
    return planners


def planner_backend(name: str, model: str | None = None, effort: str | None = None) -> PlanModel:
    """Instantiate the backend registered as `name`.

    Raises:
        PlannerError: If no backend has that name.
    """
    planners = available_planners()
    key = ALIASES.get(name, name)
    if key not in planners:
        raise PlannerError(f"unknown planner {name!r}; available: {', '.join(sorted(planners))}")
    return planners[key](model, effort)
