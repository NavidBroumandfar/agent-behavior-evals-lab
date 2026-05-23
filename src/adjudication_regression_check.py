"""Check adjudication-aware report aggregates against a saved snapshot.

This command validates deterministic reviewer-decision counts. It reads saved
adjudications and scored traces only; it does not rescore outputs, rewrite
traces, call models, execute agents, or collect live outputs.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from adjudication_report import (
    DEFAULT_ADJUDICATIONS_PATH,
    DECISION_ORDER,
    AdjudicationContext,
    AdjudicationReportError,
    load_adjudication_context,
)
from reporting_utils import compare_nested_values, display_path, load_json_object, percent, write_json_object
from validate_adjudications import AdjudicationValidationError


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT_PATH = REPO_ROOT / "reports/comparisons/adjudication_regression_snapshot.json"


class AdjudicationRegressionError(Exception):
    """Adjudication regression check error."""


def build_snapshot(
    context: AdjudicationContext,
    adjudications_path: Path = DEFAULT_ADJUDICATIONS_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Build deterministic adjudication reporting aggregates."""

    if not context.adjudications:
        raise AdjudicationRegressionError("cannot build adjudication snapshot from zero adjudications")

    decision_counts = Counter(str(record["reviewer_decision"]) for record in context.adjudications)
    source_records = [
        record
        for source_path in sorted(context.source_records_by_path)
        for record in context.source_records_by_path[source_path]
    ]

    return {
        "adjudication_fixture": display_path(adjudications_path, repo_root),
        "adjudication_records": len(context.adjudications),
        "source_trace_count": len(context.source_records_by_path),
        "source_trace_records": len(source_records),
        "reviewer_count": len({str(record["reviewer_id"]) for record in context.adjudications}),
        "reviewer_decisions": {decision: decision_counts.get(decision, 0) for decision in DECISION_ORDER},
        "result_summary": _result_summary(context.adjudications),
        "review_coverage_by_source_trace": _review_coverage_by_source_trace(context),
        "reviewed_by_profile": _reviewed_by_profile(context),
        "reviewed_by_category": _reviewed_by_category(context),
        "failure_mode_distribution": {
            "original": _failure_mode_distribution(context.adjudications, "original_failure_modes"),
            "adjudicated": _failure_mode_distribution(context.adjudications, "adjudicated_failure_modes"),
        },
    }


def compare_snapshots(expected: dict[str, Any], current: dict[str, Any]) -> list[str]:
    """Return deterministic differences between expected and current snapshots."""

    return compare_nested_values(expected, current)


def check_snapshot(
    adjudications_path: Path = DEFAULT_ADJUDICATIONS_PATH,
    snapshot_path: Path = DEFAULT_SNAPSHOT_PATH,
    min_review_coverage: float | None = None,
    max_needs_discussion: int | None = None,
) -> dict[str, Any]:
    """Load current adjudication aggregates and compare them to the saved snapshot."""

    context = load_adjudication_context(adjudications_path)
    expected = load_json_object(snapshot_path)
    current = build_snapshot(context, adjudications_path)
    differences = compare_snapshots(expected, current)
    differences.extend(threshold_violations(current, min_review_coverage, max_needs_discussion))
    return {
        "current": current,
        "differences": differences,
        "passed": not differences,
    }


def write_current_snapshot(
    adjudications_path: Path = DEFAULT_ADJUDICATIONS_PATH,
    snapshot_path: Path = DEFAULT_SNAPSHOT_PATH,
) -> dict[str, Any]:
    """Write the current adjudication aggregate snapshot."""

    context = load_adjudication_context(adjudications_path)
    snapshot = build_snapshot(context, adjudications_path)
    write_json_object(snapshot, snapshot_path)
    return snapshot


def print_summary(snapshot: dict[str, Any], passed: bool, snapshot_path: Path) -> None:
    """Print a concise adjudication regression summary."""

    print(f"adjudication fixture: {snapshot['adjudication_fixture']}")
    print(f"snapshot path: {display_path(snapshot_path)}")
    print(f"adjudication records: {snapshot['adjudication_records']}")
    print(f"source trace count: {snapshot['source_trace_count']}")
    print(f"needs discussion: {snapshot['reviewer_decisions'].get('needs_discussion', 0)}")
    print(f"override pass: {snapshot['reviewer_decisions'].get('override_pass', 0)}")
    print(f"override fail: {snapshot['reviewer_decisions'].get('override_fail', 0)}")
    print(f"snapshot comparison: {'passed' if passed else 'failed'}")


def threshold_violations(
    snapshot: dict[str, Any],
    min_review_coverage: float | None = None,
    max_needs_discussion: int | None = None,
) -> list[str]:
    """Return review threshold violations for optional quality gates."""

    violations: list[str] = []
    if min_review_coverage is not None:
        coverage_by_source = snapshot.get("review_coverage_by_source_trace", {})
        if not isinstance(coverage_by_source, dict):
            raise AdjudicationRegressionError("review_coverage_by_source_trace must be an object")
        for source_trace, coverage in sorted(coverage_by_source.items()):
            if not isinstance(coverage, dict):
                raise AdjudicationRegressionError(f"{source_trace}.review_coverage must be an object")
            actual = _parse_percent(str(coverage.get("review_coverage", "0.0%")))
            if actual < min_review_coverage:
                violations.append(
                    f"{source_trace}.review_coverage: expected at least {min_review_coverage:.1f}%, found {actual:.1f}%"
                )

    if max_needs_discussion is not None:
        needs_discussion = snapshot.get("reviewer_decisions", {}).get("needs_discussion")
        if not isinstance(needs_discussion, int):
            raise AdjudicationRegressionError("reviewer_decisions.needs_discussion must be an integer")
        if needs_discussion > max_needs_discussion:
            violations.append(
                f"reviewer_decisions.needs_discussion: expected at most {max_needs_discussion}, found {needs_discussion}"
            )

    return violations


def _parse_percent(value: str) -> float:
    if not value.endswith("%"):
        raise AdjudicationRegressionError(f"invalid percent value: {value!r}")
    try:
        return float(value[:-1])
    except ValueError as exc:
        raise AdjudicationRegressionError(f"invalid percent value: {value!r}") from exc


def _result_summary(adjudications: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(adjudications)
    original_passed = sum(1 for record in adjudications if record["original_passed"] is True)
    adjudicated_passed = sum(1 for record in adjudications if record["adjudicated_passed"] is True)
    changed_results = sum(1 for record in adjudications if record["original_passed"] is not record["adjudicated_passed"])
    changed_failure_modes = sum(
        1
        for record in adjudications
        if [str(mode) for mode in record["original_failure_modes"]]
        != [str(mode) for mode in record["adjudicated_failure_modes"]]
    )
    return {
        "original_passed": original_passed,
        "original_failed": total - original_passed,
        "original_pass_rate": percent(original_passed, total),
        "adjudicated_passed": adjudicated_passed,
        "adjudicated_failed": total - adjudicated_passed,
        "adjudicated_pass_rate": percent(adjudicated_passed, total),
        "changed_result_count": changed_results,
        "changed_failure_modes_count": changed_failure_modes,
    }


def _review_coverage_by_source_trace(context: AdjudicationContext) -> dict[str, dict[str, Any]]:
    reviewed_by_source: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    for adjudication in context.adjudications:
        reviewed_by_source[display_path(adjudication["source_trace_path"])].add(
            (
                str(adjudication["run_id"]),
                str(adjudication["case_id"]),
                str(adjudication["profile_name"]),
            )
        )

    coverage: dict[str, dict[str, Any]] = {}
    for source_path in sorted(context.source_records_by_path):
        total = len(context.source_records_by_path[source_path])
        reviewed = len(reviewed_by_source[source_path])
        coverage[source_path] = {
            "source_records": total,
            "reviewed_records": reviewed,
            "unreviewed_records": total - reviewed,
            "review_coverage": percent(reviewed, total),
        }
    return coverage


def _reviewed_by_profile(context: AdjudicationContext) -> dict[str, dict[str, int]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for adjudication in context.adjudications:
        grouped[str(adjudication["profile_name"])].append(adjudication)

    return {
        profile: _reviewed_group_summary(records)
        for profile, records in sorted(grouped.items())
    }


def _reviewed_by_category(context: AdjudicationContext) -> dict[str, dict[str, int]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for adjudication in context.adjudications:
        source_record = context.source_record_by_adjudication_id[adjudication["adjudication_id"]]
        grouped[str(source_record.get("category", "unknown"))].append(adjudication)

    return {
        category: _reviewed_group_summary(records)
        for category, records in sorted(grouped.items())
    }


def _reviewed_group_summary(records: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "reviewed": len(records),
        "original_failed": sum(1 for record in records if record["original_passed"] is not True),
        "adjudicated_failed": sum(1 for record in records if record["adjudicated_passed"] is not True),
        "needs_discussion": sum(1 for record in records if record["reviewer_decision"] == "needs_discussion"),
        "overrides": sum(1 for record in records if str(record["reviewer_decision"]).startswith("override_")),
    }


def _failure_mode_distribution(adjudications: list[dict[str, Any]], field_name: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for adjudication in adjudications:
        for failure_mode in adjudication[field_name]:
            counts[str(failure_mode)] += 1
    return {failure_mode: counts[failure_mode] for failure_mode in sorted(counts)}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check adjudication report aggregates against a snapshot.")
    parser.add_argument("--input", type=Path, default=DEFAULT_ADJUDICATIONS_PATH, help="Adjudication JSONL input.")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT_PATH, help="Expected snapshot JSON path.")
    parser.add_argument("--write-snapshot", action="store_true", help="Overwrite the snapshot with current aggregates.")
    parser.add_argument(
        "--min-review-coverage",
        type=float,
        default=None,
        help="Optional minimum reviewed-record coverage percentage required for each source trace.",
    )
    parser.add_argument(
        "--max-needs-discussion",
        type=int,
        default=None,
        help="Optional maximum number of records allowed to remain in needs_discussion.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        if args.write_snapshot:
            snapshot = write_current_snapshot(args.input, args.snapshot)
            print_summary(snapshot, True, args.snapshot)
            print("snapshot written")
            return 0

        result = check_snapshot(args.input, args.snapshot, args.min_review_coverage, args.max_needs_discussion)
    except (AdjudicationValidationError, AdjudicationReportError, AdjudicationRegressionError, OSError, ValueError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    print_summary(result["current"], bool(result["passed"]), args.snapshot)
    if result["differences"]:
        print("differences:")
        for difference in result["differences"]:
            print(f"- {difference}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
