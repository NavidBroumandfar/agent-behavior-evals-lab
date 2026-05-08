"""Run the v0 deterministic mock evaluation harness.

This runner uses local JSONL cases, the deterministic MockModelClient, and the
rule-based scorer. It does not call real LLMs, execute tools, contact networks,
or run live agent systems.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from model_clients import MockModelClient
from scorers import score_response
from trace_writer import write_jsonl


REPO_ROOT = Path(__file__).resolve().parents[1]

CASE_PATHS = [
    REPO_ROOT / "evals/cases/safe_task_cases.jsonl",
    REPO_ROOT / "evals/cases/approval_gate_cases.jsonl",
    REPO_ROOT / "evals/cases/refusal_cases.jsonl",
    REPO_ROOT / "evals/cases/uncertainty_cases.jsonl",
]

PROFILE_NAMES = [
    "generic_assistant",
    "openclaw_reference_agent",
    "strict_approval_agent",
]

RUN_ID = "baseline_mock_run"
OUTPUT_PATH = REPO_ROOT / "traces/scored/baseline_mock_run.jsonl"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load one JSON object per line from a local JSONL file."""

    records = []
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path} on line {line_number}: {exc}") from exc
    return records


def load_cases(case_paths: list[Path]) -> list[dict[str, Any]]:
    """Load all configured evaluation cases."""

    cases: list[dict[str, Any]] = []
    for case_path in case_paths:
        cases.extend(load_jsonl(case_path))
    return cases


def utc_timestamp() -> str:
    """Return a compact UTC timestamp for trace records."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_trace_record(
    run_id: str,
    timestamp: str,
    case: dict[str, Any],
    response: dict[str, Any],
    score: dict[str, Any],
) -> dict[str, Any]:
    """Combine case, response, and score data into one scored trace record."""

    return {
        "run_id": run_id,
        "timestamp": timestamp,
        "case_id": score["case_id"],
        "category": score["category"],
        "profile_name": score["profile_name"],
        "user_prompt": case.get("user_prompt", ""),
        "expected_behavior": case.get("expected_behavior", ""),
        "model_output": response.get("output_text", ""),
        "mock_behavior_notes": response.get("mock_behavior_notes", ""),
        "passed": score["passed"],
        "score": score["score"],
        "failure_modes": score["failure_modes"],
        "severity": score["severity"],
        "policy_refs": score["policy_refs"],
        "expected_failure_modes": case.get("expected_failure_modes", []),
        "scoring_notes": case.get("scoring_notes", ""),
        "rationale": score["rationale"],
    }


def run_eval() -> dict[str, Any]:
    """Run all configured cases against all configured mock profiles."""

    cases = load_cases(CASE_PATHS)
    timestamp = utc_timestamp()
    scored_traces = []

    for profile_name in PROFILE_NAMES:
        client = MockModelClient(profile_name)
        for case in cases:
            response = client.generate(case)
            score = score_response(case, response)
            scored_traces.append(build_trace_record(RUN_ID, timestamp, case, response, score))

    write_jsonl(scored_traces, OUTPUT_PATH)

    pass_count = sum(1 for trace in scored_traces if trace["passed"])
    fail_count = len(scored_traces) - pass_count

    return {
        "run_id": RUN_ID,
        "total_cases_loaded": len(cases),
        "profiles_evaluated": PROFILE_NAMES,
        "total_scored_records": len(scored_traces),
        "output_path": str(OUTPUT_PATH.relative_to(REPO_ROOT)),
        "pass_count": pass_count,
        "fail_count": fail_count,
    }


def print_summary(summary: dict[str, Any]) -> None:
    """Print a concise human-readable run summary."""

    print(f"run_id: {summary['run_id']}")
    print(f"total cases loaded: {summary['total_cases_loaded']}")
    print(f"profiles evaluated: {', '.join(summary['profiles_evaluated'])}")
    print(f"total scored records: {summary['total_scored_records']}")
    print(f"output path: {summary['output_path']}")
    print(f"pass count: {summary['pass_count']}")
    print(f"fail count: {summary['fail_count']}")


if __name__ == "__main__":
    print_summary(run_eval())
