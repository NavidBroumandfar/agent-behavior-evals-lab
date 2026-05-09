"""Generate a deterministic failure inspection report from scored traces.

This helper reviews failed records from the mock baseline. It does not
benchmark real models, call external services, or execute OpenClaw.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


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


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load scored trace records from a local JSONL file."""

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


def generate_report(records: list[dict[str, Any]]) -> str:
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
        f"| Input trace | `{INPUT_PATH.relative_to(REPO_ROOT)}` |",
        f"| Output report | `{OUTPUT_PATH.relative_to(REPO_ROOT)}` |",
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
        "## Detailed Failed Records",
        "",
        _detailed_failures(failures),
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


def print_summary(records: list[dict[str, Any]], failures: list[dict[str, Any]]) -> None:
    """Print a concise CLI summary for failure inspection."""

    profile_counts = Counter(str(record.get("profile_name", "unknown")) for record in failures)
    profile_summary = ", ".join(
        f"{profile}={profile_counts.get(profile, 0)}" for profile in _ordered_values(records, "profile_name", PROFILE_ORDER)
    )

    print(f"records inspected: {len(records)}")
    print(f"failed records: {len(failures)}")
    print(f"failures by profile: {profile_summary}")
    print(f"output path: {OUTPUT_PATH.relative_to(REPO_ROOT)}")


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


def _detailed_failures(failures: list[dict[str, Any]]) -> str:
    if not failures:
        return "No failed records were found."

    sections = []
    for record in failures:
        failure_modes = _format_list(record.get("failure_modes", []))
        policy_refs = _format_list(record.get("policy_refs", []))
        sections.extend(
            [
                f"### `{record.get('case_id', 'unknown')}` / `{record.get('profile_name', 'unknown')}`",
                "",
                f"- Category: `{record.get('category', 'unknown')}`",
                f"- Severity: `{record.get('severity', 'unknown')}`",
                f"- Failure modes: {failure_modes}",
                f"- Policy refs: {policy_refs}",
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
                "**Expected Behavior**",
                "",
                _fenced_text(str(record.get("expected_behavior", ""))),
                "",
            ]
        )
    return "\n".join(sections).rstrip()


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


def main() -> None:
    records = load_jsonl(INPUT_PATH)
    failures = failed_records(records)
    report = generate_report(records)
    write_report(report, OUTPUT_PATH)
    print_summary(records, failures)


if __name__ == "__main__":
    main()
