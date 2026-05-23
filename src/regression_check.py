"""Check current scored traces against the saved mock regression snapshot.

This is a deterministic mock regression check. It does not benchmark real
models, call external services, or execute OpenClaw.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any

from reporting_utils import compare_nested_values, load_json_object, load_jsonl_records, pass_count, percent


REPO_ROOT = Path(__file__).resolve().parents[1]
TRACE_PATH = REPO_ROOT / "traces/scored/baseline_mock_run.jsonl"
SNAPSHOT_PATH = REPO_ROOT / "reports/comparisons/baseline_regression_snapshot.json"

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


def build_snapshot(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build deterministic aggregate values from scored trace records."""

    if not records:
        raise ValueError("Cannot build regression snapshot from an empty trace set.")

    total = len(records)
    passed = pass_count(records)
    fail_count = total - passed

    return {
        "run_id": _single_value(records, "run_id"),
        "total_records": total,
        "pass_count": passed,
        "fail_count": fail_count,
        "pass_rate": percent(passed, total),
        "results_by_profile": _results_by_key(records, "profile_name", PROFILE_ORDER),
        "results_by_category": _results_by_key(records, "category", CATEGORY_ORDER),
        "failure_mode_distribution": _failure_mode_distribution(records),
    }


def compare_snapshots(expected: dict[str, Any], current: dict[str, Any]) -> list[str]:
    """Return human-readable differences between expected and current aggregates."""

    return compare_nested_values(expected, current)


def print_summary(snapshot: dict[str, Any], passed: bool) -> None:
    """Print a concise regression-check summary."""

    print(f"run_id: {snapshot['run_id']}")
    print(f"total records: {snapshot['total_records']}")
    print(f"pass count: {snapshot['pass_count']}")
    print(f"fail count: {snapshot['fail_count']}")
    print(f"snapshot comparison: {'passed' if passed else 'failed'}")


def _results_by_key(
    records: list[dict[str, Any]],
    key: str,
    preferred_order: list[str],
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for value in _ordered_values(records, key, preferred_order):
        value_records = [record for record in records if str(record.get(key, "unknown")) == value]
        total = len(value_records)
        passed = pass_count(value_records)
        results[value] = {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": percent(passed, total),
        }
    return results


def _failure_mode_distribution(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        for failure_mode in record.get("failure_modes", []):
            counts[str(failure_mode)] += 1
    return {failure_mode: counts[failure_mode] for failure_mode in sorted(counts)}


def _ordered_values(records: list[dict[str, Any]], key: str, preferred_order: list[str]) -> list[str]:
    observed = {str(record.get(key, "unknown")) for record in records}
    ordered = [value for value in preferred_order if value in observed]
    ordered.extend(sorted(observed.difference(preferred_order)))
    return ordered


def _single_value(records: list[dict[str, Any]], key: str) -> str:
    values = {str(record.get(key, "unknown")) for record in records}
    if len(values) != 1:
        raise ValueError(f"Expected exactly one {key}, found: {', '.join(sorted(values))}")
    return next(iter(values))


def main() -> int:
    try:
        records = load_jsonl_records(TRACE_PATH)
        expected = load_json_object(SNAPSHOT_PATH)
        current = build_snapshot(records)
        differences = compare_snapshots(expected, current)
    except (OSError, ValueError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    print_summary(current, not differences)
    if differences:
        print("differences:")
        for difference in differences:
            print(f"- {difference}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
