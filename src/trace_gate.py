"""Bring-your-own-trace structural gate for saved agent traces.

Unlike ``gate_check`` (which scores outputs written to answer the frozen
``local_public_v1`` benchmark prompts), this gate runs the structural
claim-vs-recorded-``tool_events`` verifier over **your own** agent traces. There
is no benchmark, no ``case_id`` lookup, and no canned scenario: each record
carries its own recorded tool log, the gate checks whether the agent's prose
claims match that log, and fails the build when discrepancies exceed a
threshold.

This is the check the project is actually about — "your agent says *I ran the
tests* / *I can't help with that*; did the tool log agree?" — run on the
traffic you care about instead of a fixed corpus.

Record contract (loose, one JSON object per line):

    {"record_id": "run-42-step-3",
     "output_text": "I ran the test suite and all 42 tests passed.",
     "tool_events": [{"tool_name": "shell", "action": "pytest -q", "status": "succeeded"}],
     "category": "safe_direct_response"}      # optional; see VALID_CATEGORIES

Only ``record_id`` and ``output_text`` are required. ``tool_events`` defaults to
an empty list (an agent that narrated an action while calling no tools fails as
an unverified claim — which is the point). Without ``category`` a record gets
**pure claim-vs-log checking** and nothing else: no behavior rubric runs, so an
agent that refuses, hedges, or asks for approval is never failed for it — on
real traffic the gate has no ground truth about what the task required.
Declare ``category`` (``safe_direct_response`` / ``refusal_required`` /
``approval_gated`` / ``uncertainty_handling``) to opt that record into the
category rubric on top of the structural check.

It is deterministic and standard-library only. It calls no providers, runs no
agents, uses no credentials, and takes no external actions — it only reads the
trace you already recorded.

Exit codes:
    0 - gate passed (discrepancies within threshold)
    1 - gate failed (discrepancies above threshold)
    2 - usage, input validation, or configuration error
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from html_report import render_trace_html
from structural_tool_verifier import score_response_with_evidence, score_trace_claims_only


VALID_CATEGORIES = (
    "safe_direct_response",
    "approval_gated",
    "refusal_required",
    "uncertainty_handling",
)
# Display label for records with no declared category: they get pure
# claim-vs-log checking, never the category behavior rubric.
CLAIM_CHECK_ONLY = "claim_check_only"
DEFAULT_TARGET_PROFILE = "external_trace"


class TraceGateError(Exception):
    """Trace-gate configuration or input error with public-safe context."""


def _display_path(path: Path) -> str:
    """Best-effort repo-relative path for messages, falling back to the name."""

    try:
        return str(path.resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def load_trace_records(path: Path) -> list[dict[str, Any]]:
    """Load and lightly validate bring-your-own-trace records from JSONL."""

    if not path.exists():
        raise TraceGateError(f"trace file does not exist: {_display_path(path)}")

    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as trace_file:
        for line_number, line in enumerate(trace_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise TraceGateError(
                    f"{_display_path(path)}:{line_number}: invalid JSON in trace file: {exc.msg}"
                ) from exc
            if not isinstance(record, dict):
                raise TraceGateError(
                    f"{_display_path(path)}:{line_number}: each trace record must be a JSON object"
                )
            if not isinstance(record.get("record_id"), str) or not record["record_id"].strip():
                raise TraceGateError(
                    f"{_display_path(path)}:{line_number}: trace record must have a non-empty string record_id"
                )
            record_id = record["record_id"]
            if record_id in seen_ids:
                raise TraceGateError(
                    f"{_display_path(path)}:{line_number}: duplicate record_id {record_id!r}"
                )
            seen_ids.add(record_id)
            if not isinstance(record.get("output_text", ""), str):
                raise TraceGateError(
                    f"{_display_path(path)}:{line_number}: output_text must be a string for record_id={record_id!r}"
                )
            category = record.get("category")
            if category is not None and category not in VALID_CATEGORIES:
                raise TraceGateError(
                    f"{_display_path(path)}:{line_number}: unknown category {category!r} for "
                    f"record_id={record_id!r}; expected one of: {', '.join(VALID_CATEGORIES)} "
                    f"(or omit category for pure claim-vs-log checking)"
                )
            tool_events = record.get("tool_events", [])
            if not isinstance(tool_events, list) or not all(isinstance(event, dict) for event in tool_events):
                raise TraceGateError(
                    f"{_display_path(path)}:{line_number}: tool_events must be a list of objects for "
                    f"record_id={record_id!r}"
                )
            records.append(record)

    if not records:
        raise TraceGateError(f"{_display_path(path)}: trace file contains no records; nothing to gate")
    return records


def run_trace_gate(outputs_path: Path, *, max_failures: int = 0) -> dict[str, Any]:
    """Structurally score saved agent traces and apply the failure threshold."""

    if max_failures < 0:
        raise TraceGateError("--max-failures must be zero or a positive integer")

    records = load_trace_records(outputs_path)

    scored: list[dict[str, Any]] = []
    for record in records:
        record_id = str(record["record_id"])
        raw_category = record.get("category")
        target_profile = str(record.get("target_profile", DEFAULT_TARGET_PROFILE))
        risk_area = str(record.get("risk_area", "unspecified"))
        tool_events = list(record.get("tool_events", []))

        response = {
            "case_id": record_id,
            "profile_name": target_profile,
            "output_text": str(record.get("output_text", "")),
        }
        # Always structural mode: BYO-trace records carry an evidence channel
        # (their recorded tool log), so claims are checked against events, never
        # keyword-presumed. An empty list means "the agent called no tools".
        if raw_category is None:
            # No declared category → pure claim-vs-log. The behavior rubric
            # needs ground truth about what the task required; real traffic
            # carries none, and failing an agent for asking approval or
            # refusing would punish exactly the behavior buyers want.
            category = CLAIM_CHECK_ONLY
            score = score_trace_claims_only(response, tool_events)
        else:
            category = str(raw_category)
            case = {
                "case_id": record_id,
                "category": category,
                "risk_area": risk_area,
                "severity": str(record.get("severity", "unknown")),
            }
            response["category"] = category
            score = score_response_with_evidence(case, response, tool_events)
        scored.append(
            {
                "record_id": record_id,
                "category": category,
                "risk_area": risk_area,
                "target_profile": target_profile,
                "tool_event_count": len(tool_events),
                "passed": bool(score["passed"]),
                "failure_modes": list(score["failure_modes"]),
                "rationale": str(score["rationale"]),
                "tool_claim_verification": score.get("tool_claim_verification", {}),
            }
        )

    failures = [entry for entry in scored if not entry["passed"]]
    failure_mode_counts = Counter(mode for entry in failures for mode in entry["failure_modes"])

    return {
        "gate": "bring_your_own_trace_gate",
        "mode": "trace",
        "outputs_path": _display_path(outputs_path),
        "max_failures": max_failures,
        "scored_count": len(scored),
        "pass_count": len(scored) - len(failures),
        "fail_count": len(failures),
        "gate_passed": len(failures) <= max_failures,
        "failure_mode_counts": dict(sorted(failure_mode_counts.items())),
        "failures": failures,
        "scored_records": scored,
        "content_disclosure": "full",
    }


# Fields whose values are derived from the trace itself and can therefore carry
# the agent's prose or tool arguments verbatim.
_TRACE_DERIVED_FIELDS = ("rationale",)


def redact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Aggregate-only view of a trace-gate summary — no trace content.

    The full summary quotes claim snippets and tool-call arguments in each
    rationale so a reviewer can see WHY a record failed. That is the right
    artifact inside the customer's environment and the wrong one to hand out:
    an on-prem engagement that promises "only machine-generated aggregate
    summaries leave your infrastructure" cannot ship verbatim agent output.
    This view keeps record ids, verdicts, failure modes, and counts, and drops
    every trace-derived string.
    """

    def strip(entry: dict[str, Any]) -> dict[str, Any]:
        redacted = {key: value for key, value in entry.items() if key not in _TRACE_DERIVED_FIELDS}
        verification = dict(redacted.get("tool_claim_verification", {}))
        redacted["tool_claim_verification"] = {
            key: value for key, value in verification.items() if key != "claims"
        }
        return redacted

    return {
        **{key: value for key, value in summary.items() if key not in ("failures", "scored_records")},
        "content_disclosure": "redacted",
        "redaction_note": (
            "Aggregate view: record ids, verdicts, failure modes and counts only. "
            "Claim snippets and tool-call arguments are omitted so this file can leave "
            "the environment the traces live in."
        ),
        "failures": [strip(entry) for entry in summary["failures"]],
        "scored_records": [strip(entry) for entry in summary["scored_records"]],
    }


def render_trace_markdown(summary: dict[str, Any]) -> str:
    """Render a public-safe Markdown summary (for example for GITHUB_STEP_SUMMARY)."""

    status = "PASSED" if summary["gate_passed"] else "FAILED"
    lines = [
        f"## Bring-your-own-trace safety gate: {status}",
        "",
        f"- Trace: `{summary['outputs_path']}`",
        f"- Scored records: {summary['scored_count']} "
        f"(pass {summary['pass_count']}, fail {summary['fail_count']}, "
        f"threshold max-failures={summary['max_failures']})",
        "",
    ]
    if summary["failures"]:
        lines.append("| Record | Category | Risk area | Failure modes | Why |")
        lines.append("| --- | --- | --- | --- | --- |")
        for entry in summary["failures"]:
            modes = ", ".join(entry["failure_modes"]) or "-"
            # Redacted summaries carry no rationale (it quotes trace content).
            rationale = str(entry.get("rationale", "_(redacted — run without --redact inside the trace environment to see why)_")).replace("|", "\\|")
            lines.append(
                f"| `{entry['record_id']}` | {entry['category']} | {entry['risk_area']} "
                f"| {modes} | {rationale} |"
            )
        lines.append("")
    else:
        lines.append("No scored failures — every claim matched the recorded tool log.")
        lines.append("")
    lines.append(
        "_Deterministic structural scoring of your saved traces only; no live agents, providers, "
        "credentials, or external actions._"
    )
    return "\n".join(lines) + "\n"


def render_trace_badge(summary: dict[str, Any]) -> dict[str, Any]:
    """shields.io endpoint payload: https://img.shields.io/endpoint?url=<badge json url>."""

    if summary["gate_passed"]:
        message = f"passing ({summary['pass_count']}/{summary['scored_count']})"
        color = "brightgreen"
    else:
        message = f"failing ({summary['fail_count']} of {summary['scored_count']})"
        color = "red"
    return {
        "schemaVersion": 1,
        "label": "agent trace gate",
        "message": message,
        "color": color,
    }


def write_text(path: Path, content: str) -> None:
    """Write a summary artifact, creating parent directories."""

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise TraceGateError(f"could not write {_display_path(path)}: {exc}") from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Structurally gate your own saved agent traces on claim-vs-tool-log discrepancies.",
    )
    parser.add_argument("--outputs", type=Path, required=True, help="Saved agent traces JSONL (bring-your-own-trace record schema).")
    parser.add_argument("--max-failures", type=int, default=0, help="Maximum scored failures allowed before the gate fails.")
    parser.add_argument("--summary-json", type=Path, default=None, help="Optional path for a JSON gate summary.")
    parser.add_argument("--summary-markdown", type=Path, default=None, help="Optional path for a Markdown gate summary.")
    parser.add_argument("--badge-json", type=Path, default=None, help="Optional path for a shields.io endpoint badge JSON.")
    parser.add_argument(
        "--summary-html",
        type=Path,
        default=None,
        help="Optional path for a standalone HTML evidence report (trace mode only; self-contained, offline, no external references). Respects --redact.",
    )
    parser.add_argument(
        "--redact",
        action="store_true",
        help="Write aggregate-only artifacts: record ids, verdicts, failure modes and counts, with every trace-derived string (claim snippets, tool arguments) omitted. Use when the artifact leaves the environment the traces live in.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        summary = run_trace_gate(args.outputs, max_failures=args.max_failures)
        artifact_summary = redact_summary(summary) if args.redact else summary
        if args.summary_json is not None:
            write_text(args.summary_json, json.dumps(artifact_summary, indent=2, sort_keys=True) + "\n")
        if args.summary_markdown is not None:
            write_text(args.summary_markdown, render_trace_markdown(artifact_summary))
        if args.summary_html is not None:
            write_text(args.summary_html, render_trace_html(artifact_summary))
        if args.badge_json is not None:
            write_text(args.badge_json, json.dumps(render_trace_badge(summary), indent=2, sort_keys=True) + "\n")
    except TraceGateError as exc:
        print(f"trace gate error: {exc}", file=sys.stderr)
        return 2

    status = "PASSED" if summary["gate_passed"] else "FAILED"
    print(
        f"trace gate {status}: scored={summary['scored_count']} "
        f"pass={summary['pass_count']} fail={summary['fail_count']} "
        f"max_failures={summary['max_failures']}"
    )
    for entry in summary["failures"]:
        modes = ", ".join(entry["failure_modes"]) or "-"
        print(f"  FAIL {entry['record_id']} category={entry['category']} modes=[{modes}] {entry['rationale']}")
    return 0 if summary["gate_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
