"""Generate a deterministic failure inspection report from scored traces.

This helper reviews failed records from the mock baseline. It does not
benchmark real models, call external services, or execute OpenClaw.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from adjudication_report import (
    DEFAULT_ADJUDICATION_MANIFEST_PATH,
    DEFAULT_ADJUDICATIONS_PATH,
    AdjudicationReportError,
    build_adjudication_index,
    load_adjudication_context,
    load_adjudication_context_from_manifest,
    lookup_adjudication,
    select_adjudication_input,
)
from reporting_utils import display_path, load_jsonl_records as load_jsonl
from validate_adjudications import AdjudicationValidationError


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = REPO_ROOT / "traces/scored/baseline_mock_run.jsonl"
OUTPUT_PATH = REPO_ROOT / "reports/comparisons/failure_inspection.md"

PROFILE_ORDER = [
    "generic_assistant",
    "openclaw_reference_agent",
    "strict_approval_agent",
]

CATEGORY_ORDER = [
    "safe_direct_response",
    "approval_gated",
    "refusal_required",
    "uncertainty_handling",
]

SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "unknown": 4,
}




def failed_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return failed records in deterministic review order."""

    failures = [record for record in records if record.get("passed") is False]
    failures.sort(
        key=lambda record: (
            SEVERITY_RANK.get(str(record.get("severity", "unknown")), SEVERITY_RANK["unknown"]),
            str(record.get("profile_name", "")),
            str(record.get("case_id", "")),
        )
    )
    return failures


def generate_report(
    records: list[dict[str, Any]],
    adjudication_index: dict[tuple[str, str, str, str], dict[str, Any]] | None = None,
    input_path: Path = INPUT_PATH,
    output_path: Path = OUTPUT_PATH,
) -> str:
    """Build the Markdown failure inspection report."""

    failures = failed_records(records)
    profiles = _ordered_values(records, "profile_name", PROFILE_ORDER)
    categories = _ordered_values(records, "category", CATEGORY_ORDER)
    failure_modes = _failure_modes(failures)

    lines = [
        "# Failure Inspection Report",
        "",
        "## Data Source",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Input trace | `{display_path(input_path)}` |",
        f"| Output report | `{display_path(output_path)}` |",
        f"| Total records inspected | {len(records)} |",
        f"| Total failed records | {len(failures)} |",
        "",
        "## Failures By Profile",
        "",
        _count_table(failures, "profile_name", profiles, "Profile"),
        "",
        "## Failures By Category",
        "",
        _count_table(failures, "category", categories, "Category"),
        "",
        "## Failures By Failure Mode",
        "",
        _failure_mode_table(failure_modes),
        "",
        "## Reviewer Decisions On Failed Records",
        "",
        _reviewer_decisions_table(failures, adjudication_index, input_path),
        "",
        "## Detailed Failed Records",
        "",
        _detailed_failures(failures, adjudication_index, input_path),
        "",
        "## Interpretation",
        "",
        "This is a deterministic mock failure inspection, not a real model benchmark failure analysis.",
        "",
        "No live OpenClaw execution happened. The `openclaw_reference_agent` profile is simulated, and this report should not be read as evidence from an active OpenClaw runtime.",
        "",
        "The current failures are expected mock behavior used to validate the scorer and reporting pipeline. In this baseline, the generic profile intentionally misses some approval gates, and the strict approval profile intentionally over-gates some safe tasks.",
        "",
    ]

    return "\n".join(lines)


def write_report(content: str, output_path: Path) -> None:
    """Write the Markdown inspection report to disk."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def print_summary(
    records: list[dict[str, Any]],
    failures: list[dict[str, Any]],
    adjudication_index: dict[tuple[str, str, str, str], dict[str, Any]] | None = None,
    input_path: Path = INPUT_PATH,
    output_path: Path = OUTPUT_PATH,
) -> None:
    """Print a concise CLI summary for failure inspection."""

    profile_counts = Counter(str(record.get("profile_name", "unknown")) for record in failures)
    profile_summary = ", ".join(
        f"{profile}={profile_counts.get(profile, 0)}" for profile in _ordered_values(records, "profile_name", PROFILE_ORDER)
    )
    reviewed_failures = _reviewed_failure_count(failures, adjudication_index, input_path)

    print(f"records inspected: {len(records)}")
    print(f"failed records: {len(failures)}")
    print(f"reviewed failed records: {reviewed_failures}")
    print(f"failures by profile: {profile_summary}")
    print(f"output path: {display_path(output_path)}")


def _count_table(records: list[dict[str, Any]], key: str, ordered_values: list[str], label: str) -> str:
    counts = Counter(str(record.get(key, "unknown")) for record in records)
    lines = [
        f"| {label} | Failed Records |",
        "| --- | ---: |",
    ]
    for value in ordered_values:
        lines.append(f"| `{value}` | {counts.get(value, 0)} |")
    return "\n".join(lines)


def _failure_mode_table(counts: Counter[str]) -> str:
    if not counts:
        return "No failure modes were recorded."

    lines = [
        "| Failure Mode | Failed Records |",
        "| --- | ---: |",
    ]
    for failure_mode in sorted(counts):
        lines.append(f"| `{failure_mode}` | {counts[failure_mode]} |")
    return "\n".join(lines)


def _reviewer_decisions_table(
    failures: list[dict[str, Any]],
    adjudication_index: dict[tuple[str, str, str, str], dict[str, Any]] | None,
    input_path: Path,
) -> str:
    if not adjudication_index:
        return "No adjudication records were loaded for this inspection."

    decisions: Counter[str] = Counter()
    reviewed = 0
    for record in failures:
        adjudication = lookup_adjudication(adjudication_index, input_path, record)
        if adjudication is None:
            continue
        reviewed += 1
        decisions[str(adjudication["reviewer_decision"])] += 1

    lines = [
        "| Metric | Count |",
        "| --- | ---: |",
        f"| Failed records with reviewer decisions | {reviewed} |",
        f"| Failed records without reviewer decisions | {len(failures) - reviewed} |",
    ]
    for decision in sorted(decisions):
        lines.append(f"| `{decision}` | {decisions[decision]} |")
    return "\n".join(lines)


def _reviewed_failure_count(
    failures: list[dict[str, Any]],
    adjudication_index: dict[tuple[str, str, str, str], dict[str, Any]] | None,
    input_path: Path,
) -> int:
    if not adjudication_index:
        return 0
    return sum(1 for record in failures if lookup_adjudication(adjudication_index, input_path, record) is not None)


def _detailed_failures(
    failures: list[dict[str, Any]],
    adjudication_index: dict[tuple[str, str, str, str], dict[str, Any]] | None,
    input_path: Path,
) -> str:
    if not failures:
        return "No failed records were found."

    sections = []
    for record in failures:
        failure_modes = _format_list(record.get("failure_modes", []))
        policy_refs = _format_list(record.get("policy_refs", []))
        adjudication = lookup_adjudication(adjudication_index, input_path, record) if adjudication_index else None
        sections.extend(
            [
                f"### `{record.get('case_id', 'unknown')}` / `{record.get('profile_name', 'unknown')}`",
                "",
                f"- Category: `{record.get('category', 'unknown')}`",
                f"- Severity: `{record.get('severity', 'unknown')}`",
                f"- Failure modes: {failure_modes}",
                f"- Policy refs: {policy_refs}",
                f"- Reviewer decision: {_reviewer_decision_summary(adjudication)}",
                "",
                "**User Prompt**",
                "",
                _fenced_text(str(record.get("user_prompt", ""))),
                "",
                "**Model Output**",
                "",
                _fenced_text(str(record.get("model_output", ""))),
                "",
                "**Rationale**",
                "",
                _fenced_text(str(record.get("rationale", ""))),
                "",
                "**Reviewer Notes**",
                "",
                _adjudication_notes(adjudication),
                "",
                "**Expected Behavior**",
                "",
                _fenced_text(str(record.get("expected_behavior", ""))),
                "",
            ]
        )
    return "\n".join(sections).rstrip()


def _reviewer_decision_summary(adjudication: dict[str, Any] | None) -> str:
    if adjudication is None:
        return "`none`"
    result = "pass" if adjudication["adjudicated_passed"] is True else "fail"
    modes = _format_list(adjudication["adjudicated_failure_modes"])
    return f"`{adjudication['reviewer_decision']}`; adjudicated result: {result}; adjudicated failure modes: {modes}"


def _adjudication_notes(adjudication: dict[str, Any] | None) -> str:
    if adjudication is None:
        return "No reviewer adjudication is recorded for this failed trace record."

    lines = [
        f"- Adjudication ID: `{adjudication['adjudication_id']}`",
        f"- Reviewed at: `{adjudication['reviewed_at']}`",
        f"- Reviewer: `{adjudication['reviewer_id']}`",
        f"- Original result: {'pass' if adjudication['original_passed'] is True else 'fail'}",
        f"- Adjudicated result: {'pass' if adjudication['adjudicated_passed'] is True else 'fail'}",
        "",
        _fenced_text(str(adjudication["rationale"])),
    ]
    return "\n".join(lines)


def _failure_modes(records: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for record in records:
        for failure_mode in record.get("failure_modes", []):
            counts[str(failure_mode)] += 1
    return counts


def _ordered_values(records: list[dict[str, Any]], key: str, preferred_order: list[str]) -> list[str]:
    observed = {str(record.get(key, "unknown")) for record in records}
    ordered = [value for value in preferred_order if value in observed]
    ordered.extend(sorted(observed.difference(preferred_order)))
    return ordered


def _format_list(values: Any) -> str:
    if not isinstance(values, list) or not values:
        return "`none`"
    return ", ".join(f"`{value}`" for value in values)


def _fenced_text(text: str) -> str:
    safe_text = text.replace("```", "` ` `")
    return f"```text\n{safe_text}\n```"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a failure inspection report.")
    parser.add_argument("--input", type=Path, default=INPUT_PATH, help="Scored trace JSONL to inspect.")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="Markdown report output path.")
    parser.add_argument(
        "--adjudications",
        type=Path,
        default=None,
        help=(
            "Optional adjudication JSONL used to annotate failed records in single-fixture mode. "
            f"Defaults to {display_path(DEFAULT_ADJUDICATIONS_PATH)} only when no manifest is selected."
        ),
    )
    parser.add_argument(
        "--adjudication-manifest",
        type=Path,
        default=None,
        help=(
            "Optional adjudication fixture manifest. "
            f"Defaults to {display_path(DEFAULT_ADJUDICATION_MANIFEST_PATH)} when it exists and --adjudications is omitted."
        ),
    )
    parser.add_argument("--no-adjudications", action="store_true", help="Generate without reviewer annotations.")
    return parser.parse_args(argv)


def load_failure_adjudication_index(
    adjudications_path: Path,
    adjudication_manifest_path: Path | None = None,
) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    """Load reviewer adjudications for failure annotation."""

    if adjudication_manifest_path is not None:
        context = load_adjudication_context_from_manifest(adjudication_manifest_path)
    else:
        context = load_adjudication_context(adjudications_path)
    return build_adjudication_index(context.adjudications)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    records = load_jsonl(args.input)
    failures = failed_records(records)
    adjudication_index = None
    if not args.no_adjudications:
        adjudications_path, adjudication_manifest_path = select_adjudication_input(
            args.adjudications,
            args.adjudication_manifest,
        )
        adjudication_index = load_failure_adjudication_index(adjudications_path, adjudication_manifest_path)
    report = generate_report(records, adjudication_index, args.input, args.output)
    write_report(report, args.output)
    print_summary(records, failures, adjudication_index, args.input, args.output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AdjudicationValidationError, AdjudicationReportError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
