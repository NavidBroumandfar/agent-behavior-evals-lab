"""Hosted-model sandbox agent via any OpenAI-compatible chat endpoint.

Opt-in cloud evidence track (roadmap Build 11): runs the same mock-tool
sandbox loop as the local Ollama agent against a hosted model behind an
OpenAI-compatible ``/chat/completions`` API — for example a subscription
gateway exposing GLM or other frontier models. Strictly outside the
deterministic quality gate; produced records are ``.local`` evidence until
reviewed, like every other live run in this repository.

Configuration comes only from environment variables (this module never reads
key files):

- ``AGENT_EVALS_OPENAI_COMPAT_BASE_URL`` — endpoint base, e.g. ``https://host/v1``
- ``AGENT_EVALS_OPENAI_COMPAT_API_KEY`` — bearer token

Example (Navid's hosted subscription):

    export AGENT_EVALS_OPENAI_COMPAT_BASE_URL="https://<gateway>/v1"
    export AGENT_EVALS_OPENAI_COMPAT_API_KEY="<key>"
    PYTHONPATH=src python3 src/sandbox_agent_runner.py \
        --agent openai-compatible:glm-5.5 --tier extended \
        --output traces/external/sandbox_hosted_glm55.local.jsonl

Standard-library only.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from ollama_tool_agent import SYSTEM_PROMPT
from sandbox_tools import SandboxToolbox


BASE_URL_ENV = "AGENT_EVALS_OPENAI_COMPAT_BASE_URL"
API_KEY_ENV = "AGENT_EVALS_OPENAI_COMPAT_API_KEY"


class OpenAiCompatibleAgentError(Exception):
    """Hosted chat transport, configuration, or protocol error."""


class OpenAiCompatibleToolAgent:
    """Callable sandbox agent backed by an OpenAI-compatible hosted endpoint."""

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        max_tool_rounds: int = 5,
        timeout_seconds: int = 120,
    ) -> None:
        self.model = model
        self.base_url = (base_url or os.environ.get(BASE_URL_ENV, "")).rstrip("/")
        self.api_key = api_key or os.environ.get(API_KEY_ENV, "")
        self.max_tool_rounds = max_tool_rounds
        self.timeout_seconds = timeout_seconds
        if not self.base_url or not self.api_key:
            raise OpenAiCompatibleAgentError(
                f"hosted agent needs {BASE_URL_ENV} and {API_KEY_ENV} set in the environment"
            )

    def __call__(self, prompt: str, toolbox: SandboxToolbox) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        tools = toolbox.tool_specs()

        for _ in range(self.max_tool_rounds):
            message = self._chat(messages, tools)
            tool_calls = message.get("tool_calls") or []
            content = str(message.get("content", "") or "")
            if not tool_calls:
                return content

            messages.append(
                {"role": "assistant", "content": content or None, "tool_calls": tool_calls}
            )
            for tool_call in tool_calls:
                function = tool_call.get("function", {}) if isinstance(tool_call, dict) else {}
                name = str(function.get("name", "unknown_tool"))
                arguments = function.get("arguments", {})
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except json.JSONDecodeError:
                        arguments = {"raw": arguments}
                if not isinstance(arguments, dict):
                    arguments = {"value": str(arguments)}
                result = toolbox.dispatch(name, arguments)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": str(tool_call.get("id", "call_0")),
                        "content": result,
                    }
                )

        message = self._chat(messages, tools=None)
        return str(message.get("content", "") or "(no final answer)")

    def _chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
        }
        if tools:
            payload["tools"] = tools
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise OpenAiCompatibleAgentError(f"hosted chat failed for {self.model}: {exc}") from exc

        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            raise OpenAiCompatibleAgentError(f"hosted chat returned no choices for {self.model}")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise OpenAiCompatibleAgentError(f"hosted chat returned no message for {self.model}")
        return message
