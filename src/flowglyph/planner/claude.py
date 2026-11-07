"""Planning through the Claude API with structured output."""

from collections.abc import Sequence
from typing import Any, Literal

import anthropic
from anthropic.types.beta import BetaOutputConfigParam
from pydantic import BaseModel

from flowglyph.planner import PlannerError
from flowglyph.planner.model import Plan
from flowglyph.planner.prompt import SYSTEM_PROMPT, request_text

DEFAULT_MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
NO_CREDENTIALS = (
    "no Anthropic credentials: set ANTHROPIC_API_KEY or run `ant auth login`, or use a backend "
    "that needs none: --via claude-code, codex, gemini, cursor or openai-compatible"
)

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
        """Configure the model; credentials come from the environment or `ant auth login`.

        Raises:
            PlannerError: If no client is given and the SDK finds no credentials, which it
                would otherwise only report as a `TypeError` at the first request.
        """
        self.model = model
        self.effort: Effort = effort
        self.client = client if client is not None else _default_client()

    def propose(self, requirements: str, candidates: Sequence[dict[str, Any]]) -> Plan:
        """Ask Claude for a plan.

        Raises:
            PlannerError: If the request fails, is declined, or returns no plan.
        """
        return self.answer(SYSTEM_PROMPT, request_text(requirements, candidates), Plan)

    def answer[T: BaseModel](self, system: str, prompt: str, shape: type[T]) -> T:
        """Ask Claude for an answer that validates as `shape`.

        Raises:
            PlannerError: If the request fails, is declined, or returns no answer.
        """
        noun = shape.__name__.lower()
        try:
            response = self.client.beta.messages.parse(
                model=self.model,
                max_tokens=16000,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                output_format=shape,
                output_config=BetaOutputConfigParam(effort=self.effort),
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
        except anthropic.AuthenticationError as error:
            raise PlannerError(
                f"the Anthropic API rejected the credentials: {error.message}"
            ) from error
        except anthropic.APIStatusError as error:
            raise PlannerError(
                f"the request for a {noun} failed ({error.status_code}): {error.message}"
            ) from error
        except anthropic.APIConnectionError as error:
            raise PlannerError(f"could not reach the Anthropic API: {error}") from error
        if response.stop_reason == "refusal":
            raise PlannerError(f"the model declined to write the {noun}")
        if response.stop_reason == "max_tokens" or response.parsed_output is None:
            raise PlannerError(f"the model did not return a complete {noun}")
        return response.parsed_output


def _default_client() -> anthropic.Anthropic:
    try:
        client = anthropic.Anthropic()
    except anthropic.CredentialsError as error:
        raise PlannerError(f"Anthropic credentials could not be read: {error}") from error
    if not (client.api_key or client.auth_token or client.credentials):
        raise PlannerError(NO_CREDENTIALS)
    return client
