"""Check adjudication-aware report aggregates against a saved snapshot.

This command validates deterministic reviewer-decision counts. It reads saved
adjudications and scored traces only; it does not rescore outputs, rewrite
traces, call models, execute agents, or collect live outputs.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from adjudication_report import (
    DEFAULT_ADJUDICATION_MANIFEST_PATH,
    DEFAULT_ADJUDICATIONS_PATH,
    DECISION_ORDER,
    AdjudicationContext,
    AdjudicationQualityGateThresholds,
    AdjudicationReportError,
    load_adjudication_context,
    load_adjudication_context_from_fixtures,
    load_adjudication_manifest_data,
    select_adjudication_input,
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
        "adjudication_input": display_path(adjudications_path, repo_root),
        "adjudication_fixture_count": len(context.fixtures),
        "adjudication_fixture_statuses": _adjudication_fixture_statuses(context),
        "adjudication_fixtures": _adjudication_fixtures_summary(context),
        "adjudication_records": len(context.adjudications),
        "source_trace_count": len(context.source_records_by_path),
        "source_trace_records": len(source_records),
        "reviewer_count": len({str(record["reviewer_id"]) for record in context.adjudications}),
        "reviewer_decisions": {decision: decision_counts.get(decision, 0) for decision in DECISION_ORDER},
        "result_summary": _result_summary(context.adjudications),
        "review_coverage_by_source_trace": _review_coverage_by_source_trace(context),
        "review_coverage_by_profile": _review_coverage_by_profile(context),
        "review_coverage_by_category": _review_coverage_by_category(context),
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
    manifest_path: Path | None = None,
    min_source_review_coverage: dict[str, float] | None = None,
    min_profile_review_coverage: dict[str, float] | None = None,
    min_category_review_coverage: dict[str, float] | None = None,
    max_fixture_needs_discussion: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Load current adjudication aggregates and compare them to the saved snapshot."""

    context, input_path, manifest_thresholds = load_regression_context(adjudications_path, manifest_path)
    effective_thresholds = quality_gate_thresholds_with_overrides(
        manifest_thresholds,
        min_review_coverage=min_review_coverage,
        max_needs_discussion=max_needs_discussion,
        min_source_review_coverage=min_source_review_coverage,
        min_profile_review_coverage=min_profile_review_coverage,
        min_category_review_coverage=min_category_review_coverage,
        max_fixture_needs_discussion=max_fixture_needs_discussion,
    )
    expected = load_json_object(snapshot_path)
    current = build_snapshot(context, input_path)
    differences = compare_snapshots(expected, current)
    differences.extend(
        threshold_violations(
            current,
            effective_thresholds.min_review_coverage,
            effective_thresholds.max_needs_discussion,
            effective_thresholds.min_source_review_coverage,
            effective_thresholds.min_profile_review_coverage,
            effective_thresholds.min_category_review_coverage,
            effective_thresholds.max_fixture_needs_discussion,
        )
    )
    return {
        "current": current,
        "differences": differences,
        "passed": not differences,
    }


def write_current_snapshot(
    adjudications_path: Path = DEFAULT_ADJUDICATIONS_PATH,
    snapshot_path: Path = DEFAULT_SNAPSHOT_PATH,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Write the current adjudication aggregate snapshot."""

    context, input_path, _manifest_thresholds = load_regression_context(adjudications_path, manifest_path)
    snapshot = build_snapshot(context, input_path)
    write_json_object(snapshot, snapshot_path)
    return snapshot


def load_regression_context(
    adjudications_path: Path = DEFAULT_ADJUDICATIONS_PATH,
    manifest_path: Path | None = None,
) -> tuple[AdjudicationContext, Path, AdjudicationQualityGateThresholds]:
    """Load adjudication inputs and manifest-declared quality gate policy."""

    if manifest_path is None:
        return load_adjudication_context(adjudications_path), adjudications_path, AdjudicationQualityGateThresholds()

    manifest = load_adjudication_manifest_data(manifest_path)
    context = load_adjudication_context_from_fixtures(manifest.fixtures)
    return context, manifest_path, manifest.quality_gate_thresholds


def quality_gate_thresholds_with_overrides(
    manifest_thresholds: AdjudicationQualityGateThresholds,
    min_review_coverage: float | None = None,
    max_needs_discussion: int | None = None,
    min_source_review_coverage: dict[str, float] | None = None,
    min_profile_review_coverage: dict[str, float] | None = None,
    min_category_review_coverage: dict[str, float] | None = None,
    max_fixture_needs_discussion: dict[str, int] | None = None,
) -> AdjudicationQualityGateThresholds:
    """Merge manifest quality-gate defaults with explicit CLI-style overrides."""

    return AdjudicationQualityGateThresholds(
        min_review_coverage=(
            manifest_thresholds.min_review_coverage
            if min_review_coverage is None
            else min_review_coverage
        ),
        max_needs_discussion=(
            manifest_thresholds.max_needs_discussion
            if max_needs_discussion is None
            else max_needs_discussion
        ),
        min_source_review_coverage={
            **manifest_thresholds.min_source_review_coverage,
            **(min_source_review_coverage or {}),
        },
        min_profile_review_coverage={
            **manifest_thresholds.min_profile_review_coverage,
            **(min_profile_review_coverage or {}),
        },
        min_category_review_coverage={
            **manifest_thresholds.min_category_review_coverage,
            **(min_category_review_coverage or {}),
        },
        max_fixture_needs_discussion={
            **manifest_thresholds.max_fixture_needs_discussion,
            **(max_fixture_needs_discussion or {}),
        },
    )


def print_summary(snapshot: dict[str, Any], passed: bool, snapshot_path: Path) -> None:
    """Print a concise adjudication regression summary."""

    print(f"adjudication input: {snapshot['adjudication_input']}")
    print(f"snapshot path: {display_path(snapshot_path)}")
    print(f"adjudication fixture families: {snapshot['adjudication_fixture_count']}")
    print(f"adjudication fixture statuses: {_format_counts(snapshot['adjudication_fixture_statuses'])}")
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
    min_source_review_coverage: dict[str, float] | None = None,
    min_profile_review_coverage: dict[str, float] | None = None,
    min_category_review_coverage: dict[str, float] | None = None,
    max_fixture_needs_discussion: dict[str, int] | None = None,
) -> list[str]:
    """Return review threshold violations for optional quality gates."""

    violations: list[str] = []
    if min_review_coverage is not None or min_source_review_coverage:
        coverage_by_source = snapshot.get("review_coverage_by_source_trace", {})
        if not isinstance(coverage_by_source, dict):
            raise AdjudicationRegressionError("review_coverage_by_source_trace must be an object")
        for source_trace, coverage in sorted(coverage_by_source.items()):
            if not isinstance(coverage, dict):
                raise AdjudicationRegressionError(f"{source_trace}.review_coverage must be an object")
            threshold = (min_source_review_coverage or {}).get(source_trace, min_review_coverage)
            if threshold is None:
                continue
            actual = _parse_percent(str(coverage.get("review_coverage", "0.0%")))
            if actual < threshold:
                violations.append(
                    f"{source_trace}.review_coverage: expected at least {threshold:.1f}%, found {actual:.1f}%"
                )

    if max_needs_discussion is not None:
        needs_discussion = snapshot.get("reviewer_decisions", {}).get("needs_discussion")
        if not isinstance(needs_discussion, int):
            raise AdjudicationRegressionError("reviewer_decisions.needs_discussion must be an integer")
        if needs_discussion > max_needs_discussion:
            violations.append(
                f"reviewer_decisions.needs_discussion: expected at most {max_needs_discussion}, found {needs_discussion}"
            )

    violations.extend(
        coverage_threshold_violations(
            snapshot,
            "review_coverage_by_profile",
            "profile",
            min_profile_review_coverage,
        )
    )
    violations.extend(
        coverage_threshold_violations(
            snapshot,
            "review_coverage_by_category",
            "category",
            min_category_review_coverage,
        )
    )
    violations.extend(fixture_needs_discussion_violations(snapshot, max_fixture_needs_discussion))

    return violations


def coverage_threshold_violations(
    snapshot: dict[str, Any],
    snapshot_key: str,
    label: str,
    thresholds: dict[str, float] | None,
) -> list[str]:
    if not thresholds:
        return []

    coverage_by_group = snapshot.get(snapshot_key)
    if not isinstance(coverage_by_group, dict):
        raise AdjudicationRegressionError(f"{snapshot_key} must be an object")

    violations: list[str] = []
    for group_name, minimum in sorted(thresholds.items()):
        coverage = coverage_by_group.get(group_name)
        if not isinstance(coverage, dict):
            violations.append(f"{label}.{group_name}.review_coverage: missing coverage group")
            continue
        actual = _parse_percent(str(coverage.get("review_coverage", "0.0%")))
        if actual < minimum:
            violations.append(
                f"{label}.{group_name}.review_coverage: expected at least {minimum:.1f}%, found {actual:.1f}%"
            )
    return violations


def fixture_needs_discussion_violations(
    snapshot: dict[str, Any],
    thresholds: dict[str, int] | None,
) -> list[str]:
    if not thresholds:
        return []

    fixtures = snapshot.get("adjudication_fixtures")
    if not isinstance(fixtures, dict):
        raise AdjudicationRegressionError("adjudication_fixtures must be an object")

    violations: list[str] = []
    for fixture_id, maximum in sorted(thresholds.items()):
        fixture = fixtures.get(fixture_id)
        if not isinstance(fixture, dict):
            violations.append(f"fixture.{fixture_id}.needs_discussion: missing fixture")
            continue
        reviewer_decisions = fixture.get("reviewer_decisions")
        if not isinstance(reviewer_decisions, dict):
            raise AdjudicationRegressionError(f"adjudication_fixtures.{fixture_id}.reviewer_decisions must be an object")
        needs_discussion = reviewer_decisions.get("needs_discussion")
        if not isinstance(needs_discussion, int):
            raise AdjudicationRegressionError(
                f"adjudication_fixtures.{fixture_id}.reviewer_decisions.needs_discussion must be an integer"
            )
        if needs_discussion > maximum:
            violations.append(
                f"fixture.{fixture_id}.needs_discussion: expected at most {maximum}, found {needs_discussion}"
            )
    return violations


def _adjudication_fixtures_summary(context: AdjudicationContext) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for adjudication in context.adjudications:
        fixture = context.fixture_by_adjudication_id[adjudication["adjudication_id"]]
        grouped[fixture.fixture_id].append(adjudication)

    summary: dict[str, dict[str, Any]] = {}
    for fixture in context.fixtures:
        records = grouped[fixture.fixture_id]
        decision_counts = Counter(str(record["reviewer_decision"]) for record in records)
        summary[fixture.fixture_id] = {
            "label": fixture.label,
            "path": display_path(fixture.path),
            "records": len(records),
            "quality_gate_included": fixture.quality_gate_included,
            "review_status": fixture.review_status,
            "owner": fixture.owner,
            "status_notes": fixture.status_notes,
            "last_reviewed_at": fixture.last_reviewed_at,
            "reviewer_decisions": {decision: decision_counts.get(decision, 0) for decision in DECISION_ORDER},
        }
    return summary


def _adjudication_fixture_statuses(context: AdjudicationContext) -> dict[str, int]:
    counts = Counter(fixture.review_status for fixture in context.fixtures)
    return {status: counts[status] for status in sorted(counts)}


def _format_counts(counts: Any) -> str:
    if not isinstance(counts, dict) or not counts:
        return "none"
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))


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


def _review_coverage_by_profile(context: AdjudicationContext) -> dict[str, dict[str, Any]]:
    source_counts: Counter[str] = Counter()
    for records in context.source_records_by_path.values():
        for record in records:
            source_counts[str(record.get("profile_name", "unknown"))] += 1

    reviewed_by_profile: dict[str, set[tuple[str, str, str, str]]] = defaultdict(set)
    for adjudication in context.adjudications:
        profile = str(adjudication["profile_name"])
        reviewed_by_profile[profile].add(_reviewed_record_key(adjudication))

    return _coverage_by_group(source_counts, reviewed_by_profile)


def _review_coverage_by_category(context: AdjudicationContext) -> dict[str, dict[str, Any]]:
    source_counts: Counter[str] = Counter()
    for records in context.source_records_by_path.values():
        for record in records:
            source_counts[str(record.get("category", "unknown"))] += 1

    reviewed_by_category: dict[str, set[tuple[str, str, str, str]]] = defaultdict(set)
    for adjudication in context.adjudications:
        source_record = context.source_record_by_adjudication_id[adjudication["adjudication_id"]]
        category = str(source_record.get("category", "unknown"))
        reviewed_by_category[category].add(_reviewed_record_key(adjudication))

    return _coverage_by_group(source_counts, reviewed_by_category)


def _coverage_by_group(
    source_counts: Counter[str],
    reviewed_by_group: dict[str, set[tuple[str, str, str, str]]],
) -> dict[str, dict[str, Any]]:
    coverage: dict[str, dict[str, Any]] = {}
    for group_name in sorted(source_counts):
        total = source_counts[group_name]
        reviewed = len(reviewed_by_group[group_name])
        coverage[group_name] = {
            "source_records": total,
            "reviewed_records": reviewed,
            "unreviewed_records": total - reviewed,
            "review_coverage": percent(reviewed, total),
        }
    return coverage


def _reviewed_record_key(adjudication: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        display_path(adjudication["source_trace_path"]),
        str(adjudication["run_id"]),
        str(adjudication["case_id"]),
        str(adjudication["profile_name"]),
    )


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


def parse_percent_thresholds(values: list[str], option_name: str) -> dict[str, float]:
    thresholds: dict[str, float] = {}
    for value in values:
        key, raw_threshold = parse_key_value(value, option_name)
        try:
            threshold = float(raw_threshold)
        except ValueError as exc:
            raise AdjudicationRegressionError(f"{option_name} threshold for {key} must be a number") from exc
        threshold = validate_percent_threshold(threshold, f"{option_name} threshold for {key}")
        if key in thresholds:
            raise AdjudicationRegressionError(f"{option_name} duplicate threshold for {key}")
        thresholds[key] = threshold
    return thresholds


def parse_int_thresholds(values: list[str], option_name: str) -> dict[str, int]:
    thresholds: dict[str, int] = {}
    for value in values:
        key, raw_threshold = parse_key_value(value, option_name)
        try:
            threshold = int(raw_threshold)
        except ValueError as exc:
            raise AdjudicationRegressionError(f"{option_name} threshold for {key} must be an integer") from exc
        threshold = validate_non_negative_int_threshold(threshold, f"{option_name} threshold for {key}")
        if key in thresholds:
            raise AdjudicationRegressionError(f"{option_name} duplicate threshold for {key}")
        thresholds[key] = threshold
    return thresholds


def parse_key_value(value: str, option_name: str) -> tuple[str, str]:
    if "=" not in value:
        raise AdjudicationRegressionError(f"{option_name} values must use name=value format")
    key, raw_threshold = value.split("=", 1)
    if not key.strip() or not raw_threshold.strip():
        raise AdjudicationRegressionError(f"{option_name} values must use non-empty name=value format")
    return key.strip(), raw_threshold.strip()


def validate_percent_threshold(value: float, context: str) -> float:
    if not math.isfinite(value):
        raise AdjudicationRegressionError(f"{context} must be a finite number")
    if value < 0 or value > 100:
        raise AdjudicationRegressionError(f"{context} must be between 0 and 100")
    return value


def validate_non_negative_int_threshold(value: int, context: str) -> int:
    if value < 0:
        raise AdjudicationRegressionError(f"{context} must be >= 0")
    return value


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check adjudication report aggregates against a snapshot.")
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help=(
            "Adjudication JSONL input for single-fixture mode. "
            f"Defaults to {display_path(DEFAULT_ADJUDICATIONS_PATH)} only when no manifest is selected."
        ),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help=(
            "Optional adjudication fixture manifest. "
            f"Defaults to {display_path(DEFAULT_ADJUDICATION_MANIFEST_PATH)} when it exists and --input is omitted."
        ),
    )
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT_PATH, help="Expected snapshot JSON path.")
    parser.add_argument("--write-snapshot", action="store_true", help="Overwrite the snapshot with current aggregates.")
    parser.add_argument(
        "--min-review-coverage",
        type=float,
        default=None,
        help="Override the manifest/default minimum reviewed-record coverage percentage required for each source trace.",
    )
    parser.add_argument(
        "--max-needs-discussion",
        type=int,
        default=None,
        help="Override the manifest/default maximum number of records allowed to remain in needs_discussion.",
    )
    parser.add_argument(
        "--min-profile-review-coverage",
        action="append",
        default=[],
        metavar="PROFILE=PERCENT",
        help="Override or add a minimum reviewed-record coverage percentage for a specific profile. Repeatable.",
    )
    parser.add_argument(
        "--min-source-review-coverage",
        action="append",
        default=[],
        metavar="SOURCE_TRACE=PERCENT",
        help="Override or add a minimum reviewed-record coverage percentage for a specific source trace. Repeatable.",
    )
    parser.add_argument(
        "--min-category-review-coverage",
        action="append",
        default=[],
        metavar="CATEGORY=PERCENT",
        help="Override or add a minimum reviewed-record coverage percentage for a specific category. Repeatable.",
    )
    parser.add_argument(
        "--max-fixture-needs-discussion",
        action="append",
        default=[],
        metavar="FIXTURE=COUNT",
        help="Override or add a maximum needs_discussion count for a specific adjudication fixture. Repeatable.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    adjudications_path, manifest_path = select_adjudication_input(args.input, args.manifest)

    try:
        min_review_coverage = (
            None
            if args.min_review_coverage is None
            else validate_percent_threshold(args.min_review_coverage, "--min-review-coverage")
        )
        max_needs_discussion = (
            None
            if args.max_needs_discussion is None
            else validate_non_negative_int_threshold(args.max_needs_discussion, "--max-needs-discussion")
        )
        min_profile_review_coverage = parse_percent_thresholds(
            args.min_profile_review_coverage,
            "--min-profile-review-coverage",
        )
        min_source_review_coverage = parse_percent_thresholds(
            args.min_source_review_coverage,
            "--min-source-review-coverage",
        )
        min_category_review_coverage = parse_percent_thresholds(
            args.min_category_review_coverage,
            "--min-category-review-coverage",
        )
        max_fixture_needs_discussion = parse_int_thresholds(
            args.max_fixture_needs_discussion,
            "--max-fixture-needs-discussion",
        )
        if args.write_snapshot:
            snapshot = write_current_snapshot(adjudications_path, args.snapshot, manifest_path)
            print_summary(snapshot, True, args.snapshot)
            print("snapshot written")
            return 0

        result = check_snapshot(
            adjudications_path,
            args.snapshot,
            min_review_coverage,
            max_needs_discussion,
            manifest_path,
            min_source_review_coverage=min_source_review_coverage,
            min_profile_review_coverage=min_profile_review_coverage,
            min_category_review_coverage=min_category_review_coverage,
            max_fixture_needs_discussion=max_fixture_needs_discussion,
        )
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
