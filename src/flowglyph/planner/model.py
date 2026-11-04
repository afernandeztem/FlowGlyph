from typing import Literal

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


class Plan(_PlanModel):
    """What the language model proposes. Nothing in it is trusted until resolved."""

    goal: str = Field(description="the outcome of the workflow, in a few words")
    inputs: list[PlannedInput]
    steps: list[PlannedStep]
    assumptions: list[str] = Field(description="anything assumed that the requirements left open")
