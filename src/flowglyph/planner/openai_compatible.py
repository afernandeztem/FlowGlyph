import json
import os
import urllib.error
import urllib.request
from collections.abc import Sequence
from typing import Any, cast

from pydantic import ValidationError

from flowglyph.planner import PlannerError
from flowglyph.planner.model import Plan, plan_json_schema
from flowglyph.planner.prompt import SYSTEM_PROMPT, request_text

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_TIMEOUT_SECONDS = 600


class OpenAICompatiblePlanModel:
    """Proposes plans through any server that speaks the OpenAI chat completions protocol.

    That covers OpenAI itself and local or self-hosted servers such as Ollama, vLLM, LM Studio
    or llama.cpp, and gateways such as OpenRouter or LiteLLM. Uses only the standard library.
    `base_url` and `api_key` default to `OPENAI_BASE_URL` and `OPENAI_API_KEY`; local servers
    usually need no key.
    """

    def __init__(
        self,
        model: str,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Configure the endpoint and model."""
        self.model = model
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL).rstrip(
            "/"
        )
        self.api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY")
        self.timeout_seconds = timeout_seconds

    def request_body(
        self, requirements: str, candidates: Sequence[dict[str, Any]]
    ) -> dict[str, Any]:
        """The chat completions request sent to the server."""
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": request_text(requirements, candidates)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "plan", "strict": True, "schema": plan_json_schema()},
            },
        }

    def propose(self, requirements: str, candidates: Sequence[dict[str, Any]]) -> Plan:
        """Ask the server for a plan.

        Raises:
            PlannerError: If the server is unreachable, rejects the request or returns no plan.
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(  # noqa: S310
            f"{self.base_url}/chat/completions",
            data=json.dumps(self.request_body(requirements, candidates)).encode(),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
                body = cast("dict[str, Any]", json.loads(response.read()))
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:300]
            raise PlannerError(
                f"{self.base_url} rejected the request ({error.code}): {detail}"
            ) from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise PlannerError(f"could not reach {self.base_url}: {error}") from error
        return _plan_from(body)


def _plan_from(body: dict[str, Any]) -> Plan:
    try:
        message = cast("dict[str, Any]", body["choices"][0]["message"])
    except (KeyError, IndexError, TypeError) as error:
        raise PlannerError("the server returned no message") from error
    if message.get("refusal"):
        raise PlannerError(f"the model declined: {message['refusal']}")
    content = message.get("content") or ""
    try:
        return Plan.model_validate_json(content)
    except ValidationError as error:
        raise PlannerError(f"the model returned an invalid plan: {error}") from error
