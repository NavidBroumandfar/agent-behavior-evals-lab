"""Generate scorer calibration summaries from committed adjudications.

This M42 report compares deterministic v0 scorer outcomes against public-safe
human adjudication fixtures. It does not change scorer behavior, rescore traces,
call providers, run models, execute agents, inspect private logs, use networks,
or perform external actions.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from adjudication_report import DEFAULT_ADJUDICATION_MANIFEST_PATH, load_adjudication_context_from_manifest
from reporting_utils import display_path, format_list, percent, write_json_object, write_text


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-20T00:00:00Z"

ADJUDICATION_MANIFEST_PATH = REPO_ROOT / "traces/external/adjudication_manifest.json"
ADJUDICATION_SNAPSHOT_PATH = REPO_ROOT / "reports/comparisons/adjudication_regression_snapshot.json"
SCORER_PATH = REPO_ROOT / "src/scorers.py"
SCORER_LIMITATIONS_PATH = REPO_ROOT / "docs/wiki/concepts/v0_scorer_limitations.md"

JSON_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/scorer_calibration_summary.json"
MARKDOWN_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/scorer_calibration_summary.md"

CALIBRATION_LABEL_ORDER = [
    "scorer_upheld_failure",
    "scorer_upheld_pass",
    "scorer_false_positive",
    "scorer_false_negative",
    "ambiguous_review",
]


class ScorerCalibrationSummaryError(Exception):
    """Scorer calibration summary generation error."""


def build_calibration_summary() -> dict[str, Any]:
    """Build the deterministic M42 scorer calibration summary."""

    context = load_adjudication_context_from_manifest(ADJUDICATION_MANIFEST_PATH)
    if not context.adjudications:
        raise ScorerCalibrationSummaryError("cannot build calibration summary from zero adjudications")

    reviewed_records = reviewed_calibration_records(context)
    label_counts = Counter(record["calibration_label"] for record in reviewed_records)
    decision_counts = Counter(record["reviewer_decision"] for record in reviewed_records)
    source_trace_counts = Counter(record["source_trace_path"] for record in reviewed_records)
    category_counts = Counter(record["category"] for record in reviewed_records)
    profile_counts = Counter(record["profile_name"] for record in reviewed_records)

    false_positives = [record for record in reviewed_records if record["calibration_label"] == "scorer_false_positive"]
    false_negatives = [record for record in reviewed_records if record["calibration_label"] == "scorer_false_negative"]
    ambiguous = [record for record in reviewed_records if record["calibration_label"] == "ambiguous_review"]

    return {
        "summary_id": "m42_scorer_calibration_summary",
        "generated_at": GENERATED_AT,
        "scope": "Advisory calibration summary comparing deterministic scorer outcomes against committed public-safe adjudications.",
        "source_paths": [
            display_path(ADJUDICATION_MANIFEST_PATH, REPO_ROOT),
            display_path(ADJUDICATION_SNAPSHOT_PATH, REPO_ROOT),
            display_path(SCORER_PATH, REPO_ROOT),
            display_path(SCORER_LIMITATIONS_PATH, REPO_ROOT),
        ],
        "safety": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
            "credentials_required": False,
        },
        "calibration_scope": {
            "adjudication_records": len(reviewed_records),
            "source_trace_count": len(source_trace_counts),
            "source_trace_records": sum(len(records) for records in context.source_records_by_path.values()),
            "reviewed_record_coverage": {
                source_path: {
                    "reviewed_records": source_trace_counts[source_path],
                    "source_records": len(context.source_records_by_path[source_path]),
                    "review_coverage": percent(
                        source_trace_counts[source_path],
                        len(context.source_records_by_path[source_path]),
                    ),
                }
                for source_path in sorted(context.source_records_by_path)
            },
            "reviewed_by_category": sorted_count_dict(category_counts),
            "reviewed_by_profile": sorted_count_dict(profile_counts),
        },
        "calibration_labels": {
            "counts": ordered_counts(label_counts, CALIBRATION_LABEL_ORDER),
            "definitions": calibration_label_definitions(),
        },
        "reviewer_decisions": ordered_counts(
            decision_counts,
            ["uphold_score", "override_pass", "override_fail", "needs_discussion"],
        ),
        "result_changes": {
            "changed_result_count": len(false_positives) + len(false_negatives),
            "scorer_false_positive_count": len(false_positives),
            "scorer_false_negative_count": len(false_negatives),
            "ambiguous_review_count": len(ambiguous),
        },
        "records": reviewed_records,
        "suggested_refinements": suggested_refinements(false_positives, false_negatives, ambiguous),
        "accepted_scorer_changes": [],
        "regression_check": {
            "status": "no_scorer_changes_accepted",
            "accepted_scorer_changes": 0,
            "scorer_changed": False,
            "required_regression_tests": [],
            "note": "M42 records advisory calibration findings only; deterministic scorer code is unchanged.",
        },
        "boundary": [
            "Calibration uses committed public-safe adjudication fixtures only.",
            "Reviewer decisions remain advisory unless separately promoted through deterministic artifacts.",
            "No model-assisted judging or gated LLM review is introduced.",
            "No scorer changes are accepted in this phase.",
        ],
    }


def reviewed_calibration_records(context: Any) -> list[dict[str, Any]]:
    """Return row-level calibration records with labels."""

    records = []
    for adjudication in sorted(
        context.adjudications,
        key=lambda record: (
            str(record["source_trace_path"]),
            str(record["case_id"]),
            str(record["profile_name"]),
            str(record["adjudication_id"]),
        ),
    ):
        source_record = context.source_record_by_adjudication_id[adjudication["adjudication_id"]]
        label = calibration_label(adjudication)
        records.append(
            {
                "adjudication_id": str(adjudication["adjudication_id"]),
                "source_trace_path": display_path(str(adjudication["source_trace_path"]), REPO_ROOT),
                "run_id": str(adjudication["run_id"]),
                "case_id": str(adjudication["case_id"]),
                "profile_name": str(adjudication["profile_name"]),
                "category": str(source_record.get("category", "unknown")),
                "severity": str(source_record.get("severity", "unknown")),
                "reviewer_decision": str(adjudication["reviewer_decision"]),
                "original_passed": bool(adjudication["original_passed"]),
                "adjudicated_passed": bool(adjudication["adjudicated_passed"]),
                "original_failure_modes": list(adjudication["original_failure_modes"]),
                "adjudicated_failure_modes": list(adjudication["adjudicated_failure_modes"]),
                "calibration_label": label,
                "calibration_summary": calibration_summary(label),
                "rationale": str(adjudication["rationale"]),
            }
        )
    return records


def calibration_label(adjudication: dict[str, Any]) -> str:
    """Classify scorer-vs-review outcome."""

    if adjudication["reviewer_decision"] == "needs_discussion":
        return "ambiguous_review"
    if adjudication["original_passed"] is False and adjudication["adjudicated_passed"] is True:
        return "scorer_false_positive"
    if adjudication["original_passed"] is True and adjudication["adjudicated_passed"] is False:
        return "scorer_false_negative"
    if adjudication["original_passed"] is False and adjudication["adjudicated_passed"] is False:
        return "scorer_upheld_failure"
    if adjudication["original_passed"] is True and adjudication["adjudicated_passed"] is True:
        return "scorer_upheld_pass"
    raise ScorerCalibrationSummaryError(f"unsupported adjudication outcome: {adjudication['adjudication_id']}")


def calibration_summary(label: str) -> str:
    summaries = {
        "scorer_upheld_failure": "Reviewer upheld a heuristic failure.",
        "scorer_upheld_pass": "Reviewer upheld a heuristic pass.",
        "scorer_false_positive": "Heuristic failed a record that review treats as passing.",
        "scorer_false_negative": "Heuristic passed a record that review treats as failing.",
        "ambiguous_review": "Reviewer marked the scorer outcome as needing discussion.",
    }
    return summaries[label]


def calibration_label_definitions() -> list[dict[str, str]]:
    return [
        {"label": label, "definition": calibration_summary(label)}
        for label in CALIBRATION_LABEL_ORDER
    ]


def suggested_refinements(
    false_positives: list[dict[str, Any]],
    false_negatives: list[dict[str, Any]],
    ambiguous: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return advisory scorer or rubric refinements from adjudication evidence."""

    suggestions: list[dict[str, Any]] = []
    if false_positives:
        suggestions.append(
            {
                "suggestion_id": "review_safe_clarification_vs_over_refusal",
                "status": "advisory_not_accepted",
                "target": "rubric_or_scorer",
                "summary": "Clarify when a low-friction preference question in a safe task should count as over-refusal.",
                "source_adjudication_ids": [record["adjudication_id"] for record in false_positives],
                "deterministic_path": "Add focused scorer tests before changing over_refusal handling.",
            }
        )
    if false_negatives:
        suggestions.append(
            {
                "suggestion_id": "strengthen_approval_risk_disclosure_review",
                "status": "advisory_not_accepted",
                "target": "rubric_or_scorer",
                "summary": "Require clearer approval-gate risk, scope, target, and reversibility disclosure before treating confirmation requests as sufficient.",
                "source_adjudication_ids": [record["adjudication_id"] for record in false_negatives],
                "deterministic_path": "Add targeted approval-gated edge cases before accepting scorer changes.",
            }
        )
    if ambiguous:
        suggestions.append(
            {
                "suggestion_id": "resolve_needs_discussion_queue",
                "status": "advisory_not_accepted",
                "target": "review_process",
                "summary": "Resolve needs_discussion records before using them as scorer-change evidence.",
                "source_adjudication_ids": [record["adjudication_id"] for record in ambiguous],
                "deterministic_path": "Promote only resolved public-safe adjudications through the adjudication manifest.",
            }
        )
    return suggestions


def ordered_counts(counter: Counter[str], order: list[str]) -> dict[str, int]:
    observed = set(counter)
    result = {key: int(counter.get(key, 0)) for key in order}
    for key in sorted(observed.difference(order)):
        result[key] = int(counter[key])
    return result


def sorted_count_dict(counter: Counter[str]) -> dict[str, int]:
    return {key: int(counter[key]) for key in sorted(counter)}


def generate_markdown(summary: dict[str, Any]) -> str:
    """Generate reader-facing scorer calibration Markdown."""

    scope = summary["calibration_scope"]
    changes = summary["result_changes"]
    lines = [
        "# Scorer Calibration Summary",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | ---: |",
        f"| Adjudication records | {scope['adjudication_records']} |",
        f"| Source traces reviewed | {scope['source_trace_count']} |",
        f"| Changed results | {changes['changed_result_count']} |",
        f"| Scorer false positives | {changes['scorer_false_positive_count']} |",
        f"| Scorer false negatives | {changes['scorer_false_negative_count']} |",
        f"| Ambiguous reviews | {changes['ambiguous_review_count']} |",
        "",
        "This calibration summary is advisory. It compares committed public-safe adjudications with deterministic scorer outcomes and does not change scored traces or scorer code.",
        "",
        "## Calibration Labels",
        "",
        _counts_table(summary["calibration_labels"]["counts"], "Calibration Label"),
        "",
        "## Reviewer Decisions",
        "",
        _counts_table(summary["reviewer_decisions"], "Reviewer Decision"),
        "",
        "## Coverage",
        "",
        _coverage_table(scope["reviewed_record_coverage"]),
        "",
        "## Reviewed Records",
        "",
        _records_table(summary["records"]),
        "",
        "## Suggested Refinements",
        "",
        _suggestions_table(summary["suggested_refinements"]),
        "",
        "## Accepted Scorer Changes",
        "",
        "No scorer changes are accepted in M42. Suggested refinements remain advisory until a future deterministic change includes focused tests and explicit regression coverage.",
        "",
        "## Boundary",
        "",
        "\n".join(f"- {item}" for item in summary["boundary"]),
        "",
        "## Sources",
        "",
        "\n".join(f"- `{path}`" for path in summary["source_paths"]),
        "",
    ]
    return "\n".join(lines)


def _counts_table(counts: dict[str, int], label: str) -> str:
    lines = [
        f"| {label} | Count |",
        "| --- | ---: |",
    ]
    for key, value in counts.items():
        lines.append(f"| `{key}` | {value} |")
    return "\n".join(lines)


def _coverage_table(coverage: dict[str, dict[str, Any]]) -> str:
    lines = [
        "| Source Trace | Reviewed | Source Records | Coverage |",
        "| --- | ---: | ---: | ---: |",
    ]
    for source_path, item in coverage.items():
        lines.append(
            f"| `{source_path}` | {item['reviewed_records']} | {item['source_records']} | {item['review_coverage']} |"
        )
    return "\n".join(lines)


def _records_table(records: list[dict[str, Any]]) -> str:
    lines = [
        "| Case | Profile | Category | Decision | Label | Original Modes | Adjudicated Modes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in records:
        lines.append(
            f"| `{record['case_id']}` | `{record['profile_name']}` | `{record['category']}` | "
            f"`{record['reviewer_decision']}` | `{record['calibration_label']}` | "
            f"{format_list(record['original_failure_modes'])} | {format_list(record['adjudicated_failure_modes'])} |"
        )
    return "\n".join(lines)


def _suggestions_table(suggestions: list[dict[str, Any]]) -> str:
    if not suggestions:
        return "No advisory refinements were generated."
    lines = [
        "| Suggestion | Status | Target | Source Adjudications | Summary |",
        "| --- | --- | --- | --- | --- |",
    ]
    for suggestion in suggestions:
        lines.append(
            f"| `{suggestion['suggestion_id']}` | `{suggestion['status']}` | `{suggestion['target']}` | "
            f"{format_list(suggestion['source_adjudication_ids'])} | {suggestion['summary']} |"
        )
    return "\n".join(lines)


def main() -> int:
    try:
        summary = build_calibration_summary()
        write_json_object(summary, JSON_OUTPUT_PATH)
        write_text(generate_markdown(summary), MARKDOWN_OUTPUT_PATH)
    except (OSError, ValueError, ScorerCalibrationSummaryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    changes = summary["result_changes"]
    print(f"scorer calibration JSON path: {display_path(JSON_OUTPUT_PATH, REPO_ROOT)}")
    print(f"scorer calibration report path: {display_path(MARKDOWN_OUTPUT_PATH, REPO_ROOT)}")
    print(f"adjudication records calibrated: {summary['calibration_scope']['adjudication_records']}")
    print(f"scorer false positives: {changes['scorer_false_positive_count']}")
    print(f"scorer false negatives: {changes['scorer_false_negative_count']}")
    print(f"ambiguous reviews: {changes['ambiguous_review_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
