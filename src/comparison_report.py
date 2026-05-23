"""Generate a deterministic profile comparison report from scored traces.

The report compares simulated profiles from the mock baseline. It does not
benchmark real models, call external services, or execute OpenClaw.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = REPO_ROOT / "traces/scored/baseline_mock_run.jsonl"
OUTPUT_PATH = REPO_ROOT / "reports/comparisons/profile_comparison_report.md"

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

PROFILE_SUMMARIES = {
    "generic_assistant": "Useful direct-answer baseline; intentionally weaker on approval-gated cases in this mock trace.",
    "openclaw_reference_agent": "Simulated reference profile with disciplined gating and uncertainty behavior; not a live OpenClaw runtime result.",
    "strict_approval_agent": "Conservative approval-focused profile; strong on gates but intentionally prone to over-gating safe tasks.",
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


def generate_report(records: list[dict[str, Any]]) -> str:
    """Build the Markdown comparison report content."""

    if not records:
        raise ValueError("Cannot generate comparison report from an empty trace set.")

    profiles = _ordered_values(records, "profile_name", PROFILE_ORDER)
    categories = _ordered_values(records, "category", CATEGORY_ORDER)
    failure_modes = _observed_failure_modes(records)
    run_ids = _unique_values(records, "run_id")
    timestamps = _unique_values(records, "timestamp")

    lines = [
        "# Profile Comparison Report",
        "",
        "## Data Source",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Input trace | `{INPUT_PATH.relative_to(REPO_ROOT)}` |",
        f"| Output report | `{OUTPUT_PATH.relative_to(REPO_ROOT)}` |",
        f"| Run ID | {_format_list(run_ids)} |",
        f"| Total scored records | {len(records)} |",
        f"| Profiles compared | {_format_list(profiles)} |",
        f"| Categories compared | {_format_list(categories)} |",
        f"| Trace timestamp range | {_timestamp_range(timestamps)} |",
        "",
        "## Overall Profile Comparison",
        "",
        _overall_profile_table(records, profiles),
        "",
        "## Pass/Fail By Profile",
        "",
        _pass_fail_table(records, profiles),
        "",
        "## Pass Rate By Profile And Category",
        "",
        _profile_category_table(records, profiles, categories),
        "",
        "## Failure Modes By Profile",
        "",
        _failure_modes_by_profile_table(records, profiles, failure_modes),
        "",
        "## Notable Behavior Tradeoffs",
        "",
        _notable_behavior_tradeoffs(records),
        "",
        "## Interpretation",
        "",
        "This is a deterministic mock comparison, not a real model benchmark. The mock client is intentionally shaped to validate the evaluator's trace, scoring, aggregation, and reporting logic.",
        "",
        "No live OpenClaw execution happened. The `openclaw_reference_agent` profile is simulated and should be read as a reference behavior target, not as an active runtime result.",
        "",
        "The comparison is useful for validating behavior-tradeoff interpretation: the generic profile exposes approval-gate misses, the strict approval profile exposes over-gating on safe tasks, and the simulated reference profile provides a clean comparator for report mechanics.",
        "",
        "## Known Limitations",
        "",
        "- Results come from deterministic mock outputs, not live model or agent responses.",
        "- The scorer is v0 heuristic-based and intentionally simple.",
        "- Profile differences are shaped test signals, not measured production behavior.",
        "- The report compares one baseline trace and does not yet compare previous-vs-current runs.",
        "- No real model adapters, live OpenClaw execution, network calls, browser actions, email actions, or autonomous actions are involved.",
        "",
        "## Next Improvements",
        "",
        "- Make external fixture comparison manifest-driven instead of maintaining source lists in code.",
        "- Add adjudication-aware comparison summaries that separate heuristic and reviewed outcomes.",
        "- Add reviewer adjudication rollups for cases where the v0 heuristic scorer is too coarse.",
        "- Add promotion status reporting for reviewed text-only output candidates once they become committed fixtures.",
        "- Add a promotion checklist for admitting reviewed fixtures to the deterministic quality gate.",
        "- Keep comparison outputs general enough for future text-only model and agent adapters.",
        "",
    ]

    return "\n".join(lines)


def write_report(content: str, output_path: Path) -> None:
    """Write the Markdown comparison report to disk."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def _overall_profile_table(records: list[dict[str, Any]], profiles: list[str]) -> str:
    lines = [
        "| Profile | Total | Passed | Failed | Pass Rate | Comparison Note |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for profile in profiles:
        profile_records = _records_for_profile(records, profile)
        total = len(profile_records)
        passed = _pass_count(profile_records)
        failed = total - passed
        note = PROFILE_SUMMARIES.get(profile, "Additional profile observed in the trace.")
        lines.append(f"| `{profile}` | {total} | {passed} | {failed} | {_percent(passed, total)} | {note} |")
    return "\n".join(lines)


def _pass_fail_table(records: list[dict[str, Any]], profiles: list[str]) -> str:
    lines = [
        "| Profile | Passed | Failed | Total |",
        "| --- | ---: | ---: | ---: |",
    ]
    for profile in profiles:
        profile_records = _records_for_profile(records, profile)
        total = len(profile_records)
        passed = _pass_count(profile_records)
        lines.append(f"| `{profile}` | {passed} | {total - passed} | {total} |")
    return "\n".join(lines)


def _profile_category_table(
    records: list[dict[str, Any]],
    profiles: list[str],
    categories: list[str],
) -> str:
    header = "| Profile | " + " | ".join(f"`{category}`" for category in categories) + " |"
    alignment = "| --- | " + " | ".join("---:" for _ in categories) + " |"
    lines = [header, alignment]

    grouped = _records_by_profile_and_category(records)
    for profile in profiles:
        cells = []
        for category in categories:
            category_records = grouped[profile][category]
            total = len(category_records)
            passed = _pass_count(category_records)
            cells.append(f"{passed}/{total} ({_percent(passed, total)})")
        lines.append(f"| `{profile}` | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _failure_modes_by_profile_table(
    records: list[dict[str, Any]],
    profiles: list[str],
    failure_modes: list[str],
) -> str:
    if not failure_modes:
        return "No failure modes were recorded."

    header = "| Profile | " + " | ".join(f"`{failure_mode}`" for failure_mode in failure_modes) + " | Total Failure Labels |"
    alignment = "| --- | " + " | ".join("---:" for _ in failure_modes) + " | ---: |"
    lines = [header, alignment]

    for profile in profiles:
        counts = _failure_mode_counts(_records_for_profile(records, profile))
        cells = [str(counts.get(failure_mode, 0)) for failure_mode in failure_modes]
        lines.append(f"| `{profile}` | " + " | ".join(cells) + f" | {sum(counts.values())} |")
    return "\n".join(lines)


def _notable_behavior_tradeoffs(records: list[dict[str, Any]]) -> str:
    generic_records = _records_for_profile(records, "generic_assistant")
    reference_records = _records_for_profile(records, "openclaw_reference_agent")
    strict_records = _records_for_profile(records, "strict_approval_agent")

    generic_missing_gates = _failure_mode_counts(generic_records).get("missing_approval_gate", 0)
    reference_failures = len(reference_records) - _pass_count(reference_records)
    strict_over_refusals = _failure_mode_counts(strict_records).get("over_refusal", 0)

    lines = [
        f"- `generic_assistant` has {generic_missing_gates} `missing_approval_gate` failures, showing the shaped baseline weakness on consequential-action gating.",
        f"- `openclaw_reference_agent` has {reference_failures} failures in this deterministic mock trace, but this is a simulated reference profile rather than live OpenClaw evidence.",
        f"- `strict_approval_agent` has {strict_over_refusals} `over_refusal` failures, showing the tradeoff between conservative gating and direct handling of safe requests.",
    ]
    return "\n".join(lines)


def _records_for_profile(records: list[dict[str, Any]], profile: str) -> list[dict[str, Any]]:
    return [record for record in records if str(record.get("profile_name", "unknown")) == profile]


def _records_by_profile_and_category(records: list[dict[str, Any]]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for record in records:
        profile = str(record.get("profile_name", "unknown"))
        category = str(record.get("category", "unknown"))
        grouped[profile][category].append(record)
    return grouped


def _pass_count(records: list[dict[str, Any]]) -> int:
    return sum(1 for record in records if record.get("passed") is True)


def _failure_mode_counts(records: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for record in records:
        for failure_mode in record.get("failure_modes", []):
            counts[str(failure_mode)] += 1
    return counts


def _observed_failure_modes(records: list[dict[str, Any]]) -> list[str]:
    return sorted(_failure_mode_counts(records))


def _ordered_values(records: list[dict[str, Any]], key: str, preferred_order: list[str]) -> list[str]:
    observed = {str(record.get(key, "unknown")) for record in records}
    ordered = [value for value in preferred_order if value in observed]
    ordered.extend(sorted(observed.difference(preferred_order)))
    return ordered


def _unique_values(records: list[dict[str, Any]], key: str) -> list[str]:
    seen = set()
    values = []
    for record in records:
        value = str(record.get(key, "unknown"))
        if value not in seen:
            values.append(value)
            seen.add(value)
    return values


def _format_list(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values)


def _timestamp_range(timestamps: list[str]) -> str:
    if not timestamps:
        return "unknown"
    if len(timestamps) == 1:
        return f"`{timestamps[0]}`"
    return f"`{min(timestamps)}` to `{max(timestamps)}`"


def _percent(part: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{(part / total) * 100:.1f}%"


def main() -> None:
    records = load_jsonl(INPUT_PATH)
    report = generate_report(records)
    write_report(report, OUTPUT_PATH)
    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} from {len(records)} scored records")


if __name__ == "__main__":
    main()
