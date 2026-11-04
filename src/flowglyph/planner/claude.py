import json
from collections.abc import Sequence
from typing import Any, Literal

import anthropic
from anthropic.types.beta import BetaOutputConfigParam

from flowglyph.planner import PlannerError
from flowglyph.planner.model import Plan

DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"

type Effort = Literal["low", "medium", "high", "xhigh", "max"]

SYSTEM_PROMPT = """\
You design automation workflows from business requirements.

You receive the requirements and a list of candidate capabilities from the company's catalog.
Each candidate has an id, a description, typed inputs, outputs, effects and an idempotency
mode. Effects use R for reads, W for writes, D for destructive, X for external systems; lower
case means the effect is possible but not certain.

Build the smallest plan that meets the requirements:
- Use only capability ids from the candidate list, copied exactly.
- When no candidate does what a step needs, keep the step with capability null and describe
  the missing behaviour in its intent. A missing capability is useful information; an invented
  one is a defect.
- Fill each step's arguments only with the inputs its capability declares, and cover every
  required input. Take values from workflow inputs, from outputs of earlier steps, or from
  literals written as JSON.
- Declare as workflow inputs the values the requirements say arrive at run time.
- Put business rules such as thresholds in the condition of the step they gate.
- List in assumptions anything the requirements leave open that you had to decide.
"""


class ClaudePlanModel:
    """Proposes plans with Claude, using structured output so every reply is a valid `Plan`.

    Requests opt into server-side fallbacks, so a request declined by one model's safety
    classifier is retried on Anthropic's recommended substitute instead of failing.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        *,
        effort: Effort = "high",
        client: anthropic.Anthropic | None = None,
    ) -> None:
        """Configure the model; credentials come from the environment or `ant auth login`."""
        self.model = model
        self.effort: Effort = effort
        self.client = client or anthropic.Anthropic()

    def propose(self, requirements: str, candidates: Sequence[dict[str, Any]]) -> Plan:
        """Ask Claude for a plan.

        Raises:
            PlannerError: If the request fails, is declined, or returns no plan.
        """
        catalog = "\n".join(json.dumps(card, ensure_ascii=False) for card in candidates)
        content = (
            f"<candidates>\n{catalog}\n</candidates>\n\n"
            f"<requirements>\n{requirements.strip()}\n</requirements>"
        )
        try:
            response = self.client.beta.messages.parse(
                model=self.model,
                max_tokens=16000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": content}],
                output_format=Plan,
                output_config=BetaOutputConfigParam(effort=self.effort),
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
        except anthropic.AuthenticationError as error:
            raise PlannerError(
                "no valid Anthropic credentials: set ANTHROPIC_API_KEY or run `ant auth login`"
            ) from error
        except anthropic.APIStatusError as error:
            raise PlannerError(
                f"the planning request failed ({error.status_code}): {error.message}"
            ) from error
        except anthropic.APIConnectionError as error:
            raise PlannerError(f"could not reach the Anthropic API: {error}") from error
        if response.stop_reason == "refusal":
            raise PlannerError("the model declined to plan these requirements")
        if response.stop_reason == "max_tokens" or response.parsed_output is None:
            raise PlannerError("the model did not return a complete plan")
        return response.parsed_output
