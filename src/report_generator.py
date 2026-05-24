"""Generate a Markdown report from scored evaluator traces.

The report summarizes a deterministic mock run. It does not benchmark real
models, call external services, or execute OpenClaw or any other live agent.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = REPO_ROOT / "traces/scored/baseline_mock_run.jsonl"
OUTPUT_PATH = REPO_ROOT / "reports/baseline_report.md"

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


def generate_report(records: list[dict[str, Any]]) -> str:
    """Build the Markdown report content."""

    if not records:
        raise ValueError("Cannot generate report from an empty trace set.")

    run_ids = _unique_values(records, "run_id")
    timestamps = _unique_values(records, "timestamp")
    profiles = _unique_values(records, "profile_name")
    categories = _unique_values(records, "category")

    total = len(records)
    pass_count = sum(1 for record in records if record.get("passed") is True)
    fail_count = total - pass_count
    pass_rate = _percent(pass_count, total)

    lines = [
        "# Baseline Mock Evaluation Report",
        "",
        "## Run Summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Run ID | {_format_list(run_ids)} |",
        f"| Input trace | `{INPUT_PATH.relative_to(REPO_ROOT)}` |",
        f"| Total scored records | {total} |",
        f"| Profiles evaluated | {_format_list(profiles)} |",
        f"| Categories evaluated | {_format_list(categories)} |",
        f"| Trace timestamp range | {_timestamp_range(timestamps)} |",
        "",
        "## Pass / Fail Summary",
        "",
        "| Metric | Count | Rate |",
        "| --- | ---: | ---: |",
        f"| Passed | {pass_count} | {pass_rate} |",
        f"| Failed | {fail_count} | {_percent(fail_count, total)} |",
        f"| Total | {total} | 100.0% |",
        "",
        "## Results By Profile",
        "",
        _summary_table(records, "profile_name"),
        "",
        "## Results By Category",
        "",
        _summary_table(records, "category"),
        "",
        "## Failure Mode Distribution",
        "",
        _failure_mode_table(records),
        "",
        "## Worst Or Notable Failures",
        "",
        _notable_failures(records),
        "",
        "## Interpretation",
        "",
        "This report summarizes a deterministic mock run, not a real model benchmark. The mock client is a controlled test double used to validate that the evaluator can load cases, generate profile-specific outputs, score responses, write traces, and report aggregate results.",
        "",
        "The profile comparison is simulated. It is still useful because the run exercises expected evaluator behavior: the generic assistant intentionally misses some approval gates, the strict approval profile intentionally over-gates some safe tasks, and the OpenClaw-inspired reference profile is represented as a disciplined target without claiming live OpenClaw execution.",
        "",
        "These results should not be interpreted as real performance for any production model, local model, or deployed agent. They only indicate that the v0 mock pipeline is producing traceable records and reportable scoring outcomes.",
        "",
        "## Next Improvements",
        "",
        "- Add profile/category-specific review coverage thresholds.",
        "- Add status-aware thresholds for fixture-level adjudication governance.",
        "- Factor shared JSONL loading and report table helpers out of individual scripts.",
        "- Keep tool execution and external actions blocked until the text-only adapter path is stable.",
        "",
    ]

    return "\n".join(lines)


def write_report(content: str, output_path: Path) -> None:
    """Write the Markdown report to disk."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def _summary_table(records: list[dict[str, Any]], key: str) -> str:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[str(record.get(key, "unknown"))].append(record)

    lines = [
        "| Name | Total | Passed | Failed | Pass Rate |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for name in sorted(groups):
        group = groups[name]
        total = len(group)
        passed = sum(1 for record in group if record.get("passed") is True)
        failed = total - passed
        lines.append(f"| {name} | {total} | {passed} | {failed} | {_percent(passed, total)} |")
    return "\n".join(lines)


def _failure_mode_table(records: list[dict[str, Any]]) -> str:
    counts: Counter[str] = Counter()
    for record in records:
        for failure_mode in record.get("failure_modes", []):
            counts[str(failure_mode)] += 1

    if not counts:
        return "No failure modes were recorded."

    lines = [
        "| Failure Mode | Count |",
        "| --- | ---: |",
    ]
    for failure_mode, count in sorted(counts.items()):
        lines.append(f"| {failure_mode} | {count} |")
    return "\n".join(lines)


def _notable_failures(records: list[dict[str, Any]], limit: int = 10) -> str:
    failures = [record for record in records if record.get("passed") is not True]
    if not failures:
        return "No failing records were found in this run."

    failures.sort(
        key=lambda record: (
            SEVERITY_RANK.get(str(record.get("severity", "unknown")), SEVERITY_RANK["unknown"]),
            str(record.get("profile_name", "")),
            str(record.get("case_id", "")),
        )
    )

    lines = []
    for record in failures[:limit]:
        failure_modes = ", ".join(record.get("failure_modes", [])) or "none"
        rationale = _truncate(str(record.get("rationale", "")), 220)
        lines.extend(
            [
                f"- `{record.get('case_id', 'unknown')}` / `{record.get('profile_name', 'unknown')}` / `{record.get('category', 'unknown')}`",
                f"  - Severity: {record.get('severity', 'unknown')}",
                f"  - Failure modes: {failure_modes}",
                f"  - Rationale: {rationale}",
            ]
        )

    if len(failures) > limit:
        lines.append(f"- Additional failures omitted: {len(failures) - limit}")
    return "\n".join(lines)


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


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def main() -> None:
    records = load_jsonl(INPUT_PATH)
    report = generate_report(records)
    write_report(report, OUTPUT_PATH)
    print(f"wrote {OUTPUT_PATH.relative_to(REPO_ROOT)} from {len(records)} scored records")


if __name__ == "__main__":
    main()
