"""CI safety gate for external saved agent outputs.

The gate scores normalized adapter-output records (saved agent outputs in
JSONL) against the frozen public benchmark corpus ``local_public_v1`` and
fails when scored failures exceed a threshold. It is deterministic and
standard-library only. It does not call providers, run local models, execute
agents, use credentials, or perform network collection or external actions.

Exit codes:
    0 - gate passed (failures within threshold)
    1 - gate failed (failures above threshold)
    2 - usage, input validation, or configuration error
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from structural_tool_verifier import score_response_with_evidence
from target_registry import allowed_adapter_output_profiles
from validate_adapter_outputs import (
    AdapterOutputValidationError,
    display_path,
    load_adapter_output_records,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASE_PATH = REPO_ROOT / "evals/benchmarks/local_public_v1/cases.jsonl"
BENCHMARK_TIERS = ("smoke", "standard", "extended")


class GateCheckError(Exception):
    """Gate configuration or input error with public-safe context."""


def load_benchmark_cases(case_path: Path, tier: str) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """Load benchmark cases and return (all cases, selected-tier cases) keyed by case_id."""

    if tier not in BENCHMARK_TIERS:
        raise GateCheckError(f"unknown benchmark tier {tier!r}; expected one of: {', '.join(BENCHMARK_TIERS)}")
    if not case_path.exists():
        raise GateCheckError(f"benchmark case file does not exist: {display_path(case_path)}")

    all_cases: dict[str, dict[str, Any]] = {}
    tier_cases: dict[str, dict[str, Any]] = {}
    with case_path.open("r", encoding="utf-8") as case_file:
        for line_number, line in enumerate(case_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                case = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise GateCheckError(
                    f"{display_path(case_path)}:{line_number}: invalid JSON in benchmark case file: {exc}"
                ) from exc
            if not isinstance(case, dict) or "case_id" not in case:
                raise GateCheckError(
                    f"{display_path(case_path)}:{line_number}: benchmark case must be an object with case_id"
                )
            case_id = str(case["case_id"])
            all_cases[case_id] = case
            splits = case.get("benchmark_splits", [])
            if isinstance(splits, list) and tier in splits:
                tier_cases[case_id] = case

    if not tier_cases:
        raise GateCheckError(
            f"{display_path(case_path)}: no benchmark cases found for tier {tier!r}"
        )
    return all_cases, tier_cases


def run_gate(
    outputs_path: Path,
    *,
    tier: str = "smoke",
    max_failures: int = 0,
    case_path: Path = DEFAULT_CASE_PATH,
    allow_live_local: bool = False,
) -> dict[str, Any]:
    """Score saved agent outputs against the selected benchmark tier and apply the threshold."""

    if max_failures < 0:
        raise GateCheckError("--max-failures must be zero or a positive integer")

    records = load_adapter_output_records(outputs_path, allow_live_local=allow_live_local)
    all_cases, tier_cases = load_benchmark_cases(case_path, tier)
    allowed_profiles = allowed_adapter_output_profiles()

    scored: list[dict[str, Any]] = []
    skipped_out_of_tier: list[str] = []

    for line_number, record in enumerate(records, start=1):
        record_id = str(record["record_id"])
        case_id = str(record["case_id"])
        target_profile = str(record["target_profile"])

        if case_id not in all_cases:
            known = ", ".join(sorted(all_cases)[:5])
            raise GateCheckError(
                f"{display_path(outputs_path)}:{line_number}: unknown case_id {case_id!r} for "
                f"record_id={record_id!r}; case ids must come from {display_path(case_path)} "
                f"(for example: {known}, ...)"
            )
        if target_profile not in allowed_profiles:
            raise GateCheckError(
                f"{display_path(outputs_path)}:{line_number}: unsupported target_profile "
                f"{target_profile!r} for record_id={record_id!r}; expected one of: "
                f"{', '.join(allowed_profiles)}"
            )
        if case_id not in tier_cases:
            skipped_out_of_tier.append(record_id)
            continue

        case = tier_cases[case_id]
        response = {
            "case_id": case_id,
            "profile_name": target_profile,
            "category": str(case.get("category", "unknown")),
            "output_text": str(record["output_text"]),
        }
        score = score_response_with_evidence(case, response, record.get("tool_events"))
        scored.append(
            {
                "record_id": record_id,
                "case_id": case_id,
                "risk_area": str(case.get("risk_area", "unknown")),
                "target_profile": target_profile,
                "passed": bool(score["passed"]),
                "failure_modes": list(score["failure_modes"]),
                "rationale": str(score["rationale"]),
            }
        )

    if not scored:
        raise GateCheckError(
            f"{display_path(outputs_path)}: no output records matched benchmark tier {tier!r}; "
            "nothing to gate"
        )

    failures = [entry for entry in scored if not entry["passed"]]
    failure_mode_counts = Counter(mode for entry in failures for mode in entry["failure_modes"])
    covered_case_ids = {entry["case_id"] for entry in scored}

    return {
        "gate": "local_public_v1_benchmark_gate",
        "outputs_path": display_path(outputs_path),
        "case_path": display_path(case_path),
        "tier": tier,
        "max_failures": max_failures,
        "scored_count": len(scored),
        "pass_count": len(scored) - len(failures),
        "fail_count": len(failures),
        "gate_passed": len(failures) <= max_failures,
        "tier_case_count": len(tier_cases),
        "covered_case_count": len(covered_case_ids),
        "skipped_out_of_tier": skipped_out_of_tier,
        "failure_mode_counts": dict(sorted(failure_mode_counts.items())),
        "failures": failures,
        "scored_records": scored,
    }


def render_markdown_summary(summary: dict[str, Any]) -> str:
    """Render a public-safe Markdown gate summary (for example for GITHUB_STEP_SUMMARY)."""

    status = "PASSED" if summary["gate_passed"] else "FAILED"
    lines = [
        f"## Agent behavior safety gate: {status}",
        "",
        f"- Benchmark: `local_public_v1` tier `{summary['tier']}`",
        f"- Outputs: `{summary['outputs_path']}`",
        f"- Scored records: {summary['scored_count']} "
        f"(pass {summary['pass_count']}, fail {summary['fail_count']}, "
        f"threshold max-failures={summary['max_failures']})",
        f"- Benchmark coverage: {summary['covered_case_count']}/{summary['tier_case_count']} "
        f"tier cases covered; {len(summary['skipped_out_of_tier'])} record(s) outside tier skipped",
        "",
    ]
    if summary["failures"]:
        lines.append("| Record | Case | Risk area | Failure modes | Why |")
        lines.append("| --- | --- | --- | --- | --- |")
        for entry in summary["failures"]:
            modes = ", ".join(entry["failure_modes"]) or "-"
            rationale = entry["rationale"].replace("|", "\\|")
            lines.append(
                f"| `{entry['record_id']}` | `{entry['case_id']}` | {entry['risk_area']} "
                f"| {modes} | {rationale} |"
            )
        lines.append("")
    else:
        lines.append("No scored failures.")
        lines.append("")
    lines.append(
        "_Deterministic rule-based scoring of saved outputs only; no live agents, providers, "
        "credentials, or external actions._"
    )
    return "\n".join(lines) + "\n"


def write_text(path: Path, content: str) -> None:
    """Write a summary artifact, creating parent directories."""

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise GateCheckError(f"could not write {display_path(path)}: {exc}") from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Score saved agent outputs against the public benchmark and gate on failures.",
    )
    parser.add_argument("--outputs", type=Path, required=True, help="Saved agent outputs JSONL (adapter-output schema).")
    parser.add_argument("--tier", choices=list(BENCHMARK_TIERS), default="smoke", help="Benchmark tier to gate on.")
    parser.add_argument("--max-failures", type=int, default=0, help="Maximum scored failures allowed before the gate fails.")
    parser.add_argument("--case-path", type=Path, default=DEFAULT_CASE_PATH, help="Benchmark case JSONL path.")
    parser.add_argument("--allow-live-local", action="store_true", help="Accept reviewed live-local records (provenance.live_execution=true).")
    parser.add_argument("--summary-json", type=Path, default=None, help="Optional path for a JSON gate summary.")
    parser.add_argument("--summary-markdown", type=Path, default=None, help="Optional path for a Markdown gate summary.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        summary = run_gate(
            args.outputs,
            tier=args.tier,
            max_failures=args.max_failures,
            case_path=args.case_path,
            allow_live_local=args.allow_live_local,
        )
        if args.summary_json is not None:
            write_text(args.summary_json, json.dumps(summary, indent=2, sort_keys=True) + "\n")
        if args.summary_markdown is not None:
            write_text(args.summary_markdown, render_markdown_summary(summary))
    except (GateCheckError, AdapterOutputValidationError) as exc:
        print(f"gate error: {exc}", file=sys.stderr)
        return 2

    status = "PASSED" if summary["gate_passed"] else "FAILED"
    print(
        f"benchmark gate {status}: tier={summary['tier']} scored={summary['scored_count']} "
        f"pass={summary['pass_count']} fail={summary['fail_count']} "
        f"max_failures={summary['max_failures']}"
    )
    for entry in summary["failures"]:
        modes = ", ".join(entry["failure_modes"]) or "-"
        print(f"  FAIL {entry['record_id']} case={entry['case_id']} modes=[{modes}] {entry['rationale']}")
    return 0 if summary["gate_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
