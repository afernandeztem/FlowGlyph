"""The plan an LLM proposes, and the strict JSON Schema every backend must follow."""

from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field

type JsonType = Literal["string", "number", "integer", "boolean", "object", "array"]


class _PlanModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlannedInput(_PlanModel):
    """A value the workflow needs from whoever runs it."""

    name: str = Field(description="snake_case name of the workflow input")
    type: JsonType
    description: str


class PlannedArgument(_PlanModel):
    """Where one argument of a step comes from."""

    name: str = Field(description="exact input name of the chosen capability")
    source: Literal["workflow_input", "step_output", "literal"]
    value: str = Field(
        description=(
            "workflow_input: the input name; step_output: '<step id>.<output name>'; "
            "literal: the value as JSON text"
        )
    )


class PlannedStep(_PlanModel):
    """One step of the plan, bound to a catalog capability when one fits."""

    id: str = Field(description="short snake_case id, unique in the plan")
    intent: str = Field(description="what the step must achieve, in one sentence")
    capability: str | None = Field(
        description="id of a candidate capability, or null when none of them fits"
    )
    arguments: list[PlannedArgument]
    after: list[str] = Field(description="ids of steps that must finish first")
    condition: str | None = Field(
        description="expression over inputs and earlier outputs that gates this step, or null"
    )
    join: Literal["all", "any"] = Field(
        default="all",
        description=(
            "all: run only if every step in `after` ran; any: run if at least one did. "
            "Use any where an optional, conditional step rejoins the main path."
        ),
    )


class Plan(_PlanModel):
    """What the language model proposes. Nothing in it is trusted until resolved."""

    goal: str = Field(description="the outcome of the workflow, in a few words")
    inputs: list[PlannedInput]
    steps: list[PlannedStep]
    assumptions: list[str] = Field(description="anything assumed that the requirements left open")


def plan_json_schema() -> dict[str, Any]:
    """JSON Schema of `Plan` in the strict form most structured-output APIs require."""
    return strict_json_schema(Plan)


def strict_json_schema(shape: type[BaseModel]) -> dict[str, Any]:
    """JSON Schema of `shape` in the strict form most structured-output APIs require.

    Every property is listed as required and objects reject unknown keys, which OpenAI's strict
    mode demands and Anthropic, Gemini and local servers accept.
    """
    return _strict(shape.model_json_schema())


def _strict(node: Any) -> Any:
    if isinstance(node, list):
        return [_strict(item) for item in cast("list[Any]", node)]
    if not isinstance(node, dict):
        return node
    schema = {
        key: _strict(value)
        for key, value in cast("dict[str, Any]", node).items()
        if key != "default"
    }
    if schema.get("type") == "object" and "properties" in schema:
        schema["required"] = list(schema["properties"])
        schema["additionalProperties"] = False
    return schema
