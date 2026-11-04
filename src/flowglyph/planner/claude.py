from collections.abc import Sequence
from typing import Any, Literal

import anthropic
from anthropic.types.beta import BetaOutputConfigParam

from flowglyph.planner import PlannerError
from flowglyph.planner.model import Plan
from flowglyph.planner.prompt import SYSTEM_PROMPT, request_text

DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"

type Effort = Literal["low", "medium", "high", "xhigh", "max"]


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
        content = request_text(requirements, candidates)
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
