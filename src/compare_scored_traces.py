"""Compare two scored trace JSONL files.

This command compares saved scored traces only. It does not run scoring, call
models, execute agents, or collect live outputs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from reporting_utils import atomic_write_text
from validate_schemas import ValidationError, validate_trace_record


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BEFORE_PATH = REPO_ROOT / "traces/scored/baseline_mock_run.jsonl"
DEFAULT_AFTER_PATH = REPO_ROOT / "traces/scored/baseline_mock_run.jsonl"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/baseline_self_comparison_report.md"


class ScoredTraceComparisonError(Exception):
    """Scored trace comparison error."""


def compare_scored_traces(before_path: Path, after_path: Path, output_path: Path, title: str) -> dict[str, Any]:
    """Compare two scored trace files and write a Markdown report."""

    before_records = load_trace_records(before_path)
    after_records = load_trace_records(after_path)
    comparison = build_comparison(before_records, after_records)
    report = generate_report(before_path, after_path, output_path, title, comparison)
    atomic_write_text(report, output_path)

    return {
        "before_path": display_path(before_path),
        "after_path": display_path(after_path),
        "output_path": display_path(output_path),
        "before_records": len(before_records),
        "after_records": len(after_records),
        "changed_records": len(comparison["changed_records"]),
        "new_records": len(comparison["new_records"]),
        "removed_records": len(comparison["removed_records"]),
    }


def load_trace_records(path: Path) -> list[dict[str, Any]]:
    """Load and validate scored trace records."""

    if not path.exists():
        raise ScoredTraceComparisonError(f"{display_path(path)}: file does not exist")

    records = []
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ScoredTraceComparisonError(
                    f"{display_path(path)}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc
            try:
                validate_trace_record(record, str(path), line_number)
            except ValidationError as exc:
                raise ScoredTraceComparisonError(str(exc)) from exc
            records.append(record)

    if not records:
        raise ScoredTraceComparisonError(f"{display_path(path)}: file contains no trace records")
    return records


def build_comparison(before_records: list[dict[str, Any]], after_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build deterministic record-level and aggregate deltas."""

    before_by_key = records_by_key(before_records, "before")
    after_by_key = records_by_key(after_records, "after")
    before_keys = set(before_by_key)
    after_keys = set(after_by_key)
    shared_keys = sorted(before_keys & after_keys)

    changed_records = []
    resolved_failures = []
    new_failures = []
    for key in shared_keys:
        before = before_by_key[key]
        after = after_by_key[key]
        changes = record_changes(before, after)
        if changes:
            changed_records.append(
                {
                    "key": key,
                    "before": before,
                    "after": after,
                    "changes": changes,
                }
            )
        if before.get("passed") is not True and after.get("passed") is True:
            resolved_failures.append({"key": key, "before": before, "after": after})
        if before.get("passed") is True and after.get("passed") is not True:
            new_failures.append({"key": key, "before": before, "after": after})

    return {
        "before_summary": summarize_records(before_records),
        "after_summary": summarize_records(after_records),
        "new_records": [after_by_key[key] for key in sorted(after_keys - before_keys)],
        "removed_records": [before_by_key[key] for key in sorted(before_keys - after_keys)],
        "changed_records": changed_records,
        "resolved_failures": resolved_failures,
        "new_failures": new_failures,
    }


def records_by_key(records: list[dict[str, Any]], label: str) -> dict[tuple[str, str], dict[str, Any]]:
    """Index records by case/profile and reject duplicates."""

    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (str(record.get("case_id", "")), str(record.get("profile_name", "")))
        if key in indexed:
            raise ScoredTraceComparisonError(f"{label}: duplicate trace key case_id={key[0]!r}, profile_name={key[1]!r}")
        indexed[key] = record
    return indexed


def record_changes(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    """Return human-readable changes for a shared record."""

    changes = []
    for field_name in ["passed", "score", "severity"]:
        if before.get(field_name) != after.get(field_name):
            changes.append(f"{field_name}: {before.get(field_name)!r} -> {after.get(field_name)!r}")

    before_modes = [str(mode) for mode in before.get("failure_modes", [])]
    after_modes = [str(mode) for mode in after.get("failure_modes", [])]
    if before_modes != after_modes:
        changes.append(f"failure_modes: {before_modes!r} -> {after_modes!r}")

    return changes


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    passed = sum(1 for record in records if record.get("passed") is True)
    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": percent(passed, total),
    }


def generate_report(
    before_path: Path,
    after_path: Path,
    output_path: Path,
    title: str,
    comparison: dict[str, Any],
) -> str:
    """Generate a deterministic Markdown comparison report."""

    before_summary = comparison["before_summary"]
    after_summary = comparison["after_summary"]
    lines = [
        f"# {title}",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Before trace | `{display_path(before_path)}` |",
        f"| After trace | `{display_path(after_path)}` |",
        f"| Output report | `{display_path(output_path)}` |",
        "",
        "This compares already-scored trace files. It does not collect outputs, run models, execute agents, or rescore records.",
        "",
        "## Aggregate Delta",
        "",
        "| Metric | Before | After | Delta |",
        "| --- | ---: | ---: | ---: |",
        aggregate_row("Total", before_summary["total"], after_summary["total"]),
        aggregate_row("Passed", before_summary["passed"], after_summary["passed"]),
        aggregate_row("Failed", before_summary["failed"], after_summary["failed"]),
        f"| Pass rate | {before_summary['pass_rate']} | {after_summary['pass_rate']} | n/a |",
        "",
        "## Record Changes",
        "",
        changed_records_table(comparison["changed_records"]),
        "",
        "## New Failures",
        "",
        keyed_records_table(comparison["new_failures"], "No new failures were found."),
        "",
        "## Resolved Failures",
        "",
        keyed_records_table(comparison["resolved_failures"], "No resolved failures were found."),
        "",
        "## Added Records",
        "",
        records_table(comparison["new_records"], "No added records were found."),
        "",
        "## Removed Records",
        "",
        records_table(comparison["removed_records"], "No removed records were found."),
        "",
    ]
    return "\n".join(lines)


def aggregate_row(label: str, before: int, after: int) -> str:
    delta = after - before
    delta_text = f"+{delta}" if delta > 0 else str(delta)
    return f"| {label} | {before} | {after} | {delta_text} |"


def changed_records_table(changed_records: list[dict[str, Any]]) -> str:
    if not changed_records:
        return "No shared records changed."

    lines = [
        "| Case ID | Profile | Changes |",
        "| --- | --- | --- |",
    ]
    for item in changed_records:
        case_id, profile_name = item["key"]
        changes = "<br>".join(item["changes"])
        lines.append(f"| `{case_id}` | `{profile_name}` | {changes} |")
    return "\n".join(lines)


def keyed_records_table(items: list[dict[str, Any]], empty_message: str) -> str:
    if not items:
        return empty_message

    lines = [
        "| Case ID | Profile | Before | After |",
        "| --- | --- | --- | --- |",
    ]
    for item in items:
        case_id, profile_name = item["key"]
        before = pass_fail_text(item["before"])
        after = pass_fail_text(item["after"])
        lines.append(f"| `{case_id}` | `{profile_name}` | {before} | {after} |")
    return "\n".join(lines)


def records_table(records: list[dict[str, Any]], empty_message: str) -> str:
    if not records:
        return empty_message

    lines = [
        "| Case ID | Profile | Result |",
        "| --- | --- | --- |",
    ]
    for record in records:
        lines.append(
            f"| `{record.get('case_id', 'unknown')}` | `{record.get('profile_name', 'unknown')}` | {pass_fail_text(record)} |"
        )
    return "\n".join(lines)


def pass_fail_text(record: dict[str, Any]) -> str:
    status = "pass" if record.get("passed") is True else "fail"
    modes = ", ".join(str(mode) for mode in record.get("failure_modes", [])) or "none"
    return f"{status}; score={record.get('score', 'unknown')}; modes={modes}"


def percent(part: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{(part / total) * 100:.1f}%"


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two scored trace JSONL files.")
    parser.add_argument("--before", type=Path, default=DEFAULT_BEFORE_PATH, help="Before scored trace JSONL.")
    parser.add_argument("--after", type=Path, default=DEFAULT_AFTER_PATH, help="After scored trace JSONL.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Markdown report output path.")
    parser.add_argument("--title", default="Scored Trace Comparison Report", help="Markdown report title.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        summary = compare_scored_traces(args.before, args.after, args.output, args.title)
    except (ScoredTraceComparisonError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"before path: {summary['before_path']}")
    print(f"after path: {summary['after_path']}")
    print(f"output path: {summary['output_path']}")
    print(f"before records: {summary['before_records']}")
    print(f"after records: {summary['after_records']}")
    print(f"changed records: {summary['changed_records']}")
    print(f"new records: {summary['new_records']}")
    print(f"removed records: {summary['removed_records']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
