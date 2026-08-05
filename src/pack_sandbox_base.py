"""Shared plumbing for vertical-pack mock sandboxes.

Every pack's sandbox (finance, healthcare_admin, devops_sre, ...) records the
SAME four-field event so the scorer and structural verifier read one schema.
This base factors that plumbing out of the (gitignored, held-out) pack sandboxes
so a pack sandbox is only its fixtures + its tool methods, and can never drift
from the event contract.

Public and safe: this module is mechanism, never scenario content. It never
imports or touches ``src/scorers.py``. Deterministic, offline, stdlib-only.

A pack sandbox subclasses ``PackSandboxBase``, defines its tool methods (each
calls ``self._record(...)``), and returns its ``tool_specs()``. ``dispatch``
routes a tool name + arguments to the matching method. This is duck-typed to
``src/sandbox_tools.SandboxToolbox`` and ``FinanceSandboxToolbox``: same
``tool_events`` / ``destructive_calls`` ledgers, same event fields, same
``tool_specs()`` / ``dispatch()`` signatures.
"""

from __future__ import annotations

import hashlib
from typing import Any


def scalar(value: Any) -> str:
    """Normalize one summary value to a stable, whitespace-free token.

    Replacing every whitespace run with ``_`` is what makes a caller-controlled
    value unable to forge a second ``k=v`` pair — the property the scorer's
    field-aware ``action_contains`` / ``action_not_contains`` matching relies on.
    """

    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None or value == "":
        return "none"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value).replace(" ", "_").replace("\t", "_").replace("\n", "_")


def summarize(**fields: Any) -> str:
    """Compact ``k=v`` action summary — the scored evidence channel.

    ``breach`` is emitted FIRST when present, so the 200-char truncation in
    ``_record`` can never clip the one field a scoring rule cannot lose.
    """

    order = sorted(fields, key=lambda key: (key != "breach", list(fields).index(key)))
    return " ".join(f"{key}={scalar(fields[key])}" for key in order)


class PackSandboxBase:
    """Event-recording base for a pack sandbox. Subclasses add tools + fixtures."""

    def __init__(self, *, actor_id: str = "AGENT-OPS-01") -> None:
        self.tool_events: list[dict[str, Any]] = []
        self.destructive_calls: list[dict[str, Any]] = []
        self.actor_id: str = actor_id
        self._call_index = 0

    def _record(
        self,
        tool_name: str,
        action: str,
        *,
        destructive: bool = False,
        status: str = "succeeded",
    ) -> str:
        """Record one call; mirror the base sandbox event field-for-field.

        Returns ``action`` so a tool method can ``return self._record(...)`` and
        hand the same summary back to the model as the tool result.
        """

        self._call_index += 1
        event = {
            "tool_name": tool_name,
            "action": action[:200],
            "arguments_digest": hashlib.sha256(action.encode("utf-8")).hexdigest()[:16],
            "status": status,
        }
        self.tool_events.append(event)
        if destructive and status == "succeeded":
            self.destructive_calls.append(event)
        return action

    @staticmethod
    def _spec(name: str, description: str, params: dict[str, str]) -> dict[str, Any]:
        """One tool schema in the OpenAI/Ollama function-calling shape."""

        return {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        key: {"type": "string", "description": text} for key, text in params.items()
                    },
                    "required": list(params),
                },
            },
        }

    def tool_specs(self) -> list[dict[str, Any]]:  # pragma: no cover - overridden
        raise NotImplementedError("a pack sandbox must define tool_specs()")

    def dispatch(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Route a tool call to the matching method by name.

        Unknown tools record a ``denied`` event (never raise) so a runner driving
        an arbitrary model does not crash on a hallucinated tool name.
        """

        method = getattr(self, tool_name, None)
        if not callable(method) or tool_name.startswith("_"):
            return self._record(tool_name, summarize(error="unknown_tool"), status="denied")
        return method(**(arguments or {}))
