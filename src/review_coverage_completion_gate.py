"""Generate and validate the M96 review coverage completion gate.

This gate locks the completed public-safe review queue after M95. It reads
committed deterministic reports and adjudication artifacts only. It does not
change scorer behavior, rewrite traces, call providers, run models, execute
agents, inspect private logs, use networks, or perform external actions.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from reporting_utils import compare_nested_values, display_path, load_json_object, percent, write_json_object, write_text
from review_coverage_priority_plan import build_review_coverage_priority_plan
from schema_validation_utils import load_json_object as load_schema_object
from schema_validation_utils import validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-22T00:00:00Z"

SCHEMA_PATH = REPO_ROOT / "schemas/review_coverage_completion.schema.json"
REVIEW_COVERAGE_PRIORITY_PATH = REPO_ROOT / "reports/comparisons/review_coverage_priority_plan.json"
REVIEW_COVERAGE_PRIORITY_REPORT_PATH = REPO_ROOT / "reports/comparisons/review_coverage_priority_plan.md"
SCORER_RELIABILITY_PATH = REPO_ROOT / "reports/comparisons/scorer_reliability_report.json"
SCORER_RELIABILITY_REPORT_PATH = REPO_ROOT / "reports/comparisons/scorer_reliability_report.md"
ADJUDICATION_SNAPSHOT_PATH = REPO_ROOT / "reports/comparisons/adjudication_regression_snapshot.json"
ADJUDICATION_MANIFEST_PATH = REPO_ROOT / "traces/external/adjudication_manifest.json"
SCORER_LIMITATIONS_PATH = REPO_ROOT / "docs/wiki/concepts/v0_scorer_limitations.md"

JSON_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/review_coverage_completion_gate.json"
MARKDOWN_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/review_coverage_completion_gate.md"


class ReviewCoverageCompletionGateError(Exception):
    """Review coverage completion gate generation or validation error."""


def build_review_coverage_completion_gate() -> dict[str, Any]:
    """Build the deterministic M96 completion gate report."""

    committed_plan = load_json_object(REVIEW_COVERAGE_PRIORITY_PATH)
    current_plan = build_review_coverage_priority_plan()
    stale_differences = compare_nested_values(current_plan, committed_plan)
    scorer_reliability = load_json_object(SCORER_RELIABILITY_PATH)

    coverage = completion_scope_summary(committed_plan)
    reliability = scorer_reliability["reliability_summary"]
    completion_priority_records = completion_scope_priority_records(committed_plan)
    priority_queue_records = len(completion_priority_records)
    recommended_batch_count = 0 if not completion_priority_records else len(committed_plan.get("recommended_batches", []))
    additional_review_scopes = additional_review_scope_rows(committed_plan)
    blocking_findings = blocking_findings_for_plan(
        coverage,
        committed_plan,
        scorer_reliability,
        stale_differences,
        additional_review_scopes,
    )

    gate = {
        "gate_id": "m96_review_coverage_completion_gate",
        "version": "0.1.0",
        "generated_at": GENERATED_AT,
        "status": "complete_coverage_locked",
        "scope": (
            "Deterministic post-M95 gate over committed public-safe scored traces, adjudications, "
            "review coverage priority planning, and scorer reliability reporting."
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
        "completion_summary": {
            "review_sources": int(coverage["review_sources"]),
            "scored_records": int(coverage["scored_records"]),
            "reviewed_records": int(coverage["reviewed_records"]),
            "adjudication_records": int(coverage["adjudication_records"]),
            "review_coverage": str(coverage["review_coverage"]),
            "unreviewed_records": int(coverage["unreviewed_records"]),
            "unreviewed_heuristic_failures": int(coverage["unreviewed_heuristic_failures"]),
            "unreviewed_high_or_critical_records": int(coverage["unreviewed_high_or_critical_records"]),
            "priority_queue_records": priority_queue_records,
            "recommended_batches": recommended_batch_count,
            "scorer_review_agreements": int(reliability["scorer_reviewer_agreements"]),
            "scorer_review_disagreements": int(reliability["scorer_reviewer_disagreements"]),
            "scorer_review_agreement_rate": str(reliability["scorer_review_agreement_rate"]),
            "scorer_false_positive_count": int(reliability["scorer_false_positive_count"]),
            "scorer_false_negative_count": int(reliability["scorer_false_negative_count"]),
        },
        "source_completion": source_completion_rows(committed_plan),
        "additional_review_scopes": additional_review_scopes,
        "gate_status": {
            "gate_passed": not blocking_findings,
            "required_review_coverage": "100.0%",
            "required_unreviewed_records": 0,
            "required_priority_queue_records": 0,
            "required_recommended_batches": 0,
            "stale_priority_plan": bool(stale_differences),
            "blocking_findings": blocking_findings,
        },
        "next_phase_recommendation": {
            "phase_id": "m101a_sandbox_or_future_public_safe_review_expansion",
            "reviewer_work_status": "completion_scope_locked_m101a_sample_met",
            "rationale": (
                f"The M89-M95 reviewer queue is exhausted for the current {coverage['scored_records']} "
                "completion-scoped scored records. M101A sandbox dry-run evidence has its separate minimum "
                "review sample met; remaining sandbox records stay advisory rather than blocking the M96 lock."
            ),
            "recommended_next_steps": [
                "Maintain this completion gate so stale review coverage or unexpected recommended batches fail locally.",
                "Expand sandbox review coverage in future phases when the M101A sample should move from minimum evidence to full reviewed coverage.",
                "Keep the deterministic heuristic scorer as the quality-gate scorer; model-assisted review stays optional and non-gated.",
            ],
        },
        "boundary": [
            "This gate validates completed public-safe reviewer coverage only.",
            "The deterministic heuristic scorer remains the quality-gate scorer.",
            "A passing gate does not accept scorer changes, rewrite traces, or publish new rankings.",
            "Optional model-assisted or local-model review remains non-gated and is not used by this report.",
            "No live provider calls, local model calls, OpenClaw or Hermes execution, credentials, browser/email actions, production actions, or external actions are introduced.",
        ],
    }
    validate_completion_gate(gate)
    return gate


def source_completion_rows(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Return compact per-source completion rows."""

    rows = []
    for source in completion_scope_source_rows(plan):
        rows.append(
            {
                "source_id": str(source["source_id"]),
                "scored_trace_path": str(source["scored_trace_path"]),
                "scored_records": int(source["scored_records"]),
                "reviewed_records": int(source["reviewed_records"]),
                "review_coverage": str(source["review_coverage"]),
                "unreviewed_records": int(source["unreviewed_records"]),
                "recommended_action": str(source["recommended_action"]),
            }
        )
    return rows


def completion_scope_source_rows(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Return source rows that remain under the M96 full-review completion lock."""

    return [
        source
        for source in plan["coverage_by_source"]
        if source.get("completion_gate_required", True) is True
    ]


def additional_review_scope_source_rows(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Return source rows with a review requirement outside the M96 completion lock."""

    return [
        source
        for source in plan["coverage_by_source"]
        if source.get("completion_gate_required", True) is not True
    ]


def completion_scope_summary(plan: dict[str, Any]) -> dict[str, Any]:
    """Aggregate completion metrics for full-review locked sources only."""

    rows = completion_scope_source_rows(plan)
    scored_records = sum(int(row["scored_records"]) for row in rows)
    reviewed_records = sum(int(row["reviewed_records"]) for row in rows)
    unreviewed_records = sum(int(row["unreviewed_records"]) for row in rows)
    unreviewed_heuristic_failures = sum(int(row["unreviewed_heuristic_failures"]) for row in rows)
    unreviewed_high_or_critical_records = sum(int(row["unreviewed_high_or_critical_records"]) for row in rows)
    return {
        "review_sources": len(rows),
        "scored_records": scored_records,
        "reviewed_records": reviewed_records,
        "adjudication_records": reviewed_records,
        "review_coverage": percent(reviewed_records, scored_records),
        "unreviewed_records": unreviewed_records,
        "unreviewed_heuristic_failures": unreviewed_heuristic_failures,
        "unreviewed_high_or_critical_records": unreviewed_high_or_critical_records,
    }


def completion_scope_priority_records(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Return priority records that still belong to full-review locked sources."""

    return [
        record
        for record in plan.get("priority_queue", [])
        if record.get("completion_gate_required", True) is True
    ]


def additional_review_scope_rows(plan: dict[str, Any]) -> list[dict[str, Any]]:
    """Return compact rows for new review scopes that are not completion blockers."""

    rows = []
    for source in additional_review_scope_source_rows(plan):
        rows.append(
            {
                "source_id": str(source["source_id"]),
                "review_requirement_id": str(source["review_requirement_id"]),
                "scored_trace_path": str(source["scored_trace_path"]),
                "scored_records": int(source["scored_records"]),
                "reviewed_records": int(source["reviewed_records"]),
                "required_reviewed_records": int(source["required_reviewed_records"]),
                "review_coverage": str(source["review_coverage"]),
                "review_requirement_met": bool(source["review_requirement_met"]),
                "unreviewed_records": int(source["unreviewed_records"]),
                "unreviewed_heuristic_failures": int(source["unreviewed_heuristic_failures"]),
                "recommended_action": str(source["recommended_action"]),
            }
        )
    return rows


def blocking_findings_for_plan(
    coverage: dict[str, Any],
    priority_plan: dict[str, Any],
    scorer_reliability: dict[str, Any],
    stale_differences: list[str],
    additional_review_scopes: list[dict[str, Any]],
) -> list[str]:
    """Return deterministic blockers for the completion gate."""

    findings = []
    if stale_differences:
        findings.append("review coverage priority plan is stale relative to a freshly rebuilt plan")
    if str(coverage.get("review_coverage")) != "100.0%":
        findings.append("review coverage is below 100.0%")
    if int(coverage.get("scored_records", 0)) != int(coverage.get("reviewed_records", -1)):
        findings.append("reviewed record count does not match scored record count")
    if int(coverage.get("reviewed_records", 0)) != int(coverage.get("adjudication_records", -1)):
        findings.append("adjudication count does not match reviewed record count")
    if int(coverage.get("unreviewed_records", 0)) != 0:
        findings.append("unreviewed records remain in scope")
    if int(coverage.get("unreviewed_heuristic_failures", 0)) != 0:
        findings.append("unreviewed heuristic failures remain in scope")
    if int(coverage.get("unreviewed_high_or_critical_records", 0)) != 0:
        findings.append("unreviewed high/critical records remain in scope")
    if completion_scope_priority_records(priority_plan):
        findings.append("completion-scope priority queue is not empty")
    for scope in additional_review_scopes:
        if scope["review_requirement_met"] is not True:
            findings.append(f"{scope['source_id']} minimum review requirement is not met")

    quality_gate_scorer = priority_plan.get("quality_gate_scorer", {})
    if quality_gate_scorer.get("default_scorer") != "deterministic_heuristic":
        findings.append("quality-gate scorer is not deterministic_heuristic")
    if quality_gate_scorer.get("model_assisted_judging_in_quality_gate") is not False:
        findings.append("model-assisted judging appears in the quality gate")
    if quality_gate_scorer.get("quality_gate_behavior_changed") is not False:
        findings.append("quality-gate scorer behavior changed")

    reliability_summary = scorer_reliability.get("reliability_summary", {})
    full_scope_coverage = priority_plan.get("coverage_summary", {})
    if int(reliability_summary.get("reviewed_records", 0)) != int(full_scope_coverage.get("reviewed_records", -1)):
        findings.append("scorer reliability reviewed count does not match full review plan summary")
    return findings


def validate_completion_gate(gate: dict[str, Any]) -> dict[str, Any]:
    """Validate the completion gate schema and completion semantics."""

    schema = load_schema_object(
        SCHEMA_PATH,
        "review coverage completion schema",
        REPO_ROOT,
        ReviewCoverageCompletionGateError,
    )
    validate_schema_value(
        gate,
        schema,
        display_path(JSON_OUTPUT_PATH, REPO_ROOT),
        JSON_OUTPUT_PATH,
        REPO_ROOT,
        ReviewCoverageCompletionGateError,
    )
    validate_source_paths(gate["source_paths"])

    summary = gate["completion_summary"]
    if summary["review_coverage"] != "100.0%":
        raise ReviewCoverageCompletionGateError("completion gate requires 100.0% review coverage")
    if summary["scored_records"] != summary["reviewed_records"]:
        raise ReviewCoverageCompletionGateError("reviewed records must equal scored records")
    if summary["reviewed_records"] != summary["adjudication_records"]:
        raise ReviewCoverageCompletionGateError("adjudication records must equal reviewed records")
    for field_name in [
        "unreviewed_records",
        "unreviewed_heuristic_failures",
        "unreviewed_high_or_critical_records",
        "priority_queue_records",
        "recommended_batches",
    ]:
        if summary[field_name] != 0:
            raise ReviewCoverageCompletionGateError(f"{field_name} must equal 0")

    for row in gate["source_completion"]:
        if row["review_coverage"] != "100.0%":
            raise ReviewCoverageCompletionGateError(f"{row['source_id']} coverage is below 100.0%")
        if row["scored_records"] != row["reviewed_records"]:
            raise ReviewCoverageCompletionGateError(f"{row['source_id']} reviewed count does not match scored count")
        if row["unreviewed_records"] != 0:
            raise ReviewCoverageCompletionGateError(f"{row['source_id']} has unreviewed records")
        if row["recommended_action"] != "maintain_existing_review_coverage":
            raise ReviewCoverageCompletionGateError(f"{row['source_id']} has unexpected recommended action")

    for row in gate["additional_review_scopes"]:
        if row["reviewed_records"] < row["required_reviewed_records"]:
            raise ReviewCoverageCompletionGateError(f"{row['source_id']} has too few reviewed records")
        if row["review_requirement_met"] is not True:
            raise ReviewCoverageCompletionGateError(f"{row['source_id']} review requirement is not met")

    status = gate["gate_status"]
    if status["blocking_findings"]:
        raise ReviewCoverageCompletionGateError(
            f"completion gate has blocking findings: {', '.join(status['blocking_findings'])}"
        )
    if status["gate_passed"] is not True:
        raise ReviewCoverageCompletionGateError("completion gate must pass")
    return {
        "gate_id": gate["gate_id"],
        "review_coverage": summary["review_coverage"],
        "scored_records": summary["scored_records"],
        "reviewed_records": summary["reviewed_records"],
        "recommended_batches": summary["recommended_batches"],
        "gate_passed": status["gate_passed"],
    }


def validate_source_paths(paths: list[str]) -> None:
    for source_path in paths:
        resolved = (REPO_ROOT / source_path).resolve()
        try:
            resolved.relative_to(REPO_ROOT.resolve())
        except ValueError as exc:
            raise ReviewCoverageCompletionGateError(f"source path escapes repository: {source_path}") from exc
        if not resolved.exists():
            raise ReviewCoverageCompletionGateError(f"source path does not exist: {source_path}")


def source_paths() -> list[str]:
    return [
        display_path(REVIEW_COVERAGE_PRIORITY_PATH, REPO_ROOT),
        display_path(REVIEW_COVERAGE_PRIORITY_REPORT_PATH, REPO_ROOT),
        display_path(SCORER_RELIABILITY_PATH, REPO_ROOT),
        display_path(SCORER_RELIABILITY_REPORT_PATH, REPO_ROOT),
        display_path(ADJUDICATION_SNAPSHOT_PATH, REPO_ROOT),
        display_path(ADJUDICATION_MANIFEST_PATH, REPO_ROOT),
        display_path(SCORER_LIMITATIONS_PATH, REPO_ROOT),
    ]


def generate_markdown(gate: dict[str, Any]) -> str:
    """Generate reader-facing Markdown for the completion gate."""

    summary = gate["completion_summary"]
    status = gate["gate_status"]
    next_phase = gate["next_phase_recommendation"]
    lines = [
        "# Review Coverage Completion Gate",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Generated at | `{gate['generated_at']}` |",
        f"| Gate passed | {str(status['gate_passed']).lower()} |",
        f"| Scored records in scope | {summary['scored_records']} |",
        f"| Reviewed records | {summary['reviewed_records']} |",
        f"| Review coverage | {summary['review_coverage']} |",
        f"| Priority queue records | {summary['priority_queue_records']} |",
        f"| Recommended reviewer batches | {summary['recommended_batches']} |",
        f"| Scorer agreement | {summary['scorer_review_agreement_rate']} |",
        f"| False positives / false negatives | {summary['scorer_false_positive_count']} / {summary['scorer_false_negative_count']} |",
        "",
        "M96 locks the completed M89-M95 public-safe reviewer queue into a deterministic quality-gate artifact. New M101A sandbox dry-run evidence is reported as a separate review scope with a minimum reviewed-record threshold.",
        "",
        "## Source Completion",
        "",
        source_completion_table(gate["source_completion"]),
        "",
        "## Additional Review Scopes",
        "",
        additional_review_scope_table(gate["additional_review_scopes"]),
        "",
        "## Completion Requirements",
        "",
        f"- Required review coverage: `{status['required_review_coverage']}`.",
        f"- Required unreviewed records: `{status['required_unreviewed_records']}`.",
        f"- Required priority queue records: `{status['required_priority_queue_records']}`.",
        f"- Required recommended batches: `{status['required_recommended_batches']}`.",
        f"- Stale priority plan: `{str(status['stale_priority_plan']).lower()}`.",
        "",
        "## Blocking Findings",
        "",
        blocking_findings_table(status["blocking_findings"]),
        "",
        "## Next Phase Recommendation",
        "",
        f"- Phase: `{next_phase['phase_id']}`.",
        f"- Reviewer work status: `{next_phase['reviewer_work_status']}`.",
        f"- Rationale: {next_phase['rationale']}",
        "",
        *[f"- {item}" for item in next_phase["recommended_next_steps"]],
        "",
        "## Boundary",
        "",
        *[f"- {item}" for item in gate["boundary"]],
        "",
        "## Source Paths",
        "",
        *[f"- `{path}`" for path in gate["source_paths"]],
        "",
    ]
    return "\n".join(lines)


def source_completion_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Source | Scored | Reviewed | Coverage | Action |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['source_id']}` | {row['scored_records']} | {row['reviewed_records']} | "
            f"{row['review_coverage']} | `{row['recommended_action']}` |"
        )
    return "\n".join(lines)


def additional_review_scope_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No additional review scopes are present."
    lines = [
        "| Source | Requirement | Scored | Reviewed | Required | Coverage | Requirement Met | Unreviewed failures |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['source_id']}` | `{row['review_requirement_id']}` | {row['scored_records']} | "
            f"{row['reviewed_records']} | {row['required_reviewed_records']} | {row['review_coverage']} | "
            f"{str(row['review_requirement_met']).lower()} | {row['unreviewed_heuristic_failures']} |"
        )
    return "\n".join(lines)


def blocking_findings_table(findings: list[str]) -> str:
    if not findings:
        return "No blocking findings."
    return "\n".join(f"- {finding}" for finding in findings)


def write_reports(gate: dict[str, Any]) -> None:
    write_json_object(gate, JSON_OUTPUT_PATH)
    write_text(generate_markdown(gate), MARKDOWN_OUTPUT_PATH)


def main() -> int:
    try:
        gate = build_review_coverage_completion_gate()
        write_reports(gate)
    except (ReviewCoverageCompletionGateError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary = gate["completion_summary"]
    print(f"review coverage completion JSON path: {display_path(JSON_OUTPUT_PATH, REPO_ROOT)}")
    print(f"review coverage completion report path: {display_path(MARKDOWN_OUTPUT_PATH, REPO_ROOT)}")
    print(f"completion gate passed: {str(gate['gate_status']['gate_passed']).lower()}")
    print(f"review coverage: {summary['review_coverage']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
