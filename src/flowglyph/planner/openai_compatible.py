"""Planning through any server that speaks the OpenAI chat completions API."""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Sequence
from typing import Any, cast

from pydantic import BaseModel, ValidationError

from flowglyph.planner import PlannerError
from flowglyph.planner.model import Plan, strict_json_schema
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
        """Configure the endpoint and model.

        Raises:
            PlannerError: If the base URL is not an `http` or `https` URL.
        """
        self.model = model
        url = base_url or os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL
        if urllib.parse.urlsplit(url).scheme not in {"http", "https"}:
            raise PlannerError(f"the planner base URL must use http or https, not {url!r}")
        self.base_url = url.rstrip("/")
        self.api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY")
        self.timeout_seconds = timeout_seconds

    def request_body(
        self, requirements: str, candidates: Sequence[dict[str, Any]]
    ) -> dict[str, Any]:
        """The chat completions request sent to the server for a plan."""
        return self._body(SYSTEM_PROMPT, request_text(requirements, candidates), Plan)

    def propose(self, requirements: str, candidates: Sequence[dict[str, Any]]) -> Plan:
        """Ask the server for a plan.

        Raises:
            PlannerError: If the server is unreachable, rejects the request or returns no plan.
        """
        return self.answer(SYSTEM_PROMPT, request_text(requirements, candidates), Plan)

    def answer[T: BaseModel](self, system: str, prompt: str, shape: type[T]) -> T:
        """Ask the server for an answer that validates as `shape`.

        Raises:
            PlannerError: If the server is unreachable, rejects the request or returns nothing
                valid.
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        # The scheme was checked in __init__, so urllib cannot be pointed at local files.
        request = urllib.request.Request(  # noqa: S310
            f"{self.base_url}/chat/completions",
            data=json.dumps(self._body(system, prompt, shape)).encode(),
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
        return _answer_from(body, shape)

    def _body(self, system: str, prompt: str, shape: type[BaseModel]) -> dict[str, Any]:
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": shape.__name__.lower(),
                    "strict": True,
                    "schema": strict_json_schema(shape),
                },
            },
        }


def _answer_from[T: BaseModel](body: dict[str, Any], shape: type[T]) -> T:
    try:
        message = cast("dict[str, Any]", body["choices"][0]["message"])
    except (KeyError, IndexError, TypeError) as error:
        raise PlannerError("the server returned no message") from error
    if message.get("refusal"):
        raise PlannerError(f"the model declined: {message['refusal']}")
    content = message.get("content") or ""
    try:
        return shape.model_validate_json(content)
    except ValidationError as error:
        raise PlannerError(
            f"the model returned an invalid {shape.__name__.lower()}: {error}"
        ) from error
