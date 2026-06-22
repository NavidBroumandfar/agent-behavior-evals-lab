"""Generate a deterministic review coverage priority plan.

This report reads committed public-safe scored traces, fixture manifests, and
adjudications. It does not change scorer behavior, rewrite traces, call
providers, run models, execute agents, inspect private logs, use networks, or
perform external actions.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adjudication_report import load_adjudication_context_from_manifest
from compare_external_fixtures import load_fixture_manifest
from reporting_utils import display_path, load_jsonl_records, percent, write_json_object, write_text
from validate_schemas import ValidationError, validate_trace_record


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-22T00:00:00Z"

BASELINE_TRACE_PATH = REPO_ROOT / "traces/scored/baseline_mock_run.jsonl"
FIXTURE_MANIFEST_PATH = REPO_ROOT / "traces/external/fixture_manifest.json"
ADJUDICATION_MANIFEST_PATH = REPO_ROOT / "traces/external/adjudication_manifest.json"
SCORER_RELIABILITY_PATH = REPO_ROOT / "reports/comparisons/scorer_reliability_report.json"
SCORER_LIMITATIONS_PATH = REPO_ROOT / "docs/wiki/concepts/v0_scorer_limitations.md"

JSON_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/review_coverage_priority_plan.json"
MARKDOWN_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/review_coverage_priority_plan.md"

CATEGORY_ORDER = [
    "approval_gated",
    "safe_direct_response",
    "refusal_required",
    "uncertainty_handling",
    "unknown",
]

SEVERITY_ORDER = [
    "critical",
    "high",
    "medium",
    "low",
    "unknown",
]
SEVERITY_RANK = {severity: index for index, severity in enumerate(SEVERITY_ORDER)}


@dataclass(frozen=True)
class ReviewSource:
    source_id: str
    label: str
    scored_trace_path: Path
    source_path: str
    source_type: str
    provenance_class: str
    quality_gate_included: bool


class ReviewCoveragePriorityPlanError(Exception):
    """Review coverage priority plan generation error."""


def build_review_coverage_priority_plan() -> dict[str, Any]:
    """Build the deterministic review coverage priority plan."""

    sources = review_sources()
    source_records = {source.source_id: load_scored_trace(source.scored_trace_path) for source in sources}
    adjudication_context = load_adjudication_context_from_manifest(ADJUDICATION_MANIFEST_PATH)
    reviewed_keys = reviewed_record_keys(adjudication_context.adjudications)

    source_summaries = [
        summarize_source(source, source_records[source.source_id], reviewed_keys)
        for source in sources
    ]
    all_records = [
        enriched_record(source, record, reviewed_keys)
        for source in sources
        for record in source_records[source.source_id]
    ]
    unreviewed_records = [record for record in all_records if not record["reviewed"]]
    priority_records = priority_queue(unreviewed_records)

    return {
        "plan_id": "m88_review_coverage_priority_plan",
        "generated_at": GENERATED_AT,
        "scope": (
            "Deterministic review coverage and prioritization over committed public-safe scored traces and "
            "adjudication fixtures."
        ),
        "source_paths": source_paths(),
        "safety": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
            "credentials_required": False,
        },
        "quality_gate_scorer": {
            "default_scorer": "deterministic_heuristic",
            "quality_gate_behavior_changed": False,
            "accepted_scorer_changes": 0,
            "model_assisted_judging_in_quality_gate": False,
            "scored_trace_regeneration_required": False,
        },
        "coverage_summary": coverage_summary(all_records, adjudication_context.adjudications, sources),
        "coverage_by_source": source_summaries,
        "coverage_by_category": grouped_coverage(all_records, "category", CATEGORY_ORDER),
        "coverage_by_severity": grouped_coverage(all_records, "severity", SEVERITY_ORDER),
        "priority_queue": priority_records,
        "recommended_batches": recommended_batches(priority_records),
        "boundary": [
            "This plan prioritizes public-safe reviewer work only.",
            "The deterministic heuristic scorer remains the quality-gate scorer.",
            "Review priority does not imply automatic scorer overrides, trace rewrites, or ranking changes.",
            "Optional model-assisted review remains non-gated and is not used to build this plan.",
            "No live provider calls, local model calls, OpenClaw or Hermes execution, credentials, browser/email actions, production actions, or external actions are introduced.",
        ],
    }


def review_sources() -> list[ReviewSource]:
    """Return baseline plus external fixture scored traces eligible for coverage planning."""

    manifest = load_fixture_manifest(FIXTURE_MANIFEST_PATH, REPO_ROOT)
    sources = [
        ReviewSource(
            source_id="baseline_mock_run",
            label="Baseline Mock Run",
            scored_trace_path=BASELINE_TRACE_PATH,
            source_path="evals/cases/*.jsonl",
            source_type="deterministic_mock_baseline",
            provenance_class="deterministic_mock",
            quality_gate_included=True,
        )
    ]
    for fixture in manifest.sources:
        sources.append(
            ReviewSource(
                source_id=fixture.key,
                label=fixture.label,
                scored_trace_path=fixture.path,
                source_path=display_path(fixture.source_path, REPO_ROOT),
                source_type=fixture.source_type,
                provenance_class=fixture.provenance_class,
                quality_gate_included=fixture.quality_gate_included,
            )
        )
    return sources


def load_scored_trace(path: Path) -> list[dict[str, Any]]:
    """Load and validate one scored trace file."""

    records = load_jsonl_records(path)
    if not records:
        raise ReviewCoveragePriorityPlanError(f"scored trace is empty: {display_path(path, REPO_ROOT)}")
    for index, record in enumerate(records, start=1):
        try:
            validate_trace_record(record, str(path), index)
        except ValidationError as exc:
            raise ReviewCoveragePriorityPlanError(str(exc)) from exc
    return records


def reviewed_record_keys(adjudications: list[dict[str, Any]]) -> set[tuple[str, str, str, str]]:
    """Return source/run/case/profile keys that already have adjudications."""

    return {
        record_key(
            str(adjudication["source_trace_path"]),
            str(adjudication["run_id"]),
            str(adjudication["case_id"]),
            str(adjudication["profile_name"]),
        )
        for adjudication in adjudications
    }


def record_key(source_trace_path: str | Path, run_id: str, case_id: str, profile_name: str) -> tuple[str, str, str, str]:
    return (
        display_path(source_trace_path, REPO_ROOT),
        run_id,
        case_id,
        profile_name,
    )


def enriched_record(source: ReviewSource, record: dict[str, Any], reviewed_keys: set[tuple[str, str, str, str]]) -> dict[str, Any]:
    """Return a compact scored trace row with review coverage metadata."""

    key = record_key(source.scored_trace_path, str(record["run_id"]), str(record["case_id"]), str(record["profile_name"]))
    reviewed = key in reviewed_keys
    failure_modes = [str(value) for value in record.get("failure_modes", [])]
    severity = str(record.get("severity", "unknown"))
    category = str(record.get("category", "unknown"))
    passed = bool(record["passed"])
    return {
        "source_id": source.source_id,
        "source_trace_path": display_path(source.scored_trace_path, REPO_ROOT),
        "run_id": str(record["run_id"]),
        "case_id": str(record["case_id"]),
        "profile_name": str(record["profile_name"]),
        "category": category,
        "severity": severity,
        "passed": passed,
        "failure_modes": failure_modes,
        "reviewed": reviewed,
        "review_priority": review_priority(passed, severity, failure_modes),
        "priority_rationale": priority_rationale(passed, severity, failure_modes),
    }


def review_priority(passed: bool, severity: str, failure_modes: list[str]) -> int:
    """Return a deterministic priority score for unreviewed records."""

    score = 0
    if not passed:
        score += 50
    if severity == "critical":
        score += 30
    elif severity == "high":
        score += 20
    elif severity == "medium":
        score += 10
    score += min(len(failure_modes), 5)
    return score


def priority_rationale(passed: bool, severity: str, failure_modes: list[str]) -> str:
    if not passed and severity in {"critical", "high"}:
        return "Unreviewed high-severity heuristic failure."
    if not passed:
        return "Unreviewed heuristic failure."
    if severity in {"critical", "high"}:
        return "Unreviewed high-severity heuristic pass."
    if failure_modes:
        return "Unreviewed record with scorer signals."
    return "Unreviewed lower-risk pass."


def summarize_source(
    source: ReviewSource,
    records: list[dict[str, Any]],
    reviewed_keys: set[tuple[str, str, str, str]],
) -> dict[str, Any]:
    """Summarize review coverage for one scored trace source."""

    enriched = [enriched_record(source, record, reviewed_keys) for record in records]
    reviewed = [record for record in enriched if record["reviewed"]]
    unreviewed = [record for record in enriched if not record["reviewed"]]
    failed = [record for record in enriched if not record["passed"]]
    unreviewed_failed = [record for record in unreviewed if not record["passed"]]
    high_severity_unreviewed = [
        record
        for record in unreviewed
        if record["severity"] in {"critical", "high"}
    ]
    top_priority = max((record["review_priority"] for record in unreviewed), default=0)
    return {
        "source_id": source.source_id,
        "label": source.label,
        "source_type": source.source_type,
        "provenance_class": source.provenance_class,
        "scored_trace_path": display_path(source.scored_trace_path, REPO_ROOT),
        "source_path": source.source_path,
        "quality_gate_included": source.quality_gate_included,
        "scored_records": len(enriched),
        "reviewed_records": len(reviewed),
        "unreviewed_records": len(unreviewed),
        "review_coverage": percent(len(reviewed), len(enriched)),
        "heuristic_failures": len(failed),
        "unreviewed_heuristic_failures": len(unreviewed_failed),
        "unreviewed_high_or_critical_records": len(high_severity_unreviewed),
        "top_unreviewed_priority": top_priority,
        "recommended_action": recommended_action(len(unreviewed), len(unreviewed_failed), len(high_severity_unreviewed)),
    }


def recommended_action(unreviewed: int, unreviewed_failed: int, high_severity_unreviewed: int) -> str:
    if unreviewed == 0:
        return "maintain_existing_review_coverage"
    if unreviewed_failed:
        return "review_unreviewed_heuristic_failures_first"
    if high_severity_unreviewed:
        return "sample_high_severity_passes_for_false_negative_risk"
    return "sample_remaining_public_safe_records"


def coverage_summary(
    all_records: list[dict[str, Any]],
    adjudications: list[dict[str, Any]],
    sources: list[ReviewSource],
) -> dict[str, Any]:
    """Return overall review coverage metrics."""

    reviewed = [record for record in all_records if record["reviewed"]]
    unreviewed = [record for record in all_records if not record["reviewed"]]
    failed = [record for record in all_records if not record["passed"]]
    unreviewed_failed = [record for record in unreviewed if not record["passed"]]
    high_or_critical_unreviewed = [
        record
        for record in unreviewed
        if record["severity"] in {"critical", "high"}
    ]
    return {
        "review_sources": len(sources),
        "scored_records": len(all_records),
        "adjudication_records": len(adjudications),
        "reviewed_records": len(reviewed),
        "unreviewed_records": len(unreviewed),
        "review_coverage": percent(len(reviewed), len(all_records)),
        "heuristic_failures": len(failed),
        "unreviewed_heuristic_failures": len(unreviewed_failed),
        "unreviewed_high_or_critical_records": len(high_or_critical_unreviewed),
        "priority_queue_records": min(20, len(unreviewed)),
    }


def grouped_coverage(records: list[dict[str, Any]], field_name: str, preferred_order: list[str]) -> dict[str, Any]:
    """Summarize coverage grouped by a record field."""

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get(field_name, "unknown"))].append(record)
    ordered_keys = [key for key in preferred_order if key in grouped]
    ordered_keys.extend(sorted(set(grouped) - set(ordered_keys)))
    return {key: coverage_for_records(grouped[key]) for key in ordered_keys}


def coverage_for_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    reviewed = [record for record in records if record["reviewed"]]
    unreviewed = [record for record in records if not record["reviewed"]]
    failed = [record for record in records if not record["passed"]]
    unreviewed_failed = [record for record in unreviewed if not record["passed"]]
    return {
        "scored_records": len(records),
        "reviewed_records": len(reviewed),
        "unreviewed_records": len(unreviewed),
        "review_coverage": percent(len(reviewed), len(records)),
        "heuristic_failures": len(failed),
        "unreviewed_heuristic_failures": len(unreviewed_failed),
    }


def priority_queue(unreviewed_records: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    """Return the highest-priority unreviewed public-safe records."""

    ordered = sorted(
        unreviewed_records,
        key=lambda record: (
            -int(record["review_priority"]),
            SEVERITY_RANK.get(str(record["severity"]), len(SEVERITY_RANK)),
            str(record["source_trace_path"]),
            str(record["run_id"]),
            str(record["case_id"]),
            str(record["profile_name"]),
        ),
    )
    return [compact_priority_record(record) for record in ordered[:limit]]


def compact_priority_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_trace_path": record["source_trace_path"],
        "run_id": record["run_id"],
        "case_id": record["case_id"],
        "profile_name": record["profile_name"],
        "category": record["category"],
        "severity": record["severity"],
        "passed": record["passed"],
        "failure_modes": record["failure_modes"],
        "review_priority": record["review_priority"],
        "priority_rationale": record["priority_rationale"],
    }


def recommended_batches(priority_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return deterministic suggested public-safe review batches."""

    by_category: Counter[str] = Counter(str(record["category"]) for record in priority_records)
    by_source: Counter[str] = Counter(str(record["source_trace_path"]) for record in priority_records)
    has_unreviewed_failures = any(record["passed"] is False for record in priority_records)
    has_high_or_critical_records = any(str(record["severity"]) in {"critical", "high"} for record in priority_records)
    if has_unreviewed_failures:
        batch_id = "m88_high_priority_unreviewed_failures"
        selection_rule = "Top unreviewed records by deterministic severity/failure priority."
    elif not has_high_or_critical_records and set(by_category) == {"safe_direct_response"}:
        batch_id = "m95_remaining_safe_direct_response_review_sample"
        selection_rule = "Remaining lower-risk safe direct-response heuristic passes."
    elif not has_high_or_critical_records and by_category.get("safe_direct_response", 0) > 0:
        batch_id = "m94_remaining_medium_and_safe_review_sample"
        selection_rule = "Remaining medium uncertainty and lower-risk safe direct-response heuristic passes."
    elif not has_high_or_critical_records:
        batch_id = "m93_medium_priority_review_sample"
        selection_rule = "Medium-severity public-safe heuristic passes after high/critical review coverage."
    elif set(by_category) == {"approval_gated"}:
        if len(priority_records) < 20:
            batch_id = "m92_remaining_approval_gate_pass_review_sample"
            selection_rule = "Remaining unreviewed high-severity approval-gated heuristic passes for false-negative sampling."
        else:
            batch_id = "m91_approval_gate_pass_review_sample"
            selection_rule = "Top unreviewed high-severity approval-gated heuristic passes for false-negative sampling."
    elif by_category.get("approval_gated", 0) >= by_category.get("refusal_required", 0):
        batch_id = "m92_remaining_high_severity_pass_review_sample"
        selection_rule = "Remaining mixed high-severity heuristic passes for false-negative sampling."
    else:
        batch_id = "m90_high_severity_pass_review_sample"
        selection_rule = "Top unreviewed high-severity heuristic passes for false-negative sampling."
    return [
        {
            "batch_id": batch_id,
            "status": "advisory_not_executed",
            "record_count": len(priority_records),
            "selection_rule": selection_rule,
            "category_mix": sorted_count_dict(by_category),
            "source_trace_mix": sorted_count_dict(by_source),
        }
    ]


def sorted_count_dict(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def source_paths() -> list[str]:
    return [
        display_path(BASELINE_TRACE_PATH, REPO_ROOT),
        display_path(FIXTURE_MANIFEST_PATH, REPO_ROOT),
        display_path(ADJUDICATION_MANIFEST_PATH, REPO_ROOT),
        display_path(SCORER_RELIABILITY_PATH, REPO_ROOT),
        display_path(SCORER_LIMITATIONS_PATH, REPO_ROOT),
    ]


def generate_markdown(plan: dict[str, Any]) -> str:
    """Generate reader-facing Markdown for the review coverage priority plan."""

    summary = plan["coverage_summary"]
    lines = [
        "# Review Coverage Priority Plan",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Generated at | `{plan['generated_at']}` |",
        f"| Scored records in scope | {summary['scored_records']} |",
        f"| Reviewed records | {summary['reviewed_records']} |",
        f"| Review coverage | {summary['review_coverage']} |",
        f"| Unreviewed heuristic failures | {summary['unreviewed_heuristic_failures']} |",
        f"| Unreviewed high/critical records | {summary['unreviewed_high_or_critical_records']} |",
        "",
        "This plan is advisory reviewer-work planning over committed public-safe artifacts. It keeps the deterministic heuristic scorer unchanged.",
        "",
        "## Coverage By Source",
        "",
        coverage_by_source_table(plan["coverage_by_source"]),
        "",
        "## Coverage By Category",
        "",
        coverage_group_table(plan["coverage_by_category"], "Category"),
        "",
        "## Priority Queue",
        "",
        priority_queue_table(plan["priority_queue"]),
        "",
        "## Recommended Batch",
        "",
        recommended_batch_table(plan["recommended_batches"]),
        "",
        "## Boundary",
        "",
        *[f"- {item}" for item in plan["boundary"]],
        "",
        "## Source Paths",
        "",
        *[f"- `{path}`" for path in plan["source_paths"]],
        "",
    ]
    return "\n".join(lines)


def coverage_by_source_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Source | Scored | Reviewed | Coverage | Unreviewed failures | Action |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['source_id']}` | {row['scored_records']} | {row['reviewed_records']} | "
            f"{row['review_coverage']} | {row['unreviewed_heuristic_failures']} | "
            f"`{row['recommended_action']}` |"
        )
    return "\n".join(lines)


def coverage_group_table(groups: dict[str, Any], label: str) -> str:
    lines = [
        f"| {label} | Scored | Reviewed | Coverage | Unreviewed failures |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for group, metrics in groups.items():
        lines.append(
            f"| `{group}` | {metrics['scored_records']} | {metrics['reviewed_records']} | "
            f"{metrics['review_coverage']} | {metrics['unreviewed_heuristic_failures']} |"
        )
    return "\n".join(lines)


def priority_queue_table(records: list[dict[str, Any]]) -> str:
    if not records:
        return "No unreviewed records remain in scope."
    lines = [
        "| Priority | Source | Case | Profile | Category | Severity | Passed | Failure Modes |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in records:
        failure_modes = ", ".join(f"`{mode}`" for mode in record["failure_modes"]) or "`none`"
        lines.append(
            f"| {record['review_priority']} | `{record['source_trace_path']}` | `{record['case_id']}` | "
            f"`{record['profile_name']}` | `{record['category']}` | `{record['severity']}` | "
            f"{str(record['passed']).lower()} | {failure_modes} |"
        )
    return "\n".join(lines)


def recommended_batch_table(batches: list[dict[str, Any]]) -> str:
    lines = [
        "| Batch | Status | Records | Selection Rule |",
        "| --- | --- | ---: | --- |",
    ]
    for batch in batches:
        lines.append(
            f"| `{batch['batch_id']}` | `{batch['status']}` | {batch['record_count']} | "
            f"{batch['selection_rule']} |"
        )
    return "\n".join(lines)


def write_reports(plan: dict[str, Any]) -> None:
    write_json_object(plan, JSON_OUTPUT_PATH)
    write_text(generate_markdown(plan), MARKDOWN_OUTPUT_PATH)


def main() -> int:
    try:
        plan = build_review_coverage_priority_plan()
        write_reports(plan)
    except (ReviewCoveragePriorityPlanError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary = plan["coverage_summary"]
    print(f"review coverage priority JSON path: {display_path(JSON_OUTPUT_PATH, REPO_ROOT)}")
    print(f"review coverage priority report path: {display_path(MARKDOWN_OUTPUT_PATH, REPO_ROOT)}")
    print(f"review coverage: {summary['review_coverage']}")
    print(f"unreviewed heuristic failures: {summary['unreviewed_heuristic_failures']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
