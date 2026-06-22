"""Generate deterministic Scorer v1 reliability reporting.

This report compares the deterministic heuristic scorer against committed
public-safe adjudications. It is report-only: it does not change scorer behavior,
rewrite traces, call providers, run models, execute agents, inspect private
logs, use networks, or perform external actions.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from adjudication_report import DEFAULT_ADJUDICATION_MANIFEST_PATH, load_adjudication_context_from_manifest
from reporting_utils import display_path, format_list, percent, write_json_object, write_text
from scorer_calibration_summary import CALIBRATION_LABEL_ORDER, calibration_label


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-22T00:00:00Z"

ADJUDICATION_MANIFEST_PATH = REPO_ROOT / "traces/external/adjudication_manifest.json"
ADJUDICATION_SNAPSHOT_PATH = REPO_ROOT / "reports/comparisons/adjudication_regression_snapshot.json"
SCORER_CALIBRATION_PATH = REPO_ROOT / "reports/comparisons/scorer_calibration_summary.json"
SCORER_PROMOTION_DECISION_PATH = REPO_ROOT / "reports/comparisons/scorer_promotion_decision.json"
SCORER_PATH = REPO_ROOT / "src/scorers.py"
SCORER_REVIEW_CONTRACT_PATH = REPO_ROOT / "src/scorer_review_contract.py"
SCORER_LIMITATIONS_PATH = REPO_ROOT / "docs/wiki/concepts/v0_scorer_limitations.md"

JSON_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/scorer_reliability_report.json"
MARKDOWN_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/scorer_reliability_report.md"

CATEGORY_ORDER = [
    "safe_direct_response",
    "approval_gated",
    "refusal_required",
    "uncertainty_handling",
]

SEVERITY_ORDER = [
    "critical",
    "high",
    "medium",
    "low",
    "unknown",
]

RISK_AREA_ORDER = [
    "safe_task",
    "approval_gate",
    "refusal_boundary",
    "uncertainty_handling",
    "unknown",
]

RISK_AREA_BY_POLICY_PREFIX = {
    "ABP-SAFE": "safe_task",
    "ABP-APPROVAL": "approval_gate",
    "ABP-REFUSAL": "refusal_boundary",
    "ABP-UNCERTAINTY": "uncertainty_handling",
}

CATEGORY_RISK_AREAS = {
    "safe_direct_response": "safe_task",
    "approval_gated": "approval_gate",
    "refusal_required": "refusal_boundary",
    "uncertainty_handling": "uncertainty_handling",
}


class ScorerReliabilityReportError(Exception):
    """Scorer reliability report generation error."""


def build_reliability_report() -> dict[str, Any]:
    """Build the deterministic Scorer v1 reliability report."""

    context = load_adjudication_context_from_manifest(ADJUDICATION_MANIFEST_PATH)
    if not context.adjudications:
        raise ScorerReliabilityReportError("cannot build scorer reliability report from zero adjudications")

    records = reliability_records(context)
    overall = calibration_slice(records)
    by_category = grouped_slices(records, "category", CATEGORY_ORDER)
    by_risk_area = grouped_slices(records, "risk_area", RISK_AREA_ORDER)
    by_severity = grouped_slices(records, "severity", SEVERITY_ORDER)
    by_profile = grouped_slices(records, "profile_name")
    by_reviewer = grouped_slices(records, "reviewer_id")
    by_fixture = grouped_slices(records, "fixture_id")
    labels = Counter(record["calibration_label"] for record in records)

    return {
        "report_id": "scorer_v1_reliability_report",
        "generated_at": GENERATED_AT,
        "scope": (
            "Deterministic reliability report for heuristic scorer outcomes compared with committed "
            "public-safe adjudications."
        ),
        "source_paths": source_paths(context),
        "safety": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
            "credentials_required": False,
        },
        "quality_gate_scorer": {
            "default_scorer": "deterministic_heuristic",
            "scorer_path": display_path(SCORER_PATH, REPO_ROOT),
            "quality_gate_behavior_changed": False,
            "accepted_scorer_changes": 0,
            "scored_trace_regeneration_required": False,
            "model_assisted_judging_in_quality_gate": False,
        },
        "reliability_summary": {
            "reviewed_records": len(records),
            "source_trace_count": len(context.source_records_by_path),
            "reviewer_count": len(unique_values(records, "reviewer_id")),
            "scorer_reviewer_agreements": overall["scorer_review_agreements"],
            "scorer_reviewer_disagreements": overall["scorer_review_disagreements"],
            "scorer_review_agreement_rate": overall["agreement_rate"],
            "scorer_false_positive_count": overall["scorer_false_positives"],
            "scorer_false_negative_count": overall["scorer_false_negatives"],
            "ambiguous_review_count": overall["ambiguous_reviews"],
            "failure_precision": overall["failure_detection"]["failure_precision"],
            "failure_recall": overall["failure_detection"]["failure_recall"],
            "failure_specificity": overall["failure_detection"]["failure_specificity"],
        },
        "calibration_labels": {
            "counts": ordered_counts(labels, CALIBRATION_LABEL_ORDER),
            "definitions": {
                "scorer_upheld_failure": "Reviewer upheld a heuristic failure.",
                "scorer_upheld_pass": "Reviewer upheld a heuristic pass.",
                "scorer_false_positive": "Heuristic failed a record that review treats as passing.",
                "scorer_false_negative": "Heuristic passed a record that review treats as failing.",
                "ambiguous_review": "Reviewer marked the scorer outcome as needing discussion.",
            },
        },
        "overall_metrics": overall,
        "calibration_by_category": by_category,
        "calibration_by_risk_area": by_risk_area,
        "calibration_by_severity": by_severity,
        "calibration_by_profile": by_profile,
        "calibration_by_fixture": by_fixture,
        "reviewer_agreement": reviewer_agreement(records, by_reviewer),
        "disagreement_records": [
            compact_record(record)
            for record in records
            if record["calibration_label"] in {"scorer_false_positive", "scorer_false_negative", "ambiguous_review"}
        ],
        "optional_review_contract": {
            "status": "non_gated_contract_only",
            "command": "agent-evals scorer-review-contract",
            "quality_gate_included": False,
            "requires_explicit_operator_opt_in": True,
            "live_provider_calls": False,
            "local_model_calls": False,
            "external_actions": False,
            "credentials_required": False,
            "purpose": (
                "Document the interface for future saved-output scorer review without allowing model-assisted "
                "judging to affect deterministic quality gates."
            ),
        },
        "boundary": [
            "This report reads committed adjudications, scored traces, and scorer decision artifacts only.",
            "The deterministic heuristic scorer remains the default quality-gate scorer.",
            "False positives and false negatives are reliability signals, not automatic scorer overrides.",
            "Reviewer agreement is reported from available reviewer metadata and does not invent panel agreement.",
            "No live provider calls, local model calls, OpenClaw or Hermes execution, credentials, browser/email actions, production actions, or external actions are introduced.",
        ],
    }


def reliability_records(context: Any) -> list[dict[str, Any]]:
    """Return adjudication records enriched for reliability metrics."""

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
        fixture = context.fixture_by_adjudication_id[adjudication["adjudication_id"]]
        label = calibration_label(adjudication)
        source_trace_path = display_path(str(adjudication["source_trace_path"]), REPO_ROOT)
        policy_refs = [str(value) for value in source_record.get("policy_refs", [])]
        risk_areas = risk_areas_for_policy_refs(policy_refs)
        category = str(source_record.get("category", "unknown"))
        records.append(
            {
                "adjudication_id": str(adjudication["adjudication_id"]),
                "fixture_id": str(fixture.fixture_id),
                "source_trace_path": source_trace_path,
                "run_id": str(adjudication["run_id"]),
                "case_id": str(adjudication["case_id"]),
                "profile_name": str(adjudication["profile_name"]),
                "reviewer_id": str(adjudication.get("reviewer_id", "unknown")),
                "reviewed_at": str(adjudication.get("reviewed_at", "")),
                "category": category,
                "risk_area": primary_risk_area(category, risk_areas),
                "risk_areas": risk_areas,
                "severity": str(source_record.get("severity", "unknown")),
                "policy_refs": policy_refs,
                "reviewer_decision": str(adjudication["reviewer_decision"]),
                "original_passed": bool(adjudication["original_passed"]),
                "adjudicated_passed": bool(adjudication["adjudicated_passed"]),
                "original_failure_modes": [str(value) for value in adjudication["original_failure_modes"]],
                "adjudicated_failure_modes": [
                    str(value)
                    for value in adjudication["adjudicated_failure_modes"]
                ],
                "calibration_label": label,
                "scorer_review_same_result": bool(adjudication["original_passed"])
                is bool(adjudication["adjudicated_passed"]),
                "scorer_review_same_failure_modes": list(adjudication["original_failure_modes"])
                == list(adjudication["adjudicated_failure_modes"]),
                "rationale": str(adjudication["rationale"]),
            }
        )
    return records


def primary_risk_area(category: str, policy_risk_areas: list[str]) -> str:
    """Return the primary risk area for grouping."""

    if category in CATEGORY_RISK_AREAS:
        return CATEGORY_RISK_AREAS[category]
    return policy_risk_areas[0] if policy_risk_areas else "unknown"


def risk_areas_for_policy_refs(policy_refs: list[str]) -> list[str]:
    """Map policy references to stable risk-area labels."""

    observed = []
    for policy_ref in policy_refs:
        for prefix, risk_area in RISK_AREA_BY_POLICY_PREFIX.items():
            if policy_ref.startswith(prefix) and risk_area not in observed:
                observed.append(risk_area)
    if not observed:
        return ["unknown"]

    ordered = [risk_area for risk_area in RISK_AREA_ORDER if risk_area in observed]
    ordered.extend(sorted(set(observed) - set(ordered)))
    return ordered


def calibration_slice(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Return reliability metrics for one slice of records."""

    label_counts = Counter(record["calibration_label"] for record in records)
    metric_records = [record for record in records if record["calibration_label"] != "ambiguous_review"]
    true_positive = label_counts.get("scorer_upheld_failure", 0)
    true_negative = label_counts.get("scorer_upheld_pass", 0)
    false_positive = label_counts.get("scorer_false_positive", 0)
    false_negative = label_counts.get("scorer_false_negative", 0)
    agreements = true_positive + true_negative
    disagreements = false_positive + false_negative
    metric_count = len(metric_records)

    return {
        "reviewed_records": len(records),
        "metric_records": metric_count,
        "scorer_review_agreements": agreements,
        "scorer_review_disagreements": disagreements,
        "ambiguous_reviews": label_counts.get("ambiguous_review", 0),
        "scorer_false_positives": false_positive,
        "scorer_false_negatives": false_negative,
        "original_scorer_failures": true_positive + false_positive,
        "adjudicated_review_failures": true_positive + false_negative,
        "agreement_rate": percent(agreements, metric_count),
        "disagreement_rate": percent(disagreements, metric_count),
        "false_positive_rate": percent(false_positive, metric_count),
        "false_negative_rate": percent(false_negative, metric_count),
        "calibration_label_counts": ordered_counts(label_counts, CALIBRATION_LABEL_ORDER),
        "failure_detection": {
            "true_positive_review_failure": true_positive,
            "false_positive_review_pass": false_positive,
            "true_negative_review_pass": true_negative,
            "false_negative_review_failure": false_negative,
            "failure_precision": percent(true_positive, true_positive + false_positive),
            "failure_recall": percent(true_positive, true_positive + false_negative),
            "failure_specificity": percent(true_negative, true_negative + false_positive),
            "failure_accuracy": percent(true_positive + true_negative, metric_count),
        },
    }


def grouped_slices(
    records: list[dict[str, Any]],
    key: str,
    preferred_order: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Return calibration slices grouped by one field."""

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get(key, "unknown"))].append(record)

    order = [value for value in (preferred_order or []) if value in grouped]
    order.extend(sorted(set(grouped) - set(order)))
    return {group_key: calibration_slice(grouped[group_key]) for group_key in order}


def reviewer_agreement(
    records: list[dict[str, Any]],
    by_reviewer: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Summarize scorer-review and inter-reviewer agreement evidence."""

    reviewers = unique_values(records, "reviewer_id")
    targets: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    for record in records:
        targets[
            (
                str(record["source_trace_path"]),
                str(record["run_id"]),
                str(record["case_id"]),
                str(record["profile_name"]),
            )
        ].add(str(record["reviewer_id"]))

    overlapping_targets = sum(1 for target_reviewers in targets.values() if len(target_reviewers) > 1)
    if overlapping_targets == 0:
        inter_reviewer_status = "not_available_no_overlapping_review_targets"
        inter_reviewer_note = (
            "Committed adjudications currently provide one reviewer decision per target, so panel agreement "
            "cannot be estimated from these fixtures."
        )
    else:
        inter_reviewer_status = "available"
        inter_reviewer_note = "Overlapping reviewer targets are available for separate panel-agreement calculation."

    overall = calibration_slice(records)
    return {
        "reviewer_count": len(reviewers),
        "reviewer_ids": reviewers,
        "reviewed_records": len(records),
        "review_targets": len(targets),
        "single_reviewer_targets": sum(1 for target_reviewers in targets.values() if len(target_reviewers) == 1),
        "overlapping_review_targets": overlapping_targets,
        "scorer_reviewer_agreement_rate": overall["agreement_rate"],
        "scorer_reviewer_disagreement_rate": overall["disagreement_rate"],
        "by_reviewer": by_reviewer,
        "inter_reviewer_agreement": {
            "status": inter_reviewer_status,
            "agreement_rate": None,
            "overlapping_review_targets": overlapping_targets,
            "note": inter_reviewer_note,
        },
    }


def compact_record(record: dict[str, Any]) -> dict[str, Any]:
    """Return a compact disagreement record for the JSON snapshot."""

    return {
        "adjudication_id": record["adjudication_id"],
        "fixture_id": record["fixture_id"],
        "source_trace_path": record["source_trace_path"],
        "case_id": record["case_id"],
        "profile_name": record["profile_name"],
        "category": record["category"],
        "risk_area": record["risk_area"],
        "severity": record["severity"],
        "reviewer_id": record["reviewer_id"],
        "reviewer_decision": record["reviewer_decision"],
        "calibration_label": record["calibration_label"],
        "original_failure_modes": record["original_failure_modes"],
        "adjudicated_failure_modes": record["adjudicated_failure_modes"],
    }


def ordered_counts(counter: Counter[str], order: list[str]) -> dict[str, int]:
    observed = set(counter)
    result = {key: int(counter.get(key, 0)) for key in order}
    for key in sorted(observed.difference(order)):
        result[key] = int(counter[key])
    return result


def unique_values(records: list[dict[str, Any]], key: str) -> list[str]:
    values = []
    seen = set()
    for record in records:
        value = str(record.get(key, "unknown"))
        if value not in seen:
            values.append(value)
            seen.add(value)
    return sorted(values)


def source_paths(context: Any) -> list[str]:
    paths = [
        DEFAULT_ADJUDICATION_MANIFEST_PATH,
        ADJUDICATION_SNAPSHOT_PATH,
        SCORER_CALIBRATION_PATH,
        SCORER_PROMOTION_DECISION_PATH,
        SCORER_PATH,
        SCORER_REVIEW_CONTRACT_PATH,
        SCORER_LIMITATIONS_PATH,
    ]
    for fixture in context.fixtures:
        paths.append(fixture.path)
    for source_path in sorted(context.source_records_by_path):
        paths.append(REPO_ROOT / source_path)
    return [display_path(path, REPO_ROOT) for path in paths]


def generate_markdown(report: dict[str, Any]) -> str:
    """Generate reader-facing Markdown for the reliability report."""

    summary = report["reliability_summary"]
    overall = report["overall_metrics"]
    reviewer = report["reviewer_agreement"]
    lines = [
        "# Scorer Reliability Report",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | ---: |",
        f"| Generated at | `{report['generated_at']}` |",
        f"| Reviewed records | {summary['reviewed_records']} |",
        f"| Source traces reviewed | {summary['source_trace_count']} |",
        f"| Reviewers | {summary['reviewer_count']} |",
        f"| Scorer/reviewer agreement rate | {summary['scorer_review_agreement_rate']} |",
        f"| Scorer false positives | {summary['scorer_false_positive_count']} |",
        f"| Scorer false negatives | {summary['scorer_false_negative_count']} |",
        f"| Ambiguous reviews | {summary['ambiguous_review_count']} |",
        f"| Failure precision | {summary['failure_precision']} |",
        f"| Failure recall | {summary['failure_recall']} |",
        "",
        "This report is advisory. The deterministic heuristic scorer remains the default quality-gate scorer.",
        "",
        "## Overall Metrics",
        "",
        _overall_metric_table(overall),
        "",
        "## Calibration Labels",
        "",
        _counts_table(report["calibration_labels"]["counts"], "Calibration Label"),
        "",
        "## Calibration By Risk Area",
        "",
        _slice_table(report["calibration_by_risk_area"], "Risk Area"),
        "",
        "## Calibration By Category",
        "",
        _slice_table(report["calibration_by_category"], "Category"),
        "",
        "## Reviewer Agreement",
        "",
        _reviewer_table(reviewer),
        "",
        "## Disagreement Records",
        "",
        _disagreement_table(report["disagreement_records"]),
        "",
        "## Optional Review Contract",
        "",
        _optional_contract(report["optional_review_contract"]),
        "",
        "## Boundary",
        "",
        "\n".join(f"- {item}" for item in report["boundary"]),
        "",
        "## Sources",
        "",
        "\n".join(f"- `{path}`" for path in report["source_paths"]),
        "",
    ]
    return "\n".join(lines)


def _overall_metric_table(metrics: dict[str, Any]) -> str:
    detection = metrics["failure_detection"]
    rows = [
        ("Metric records", metrics["metric_records"]),
        ("Scorer/reviewer agreements", metrics["scorer_review_agreements"]),
        ("Scorer/reviewer disagreements", metrics["scorer_review_disagreements"]),
        ("Agreement rate", metrics["agreement_rate"]),
        ("False positive rate", metrics["false_positive_rate"]),
        ("False negative rate", metrics["false_negative_rate"]),
        ("Failure precision", detection["failure_precision"]),
        ("Failure recall", detection["failure_recall"]),
        ("Failure specificity", detection["failure_specificity"]),
        ("Failure accuracy", detection["failure_accuracy"]),
    ]
    lines = [
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for label, value in rows:
        lines.append(f"| {label} | {value} |")
    return "\n".join(lines)


def _counts_table(counts: dict[str, int], label: str) -> str:
    lines = [
        f"| {label} | Count |",
        "| --- | ---: |",
    ]
    for key, value in counts.items():
        lines.append(f"| `{key}` | {value} |")
    return "\n".join(lines)


def _slice_table(slices: dict[str, dict[str, Any]], label: str) -> str:
    lines = [
        f"| {label} | Records | Agreement | False Positives | False Negatives | Precision | Recall |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for key, metrics in slices.items():
        detection = metrics["failure_detection"]
        lines.append(
            f"| `{key}` | {metrics['reviewed_records']} | {metrics['agreement_rate']} | "
            f"{metrics['scorer_false_positives']} | {metrics['scorer_false_negatives']} | "
            f"{detection['failure_precision']} | {detection['failure_recall']} |"
        )
    return "\n".join(lines)


def _reviewer_table(reviewer: dict[str, Any]) -> str:
    lines = [
        "| Field | Value |",
        "| --- | --- |",
        f"| Reviewer IDs | {format_list(reviewer['reviewer_ids'])} |",
        f"| Review targets | {reviewer['review_targets']} |",
        f"| Overlapping review targets | {reviewer['overlapping_review_targets']} |",
        f"| Scorer/reviewer agreement rate | {reviewer['scorer_reviewer_agreement_rate']} |",
        f"| Inter-reviewer agreement status | `{reviewer['inter_reviewer_agreement']['status']}` |",
        f"| Inter-reviewer agreement note | {reviewer['inter_reviewer_agreement']['note']} |",
    ]
    return "\n".join(lines)


def _disagreement_table(records: list[dict[str, Any]]) -> str:
    if not records:
        return "No false-positive, false-negative, or ambiguous review records were found."
    lines = [
        "| Adjudication | Case | Profile | Risk Area | Label | Original Modes | Adjudicated Modes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in records:
        lines.append(
            f"| `{record['adjudication_id']}` | `{record['case_id']}` | `{record['profile_name']}` | "
            f"`{record['risk_area']}` | `{record['calibration_label']}` | "
            f"{format_list(record['original_failure_modes'])} | "
            f"{format_list(record['adjudicated_failure_modes'])} |"
        )
    return "\n".join(lines)


def _optional_contract(contract: dict[str, Any]) -> str:
    return "\n".join(
        [
            "| Field | Value |",
            "| --- | --- |",
            f"| Status | `{contract['status']}` |",
            f"| Command | `{contract['command']}` |",
            f"| Quality gate included | {str(contract['quality_gate_included']).lower()} |",
            f"| Requires explicit opt-in | {str(contract['requires_explicit_operator_opt_in']).lower()} |",
            f"| Live provider calls | {str(contract['live_provider_calls']).lower()} |",
            f"| Local model calls | {str(contract['local_model_calls']).lower()} |",
            f"| Credentials required | {str(contract['credentials_required']).lower()} |",
        ]
    )


def main() -> int:
    try:
        report = build_reliability_report()
        write_json_object(report, JSON_OUTPUT_PATH)
        write_text(generate_markdown(report), MARKDOWN_OUTPUT_PATH)
    except (OSError, ValueError, ScorerReliabilityReportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary = report["reliability_summary"]
    print(f"scorer reliability JSON path: {display_path(JSON_OUTPUT_PATH, REPO_ROOT)}")
    print(f"scorer reliability report path: {display_path(MARKDOWN_OUTPUT_PATH, REPO_ROOT)}")
    print(f"reviewed records: {summary['reviewed_records']}")
    print(f"scorer/reviewer agreement rate: {summary['scorer_review_agreement_rate']}")
    print(f"scorer false positives: {summary['scorer_false_positive_count']}")
    print(f"scorer false negatives: {summary['scorer_false_negative_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
