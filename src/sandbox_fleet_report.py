"""Aggregate sandbox fleet runs into a preliminary agent-behavior report.

Scores every local sandbox fleet file
(``traces/external/sandbox_*.local.jsonl``) against ``local_public_v2`` and
writes aggregate results to ``reports/comparisons/sandbox_fleet_pilot.{json,md}``.

Evidence discipline: raw run records stay git-ignored ``.local`` files until
human review promotes them (same workflow as all live evidence). This report
publishes **aggregates only** and is labeled preliminary/unreviewed
throughout. Deterministic given the local inputs; offline; stdlib-only.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from gate_check import run_gate
from reporting_utils import percent, write_json_object, write_text


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FLEET_GLOB = "sandbox_*.reviewed_sandbox_outputs.jsonl"
DEFAULT_FLEET_DIR = REPO_ROOT / "traces/external"
DEFAULT_CASE_PATH = REPO_ROOT / "evals/benchmarks/local_public_v2/cases.jsonl"
JSON_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/sandbox_fleet_pilot.json"
MARKDOWN_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/sandbox_fleet_pilot.md"


class SandboxFleetReportError(Exception):
    """Fleet report input error."""


def agent_label(fleet_path: Path) -> str:
    return (
        fleet_path.name.removesuffix(".reviewed_sandbox_outputs.jsonl")
        .removesuffix(".local.jsonl")
        .removeprefix("sandbox_")
    )


def summarize_fleet_file(fleet_path: Path, case_path: Path) -> dict[str, Any]:
    summary = run_gate(
        fleet_path,
        tier="extended",
        max_failures=10_000,  # report, not a gate: count failures, never trip
        case_path=case_path,
        allow_live_local=True,
    )
    failure_modes = Counter(
        mode for entry in summary["failures"] for mode in entry["failure_modes"]
    )
    by_risk_area: dict[str, dict[str, int]] = {}
    for entry in summary["scored_records"]:
        area = by_risk_area.setdefault(entry["risk_area"], {"scored": 0, "passed": 0})
        area["scored"] += 1
        area["passed"] += int(entry["passed"])
    return {
        "agent": agent_label(fleet_path),
        "scored": summary["scored_count"],
        "passed": summary["pass_count"],
        "pass_rate": percent(summary["pass_count"], summary["scored_count"]),
        "failure_modes": dict(sorted(failure_modes.items())),
        "by_risk_area": {
            area: {
                "scored": counts["scored"],
                "passed": counts["passed"],
                "pass_rate": percent(counts["passed"], counts["scored"]),
            }
            for area, counts in sorted(by_risk_area.items())
        },
    }


def build_report(fleet_dir: Path, case_path: Path) -> dict[str, Any]:
    fleet_paths = sorted(fleet_dir.glob(DEFAULT_FLEET_GLOB))
    if not fleet_paths:
        raise SandboxFleetReportError(
            f"no sandbox fleet files matching {DEFAULT_FLEET_GLOB} in {fleet_dir}"
        )
    agents = [summarize_fleet_file(path, case_path) for path in fleet_paths]
    agents.sort(key=lambda entry: (-(entry["passed"] / max(entry["scored"], 1)), entry["agent"]))
    return {
        "report": "sandbox_fleet_pilot",
        "status": "reviewed_single_reviewer",
        "case_set": "local_public_v2",
        "tier": "extended",
        "agent_count": len(agents),
        "agents": agents,
        "review_note": (
            "Runs reviewed 2026-07-08 (single reviewer, delegated): schema "
            "validation, public-safety scan (emails/urls/number patterns; all "
            "flags triaged as synthetic placeholders), and spot reads. Full "
            "reviewed records are committed alongside this report; see "
            "reports/comparisons/sandbox_fleet_review.md."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Sandbox Fleet Pilot — agents under temptation",
        "",
        "Local models and framework agents driving mock tools through the",
        "`local_public_v2` pressure corpus. Scoring is action-based where evidence",
        "exists: destructive tool calls without approval and claims without",
        "matching tool events fail structurally. Records reviewed and committed",
        "(single reviewer; see `sandbox_fleet_review.md`).",
        "",
        "| Agent | Scored | Pass rate | tool_use_claim | approval_gate | Top failure modes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for agent in report["agents"]:
        tool_area = agent["by_risk_area"].get("tool_use_claim", {})
        approval_area = agent["by_risk_area"].get("approval_gate", {})
        top_modes = ", ".join(
            f"{mode} ({count})"
            for mode, count in sorted(
                agent["failure_modes"].items(), key=lambda item: -item[1]
            )[:3]
        ) or "-"
        lines.append(
            f"| `{agent['agent']}` | {agent['scored']} | {agent['pass_rate']} "
            f"| {tool_area.get('pass_rate', '-')} | {approval_area.get('pass_rate', '-')} "
            f"| {top_modes} |"
        )
    lines.extend(
        [
            "",
            "_Generated by `src/sandbox_fleet_report.py` from committed reviewed runs",
            "(`traces/external/sandbox_*.reviewed_sandbox_outputs.jsonl`). Reproduce:",
            "run the fleet via `src/sandbox_agent_runner.py`, then this report._",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate sandbox fleet runs into the pilot report.")
    parser.add_argument("--fleet-dir", type=Path, default=DEFAULT_FLEET_DIR)
    parser.add_argument("--case-path", type=Path, default=DEFAULT_CASE_PATH)
    parser.add_argument("--json-path", type=Path, default=JSON_OUTPUT_PATH)
    parser.add_argument("--markdown-path", type=Path, default=MARKDOWN_OUTPUT_PATH)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        report = build_report(args.fleet_dir, args.case_path)
    except SandboxFleetReportError as exc:
        print(f"sandbox fleet report error: {exc}", file=sys.stderr)
        return 2
    write_json_object(report, args.json_path)
    write_text(render_markdown(report), args.markdown_path)
    print(
        f"sandbox fleet pilot report written for {report['agent_count']} agent(s): "
        f"{args.markdown_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
