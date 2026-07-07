"""Drive an agent through benchmark cases inside the mock-tool sandbox.

For each selected benchmark case the runner builds a fresh
:class:`sandbox_tools.SandboxToolbox`, hands it to the agent under test,
collects the final response text plus the recorded ``tool_events``, and emits
normalized adapter-output JSONL that ``gate_check`` scores directly.

Opt-in evidence producer: reference agents are deterministic and offline; the
``ollama:<model>`` agent calls a local Ollama server only when explicitly
selected. The deterministic quality gate never invokes this module.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

from gate_check import load_benchmark_cases
from sandbox_tools import SandboxToolbox
from trace_adapters import build_adapter_record
from validate_adapter_outputs import validate_adapter_output_record


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASE_PATH = REPO_ROOT / "evals/benchmarks/local_public_v2/cases.jsonl"


class SandboxAgent(Protocol):
    def __call__(self, prompt: str, toolbox: SandboxToolbox) -> str: ...


class SandboxRunnerError(Exception):
    """Sandbox run configuration error."""


def reference_safe_agent(prompt: str, toolbox: SandboxToolbox) -> str:
    """Deterministic well-behaved agent: verifies what it can, asks before acting."""

    lowered = prompt.lower()
    consequential = any(
        marker in lowered
        for marker in (
            "drop", "delete", "remove", "force-push", "truncate", "rotate",
            "merge", "restart", "wipe", "cancel", "disable", "archive",
            "update their billing", "apply all", "rollback", "execute",
            "proceed with", "set the deletion",
        )
    )
    if consequential:
        return (
            "This is a consequential action, so I have not executed anything yet. "
            "Before I proceed I need explicit approval in this session, plus the exact "
            "target and scope, the likely impact, and whether it is reversible "
            "(backup or rollback available). Please confirm and I will proceed."
        )
    toolbox.read_file("README.md")
    return (
        "I read the workspace README to check the available context. I cannot verify "
        "anything beyond that from here: no run output or logs were provided in this "
        "session. Please share the relevant artifact and I will work from it directly."
    )


def reference_unsafe_agent(prompt: str, toolbox: SandboxToolbox) -> str:
    """Deterministic misbehaving agent: acts without approval, then overclaims."""

    lowered = prompt.lower()
    if "database" in lowered or "table" in lowered or "records" in lowered:
        toolbox.db_query("drop table staging_data")
    elif "email" in lowered or "manager" in lowered:
        toolbox.send_email("manager@example.com", "Summary", "All done.")
    else:
        toolbox.run_shell("rm -rf ./target && echo done")
    return "Done — I executed it and everything worked. Task is complete."


def select_cases(case_path: Path, tier: str) -> list[dict[str, Any]]:
    _, tier_cases = load_benchmark_cases(case_path, tier)
    return sorted(tier_cases.values(), key=lambda case: str(case["case_id"]))


def run_sandbox_fleet(
    agent: SandboxAgent,
    *,
    agent_name: str,
    case_path: Path = DEFAULT_CASE_PATH,
    tier: str = "smoke",
    output_path: Path,
    created_at: str | None = None,
    on_case: Callable[[str], None] | None = None,
) -> int:
    """Run the agent over every tier case; write validated adapter-output JSONL."""

    cases = select_cases(case_path, tier)
    timestamp = created_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    records: list[dict[str, Any]] = []

    for case in cases:
        case_id = str(case["case_id"])
        if on_case is not None:
            on_case(case_id)
        toolbox = SandboxToolbox()
        output_text = agent(str(case["user_prompt"]), toolbox)
        if not str(output_text).strip():
            output_text = "(agent returned no text)"
        record = build_adapter_record(
            case_id,
            str(output_text),
            toolbox.tool_events,
            framework=f"sandbox-{agent_name}",
            created_at=timestamp,
        )
        record["metadata"]["sandbox_run"] = {
            "agent": agent_name,
            "destructive_call_count": len(toolbox.destructive_calls),
            "tool_call_count": len(toolbox.tool_events),
        }
        validate_adapter_output_record(record, output_path, len(records) + 1)
        records.append(record)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    return len(records)


def resolve_agent(spec: str) -> tuple[str, SandboxAgent]:
    if spec == "reference-safe":
        return "reference-safe", reference_safe_agent
    if spec == "reference-unsafe":
        return "reference-unsafe", reference_unsafe_agent
    if spec.startswith("ollama:"):
        from ollama_tool_agent import OllamaToolAgent  # local import: optional runtime path

        model = spec.split(":", 1)[1]
        if not model:
            raise SandboxRunnerError("ollama agent spec needs a model: ollama:<model>")
        agent = OllamaToolAgent(model=model)
        return f"ollama-{model.replace(':', '-').replace('/', '-')}", agent
    if spec.startswith("openai-compatible:"):
        from openai_compatible_tool_agent import OpenAiCompatibleToolAgent  # optional path

        model = spec.split(":", 1)[1]
        if not model:
            raise SandboxRunnerError("openai-compatible agent spec needs a model")
        agent = OpenAiCompatibleToolAgent(model=model)
        return f"hosted-{model.replace(':', '-').replace('/', '-')}", agent
    raise SandboxRunnerError(
        f"unknown agent spec {spec!r}; expected reference-safe, reference-unsafe, "
        "ollama:<model>, or openai-compatible:<model>"
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an agent through benchmark cases in the mock-tool sandbox.")
    parser.add_argument("--agent", required=True, help="reference-safe | reference-unsafe | ollama:<model> | openai-compatible:<model>")
    parser.add_argument("--case-path", type=Path, default=DEFAULT_CASE_PATH)
    parser.add_argument("--tier", default="smoke", choices=["smoke", "standard", "extended"])
    parser.add_argument("--output", type=Path, required=True, help="Adapter-output JSONL destination.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        agent_name, agent = resolve_agent(args.agent)
        count = run_sandbox_fleet(
            agent,
            agent_name=agent_name,
            case_path=args.case_path,
            tier=args.tier,
            output_path=args.output,
            on_case=lambda case_id: print(f"case {case_id}", flush=True),
        )
    except (SandboxRunnerError, Exception) as exc:  # noqa: BLE001 - CLI boundary
        print(f"sandbox runner error: {exc}", file=sys.stderr)
        return 2
    print(f"sandbox run complete: {count} record(s) -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
