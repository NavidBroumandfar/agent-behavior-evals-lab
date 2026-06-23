"""Generate dashboard-ready reporting summaries from committed local artifacts.

This M38 report product layer reads already-scored traces, manifests, and
snapshots. It does not collect outputs, rescore records, call providers, run
models, execute agents, inspect private logs, use networks, or perform external
actions.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from reporting_utils import load_json_object, load_jsonl_records, percent, write_json_object, write_text


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-21T00:00:00Z"

BASELINE_TRACE_PATH = REPO_ROOT / "traces/scored/baseline_mock_run.jsonl"
FIXTURE_MANIFEST_PATH = REPO_ROOT / "traces/external/fixture_manifest.json"
ADJUDICATION_SNAPSHOT_PATH = REPO_ROOT / "reports/comparisons/adjudication_regression_snapshot.json"
HARNESS_BRIDGE_PLAN_PATH = REPO_ROOT / "traces/external/harness_bridge_plan.example.json"
LOCAL_BENCHMARK_REPORT_PATH = REPO_ROOT / "reports/comparisons/local_open_weight_benchmark_v1.json"
SCORER_RELIABILITY_REPORT_PATH = REPO_ROOT / "reports/comparisons/scorer_reliability_report.json"

JSON_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/reporting_product_summary.json"
MARKDOWN_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/reporting_product_summary.md"

CATEGORY_ORDER = [
    "safe_direct_response",
    "approval_gated",
    "refusal_required",
    "uncertainty_handling",
]
PROFILE_ORDER = [
    "generic_assistant",
    "openclaw_reference_agent",
    "strict_approval_agent",
]


class ReportingProductSummaryError(Exception):
    """Reporting product summary generation error."""


def build_summary() -> dict[str, Any]:
    """Build the deterministic dashboard-ready summary object."""

    baseline_records = load_required_jsonl(BASELINE_TRACE_PATH)
    fixture_manifest = load_json_object(FIXTURE_MANIFEST_PATH)
    adjudication_snapshot = load_json_object(ADJUDICATION_SNAPSHOT_PATH)
    harness_plan = load_json_object(HARNESS_BRIDGE_PLAN_PATH)

    fixture_summaries = fixture_group_summaries(fixture_manifest)
    baseline_summary = trace_summary(baseline_records)
    adjudication_summary = summarize_adjudication(adjudication_snapshot)
    harness_summary = summarize_harness_plan(harness_plan)
    local_benchmark_report = load_optional_json_object(LOCAL_BENCHMARK_REPORT_PATH)
    scorer_reliability_report = load_optional_json_object(SCORER_RELIABILITY_REPORT_PATH)
    evidence_coverage = evidence_class_coverage(
        fixture_summaries,
        adjudication_summary,
        local_benchmark_report,
        scorer_reliability_report,
    )
    external_summary = external_fixture_summary(fixture_summaries)

    return {
        "summary_id": "m38_reporting_product_summary",
        "generated_at": GENERATED_AT,
        "scope": "Dashboard-ready deterministic summary of committed local quality-gate artifacts.",
        "source_paths": [
            display_path(BASELINE_TRACE_PATH),
            display_path(FIXTURE_MANIFEST_PATH),
            display_path(ADJUDICATION_SNAPSHOT_PATH),
            display_path(HARNESS_BRIDGE_PLAN_PATH),
            display_path(LOCAL_BENCHMARK_REPORT_PATH),
            display_path(SCORER_RELIABILITY_REPORT_PATH),
        ],
        "safety": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
            "credentials_required": False,
        },
        "baseline": baseline_summary,
        "external_fixtures": external_summary,
        "adjudication": adjudication_summary,
        "harness_bridge": harness_summary,
        "evidence_class_coverage": evidence_coverage,
        "product_kpis": product_kpis(
            baseline_summary,
            external_summary,
            adjudication_summary,
            harness_summary,
            evidence_coverage,
        ),
        "release_view": release_view(baseline_summary, adjudication_summary, harness_summary, evidence_coverage),
        "engineering_view": engineering_view(baseline_summary, fixture_summaries, adjudication_summary),
    }


def trace_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize one scored trace set."""

    if not records:
        raise ReportingProductSummaryError("baseline trace must not be empty")

    passed = count_passed(records)
    failed = len(records) - passed
    return {
        "run_ids": unique_values(records, "run_id"),
        "timestamps": unique_values(records, "timestamp"),
        "total_records": len(records),
        "passed": passed,
        "failed": failed,
        "pass_rate": percent(passed, len(records)),
        "by_profile": group_summary(records, "profile_name", PROFILE_ORDER),
        "by_category": group_summary(records, "category", CATEGORY_ORDER),
        "failure_modes": dict(sorted(failure_mode_counts(records).items())),
    }


def fixture_group_summaries(fixture_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Summarize manifest-backed external fixture scored traces."""

    summaries = []
    fixtures = fixture_manifest.get("fixtures", [])
    if not isinstance(fixtures, list) or not fixtures:
        raise ReportingProductSummaryError("fixture manifest must contain fixtures")

    for fixture in fixtures:
        if not isinstance(fixture, dict):
            raise ReportingProductSummaryError("fixture manifest entries must be objects")
        scored_path = REPO_ROOT / str(fixture["scored_trace_path"])
        records = load_required_jsonl(scored_path)
        passed = count_passed(records)
        total = len(records)
        summaries.append(
            {
                "fixture_id": str(fixture["fixture_id"]),
                "source_type": str(fixture["source_type"]),
                "source_path": str(fixture["source_path"]),
                "scored_trace_path": str(fixture["scored_trace_path"]),
                "quality_gate_included": bool(fixture["quality_gate_included"]),
                "scored_records": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate": percent(passed, total),
                "data_classification": str(fixture["data_classification"]),
                "provenance_class": str(fixture["provenance_class"]),
            }
        )
    return summaries


def external_fixture_summary(fixture_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    """Return aggregate external-fixture counts with a pass rate."""

    total_records = sum(item["scored_records"] for item in fixture_summaries)
    failed_records = sum(item["failed"] for item in fixture_summaries)
    passed_records = total_records - failed_records
    sandbox_groups = [item for item in fixture_summaries if item["source_type"] == "sandbox_agent_run"]
    return {
        "fixture_groups": len(fixture_summaries),
        "total_scored_records": total_records,
        "passed_records": passed_records,
        "failed_records": failed_records,
        "pass_rate": percent(passed_records, total_records),
        "sandbox_scenario_count": sum(item["scored_records"] for item in sandbox_groups),
        "sandbox_pass_rate": percent(
            sum(item["passed"] for item in sandbox_groups),
            sum(item["scored_records"] for item in sandbox_groups),
        ),
        "groups": fixture_summaries,
    }


def evidence_class_coverage(
    fixture_summaries: list[dict[str, Any]],
    adjudication_summary: dict[str, Any],
    local_benchmark_report: dict[str, Any],
    scorer_reliability_report: dict[str, Any],
) -> dict[str, Any]:
    """Summarize buyer-facing evidence classes without changing scoring."""

    sandbox_groups = [item for item in fixture_summaries if item["source_type"] == "sandbox_agent_run"]
    real_format_groups = [
        item
        for item in fixture_summaries
        if item["source_type"]
        in {
            "saved_transcript_replay",
            "openclaw_saved_transcript_pilot",
            "public_safe_transcript_expansion",
            "hermes_long_running_agent",
            "production_policy_scenario",
            "normalized_adapter_output",
        }
    ]
    synthetic_fixture_groups = [
        item
        for item in fixture_summaries
        if item["source_type"] != "sandbox_agent_run"
    ]
    rankings = local_benchmark_report.get("rankings", []) if isinstance(local_benchmark_report, dict) else []
    reviewed_local_records = sum(
        int(item.get("review_counts", {}).get("records_reviewed", 0))
        for item in rankings
        if isinstance(item, dict)
    )
    reliability_summary = scorer_reliability_report.get("reliability_summary", {})
    approval_gate = scorer_reliability_report.get("calibration_by_risk_area", {}).get("approval_gate", {})
    sandbox_review_coverage = adjudication_summary["source_trace_coverage"].get(
        "traces/scored/sandbox_agent_benchmark_eval.jsonl",
        {},
    )
    return {
        "summary": {
            "fixture_count": sum(item["scored_records"] for item in synthetic_fixture_groups),
            "sandbox_scenario_count": sum(item["scored_records"] for item in sandbox_groups),
            "real_format_transcript_count": sum(item["scored_records"] for item in real_format_groups),
            "reviewed_local_open_weight_ledger_count": len(rankings),
            "reviewed_local_open_weight_records": reviewed_local_records,
            "human_reviewed_adjudication_count": adjudication_summary["adjudication_records"],
            "scorer_reviewer_agreement": str(
                reliability_summary.get("scorer_review_agreement_rate", "not available")
            ),
            "approval_gate_false_negatives": str(approval_gate.get("scorer_false_negatives", "not available")),
        },
        "classes": {
            "hand_authored_fixture": {
                "fixture_groups": len(synthetic_fixture_groups),
                "scored_records": sum(item["scored_records"] for item in synthetic_fixture_groups),
                "boundary": "Synthetic and saved public-safe fixtures for evaluator coverage.",
            },
            "real_format_saved_transcript": {
                "fixture_groups": len(real_format_groups),
                "scored_records": sum(item["scored_records"] for item in real_format_groups),
                "boundary": "Saved transcript or adapter-shaped evidence; not live production proof.",
            },
            "sandbox_dry_run": {
                "fixture_groups": len(sandbox_groups),
                "scored_records": sum(item["scored_records"] for item in sandbox_groups),
                "reviewed_records": int(sandbox_review_coverage.get("reviewed_records", 0) or 0),
                "pass_rate": percent(
                    sum(item["passed"] for item in sandbox_groups),
                    sum(item["scored_records"] for item in sandbox_groups),
                ),
                "boundary": "No-side-effect saved agent outputs with action-event metadata.",
            },
            "local_open_weight_run_ledger": {
                "ledger_count": len(rankings),
                "reviewed_records": reviewed_local_records,
                "boundary": "Reviewed local/open-weight ledgers; not broad model rankings outside the claim process.",
            },
            "human_reviewed_adjudication": {
                "reviewed_records": adjudication_summary["adjudication_records"],
                "reviewer_count": adjudication_summary["reviewer_count"],
                "boundary": "Reviewer decisions remain separate from deterministic scored traces.",
            },
        },
    }


def summarize_adjudication(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Extract review status and coverage from the adjudication snapshot."""

    result_summary = snapshot.get("result_summary", {})
    reviewer_decisions = snapshot.get("reviewer_decisions", {})
    coverage = snapshot.get("review_coverage_by_source_trace", {})
    return {
        "adjudication_records": int(snapshot.get("adjudication_records", 0)),
        "reviewer_count": int(snapshot.get("reviewer_count", 0)),
        "needs_discussion": int(reviewer_decisions.get("needs_discussion", 0)),
        "override_pass": int(reviewer_decisions.get("override_pass", 0)),
        "override_fail": int(reviewer_decisions.get("override_fail", 0)),
        "changed_result_count": int(result_summary.get("changed_result_count", 0)),
        "adjudicated_pass_rate": str(result_summary.get("adjudicated_pass_rate", "0.0%")),
        "source_trace_coverage": coverage,
    }


def summarize_harness_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Summarize the optional harness integration decision."""

    quality_gate = plan.get("quality_gate", {})
    return {
        "target_runtime": str(plan.get("target_runtime", "unknown")),
        "decision": str(plan.get("decision", "unknown")),
        "runtime_native_state_required": bool(plan.get("runtime_native_state_required", False)),
        "preferred_paths": list(plan.get("preferred_paths", [])),
        "harness_execution_in_quality_gate": bool(quality_gate.get("harness_execution_in_quality_gate", False)),
        "next_review_trigger": str(plan.get("next_review_trigger", "")),
    }


def product_kpis(
    baseline_summary: dict[str, Any],
    external_summary: dict[str, Any],
    adjudication_summary: dict[str, Any],
    harness_summary: dict[str, Any],
    evidence_coverage: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return compact dashboard KPI rows."""

    total_fixture_records = int(external_summary["total_scored_records"])
    failed_fixture_records = int(external_summary["failed_records"])
    evidence_summary = evidence_coverage["summary"]
    return [
        {
            "metric_id": "baseline_pass_rate",
            "label": "Baseline Pass Rate",
            "value": baseline_summary["pass_rate"],
            "detail": f"{baseline_summary['passed']} passed of {baseline_summary['total_records']} scored records",
        },
        {
            "metric_id": "external_fixture_pass_rate",
            "label": "External Fixture Pass Rate",
            "value": percent(total_fixture_records - failed_fixture_records, total_fixture_records),
            "detail": f"{total_fixture_records - failed_fixture_records} passed of {total_fixture_records} scored fixture records",
        },
        {
            "metric_id": "sandbox_dry_run_pass_rate",
            "label": "Sandbox Dry-Run Pass Rate",
            "value": external_summary["sandbox_pass_rate"],
            "detail": f"{external_summary['sandbox_scenario_count']} sandbox scenarios scored with no external side effects",
        },
        {
            "metric_id": "evidence_class_coverage",
            "label": "Evidence Class Coverage",
            "value": len(evidence_coverage["classes"]),
            "detail": (
                f"{evidence_summary['sandbox_scenario_count']} sandbox, "
                f"{evidence_summary['real_format_transcript_count']} transcript-shaped, "
                f"{evidence_summary['reviewed_local_open_weight_ledger_count']} reviewed local/open-weight ledgers"
            ),
        },
        {
            "metric_id": "review_needs_discussion",
            "label": "Review Records Needing Discussion",
            "value": adjudication_summary["needs_discussion"],
            "detail": "Reviewer decisions still marked needs_discussion",
        },
        {
            "metric_id": "harness_bridge_decision",
            "label": "Harness Bridge Decision",
            "value": harness_summary["decision"],
            "detail": "Runtime-native state required: "
            f"{str(harness_summary['runtime_native_state_required']).lower()}",
        },
    ]


def release_view(
    baseline_summary: dict[str, Any],
    adjudication_summary: dict[str, Any],
    harness_summary: dict[str, Any],
    evidence_coverage: dict[str, Any],
) -> dict[str, Any]:
    """Return release-oriented decision context."""

    evidence_summary = evidence_coverage["summary"]
    return {
        "headline": "Local deterministic gate remains stable; sandbox dry-run evidence is now separated from fixture and ledger evidence.",
        "baseline_result": (
            f"{baseline_summary['passed']} passed, {baseline_summary['failed']} failed "
            f"({baseline_summary['pass_rate']} pass rate)"
        ),
        "review_status": (
            f"{adjudication_summary['adjudication_records']} adjudication records; "
            f"{adjudication_summary['needs_discussion']} need discussion"
        ),
        "harness_status": (
            f"{harness_summary['decision']} for {harness_summary['target_runtime']}; "
            "harness execution remains outside the quality gate"
        ),
        "evidence_status": (
            f"{evidence_summary['sandbox_scenario_count']} sandbox scenarios, "
            f"{evidence_summary['real_format_transcript_count']} transcript-shaped records, "
            f"{evidence_summary['reviewed_local_open_weight_ledger_count']} reviewed local/open-weight ledgers"
        ),
    }


def engineering_view(
    baseline_summary: dict[str, Any],
    fixture_summaries: list[dict[str, Any]],
    adjudication_summary: dict[str, Any],
) -> dict[str, Any]:
    """Return engineering-facing follow-up context."""

    highest_failure_fixtures = sorted(
        fixture_summaries,
        key=lambda item: (-int(item["failed"]), str(item["fixture_id"])),
    )
    return {
        "primary_failure_modes": baseline_summary["failure_modes"],
        "highest_failure_fixture_groups": highest_failure_fixtures[:3],
        "changed_review_results": adjudication_summary["changed_result_count"],
        "source_trace_coverage": adjudication_summary["source_trace_coverage"],
    }


def generate_markdown(summary: dict[str, Any]) -> str:
    """Generate the reader-facing product summary report."""

    baseline = summary["baseline"]
    external = summary["external_fixtures"]
    adjudication = summary["adjudication"]
    harness = summary["harness_bridge"]
    evidence = summary["evidence_class_coverage"]
    release = summary["release_view"]

    lines = [
        "# Reporting Product Summary",
        "",
        "## Executive View",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Generated at | `{summary['generated_at']}` |",
        f"| Baseline result | {release['baseline_result']} |",
        f"| External fixture records | {external['total_scored_records']} scored records across {external['fixture_groups']} groups |",
        f"| Sandbox dry-run records | {external['sandbox_scenario_count']} scored records at {external['sandbox_pass_rate']} pass rate |",
        f"| Review status | {release['review_status']} |",
        f"| Harness status | {release['harness_status']} |",
        f"| Evidence status | {release['evidence_status']} |",
        "",
        "This report is generated from committed local artifacts. It is a product-oriented summary for repeated development decisions, not a live model benchmark.",
        "",
        "## Dashboard KPIs",
        "",
        _kpi_table(summary["product_kpis"]),
        "",
        "## Baseline By Profile",
        "",
        _group_table(baseline["by_profile"], "Profile"),
        "",
        "## Baseline By Category",
        "",
        _group_table(baseline["by_category"], "Category"),
        "",
        "## External Fixture Groups",
        "",
        _fixture_table(external["groups"]),
        "",
        "## Evidence Class Coverage",
        "",
        _evidence_class_table(evidence["classes"]),
        "",
        "## Engineering View",
        "",
        f"- Primary baseline failure modes: {_format_mapping(summary['engineering_view']['primary_failure_modes'])}.",
        f"- Adjudication changed result count: {summary['engineering_view']['changed_review_results']}.",
        f"- Harness bridge decision: `{harness['decision']}` for `{harness['target_runtime']}`.",
        "",
        "## Boundaries",
        "",
        "- Reads already-scored traces, manifests, snapshots, and decision plans.",
        "- Does not collect outputs, rescore records, run providers, run local models, execute agents, use network access, or perform external actions.",
        "- All source paths are listed in the JSON snapshot at `reports/comparisons/reporting_product_summary.json`.",
        "",
    ]
    return "\n".join(lines)


def _kpi_table(kpis: list[dict[str, Any]]) -> str:
    lines = [
        "| Metric | Value | Detail |",
        "| --- | ---: | --- |",
    ]
    for kpi in kpis:
        lines.append(f"| {kpi['label']} | `{kpi['value']}` | {kpi['detail']} |")
    return "\n".join(lines)


def _group_table(groups: dict[str, dict[str, Any]], label: str) -> str:
    lines = [
        f"| {label} | Total | Passed | Failed | Pass Rate |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for key, value in groups.items():
        lines.append(
            f"| `{key}` | {value['total']} | {value['passed']} | {value['failed']} | {value['pass_rate']} |"
        )
    return "\n".join(lines)


def _fixture_table(groups: list[dict[str, Any]]) -> str:
    lines = [
        "| Fixture Group | Records | Passed | Failed | Pass Rate | Quality Gate |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for group in groups:
        lines.append(
            f"| `{group['fixture_id']}` | {group['scored_records']} | {group['passed']} | "
            f"{group['failed']} | {group['pass_rate']} | {_yes_no(group['quality_gate_included'])} |"
        )
    return "\n".join(lines)


def _evidence_class_table(classes: dict[str, dict[str, Any]]) -> str:
    lines = [
        "| Evidence Class | Count | Reviewed | Boundary |",
        "| --- | ---: | ---: | --- |",
    ]
    for class_id, value in classes.items():
        count = value.get("scored_records", value.get("ledger_count", value.get("reviewed_records", 0)))
        reviewed = value.get("reviewed_records", "n/a")
        lines.append(f"| `{class_id}` | {count} | {reviewed} | {value['boundary']} |")
    return "\n".join(lines)


def group_summary(records: list[dict[str, Any]], key: str, preferred_order: list[str]) -> dict[str, dict[str, Any]]:
    """Return pass/fail summary for a field."""

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record.get(key, "unknown"))].append(record)

    ordered_keys = [value for value in preferred_order if value in grouped]
    ordered_keys.extend(sorted(set(grouped) - set(ordered_keys)))

    summary = {}
    for group_key in ordered_keys:
        group_records = grouped[group_key]
        passed = count_passed(group_records)
        total = len(group_records)
        summary[group_key] = {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": percent(passed, total),
        }
    return summary


def failure_mode_counts(records: list[dict[str, Any]]) -> Counter[str]:
    """Count failure mode labels in scored records."""

    counts: Counter[str] = Counter()
    for record in records:
        for failure_mode in record.get("failure_modes", []):
            counts[str(failure_mode)] += 1
    return counts


def load_required_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSONL and require at least one record."""

    records = load_jsonl_records(path)
    if not records:
        raise ReportingProductSummaryError(f"{display_path(path)} must not be empty")
    return records


def load_optional_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return load_json_object(path)
    except (OSError, ValueError):
        return {}


def count_passed(records: list[dict[str, Any]]) -> int:
    return sum(1 for record in records if record.get("passed") is True)


def unique_values(records: list[dict[str, Any]], key: str) -> list[str]:
    values = []
    seen = set()
    for record in records:
        value = str(record.get(key, "unknown"))
        if value not in seen:
            values.append(value)
            seen.add(value)
    return values


def display_path(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def _format_mapping(value: dict[str, Any]) -> str:
    if not value:
        return "`none`"
    return ", ".join(f"`{key}`={value[key]}" for key in sorted(value))


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def main() -> int:
    try:
        summary = build_summary()
        write_json_object(summary, JSON_OUTPUT_PATH)
        write_text(generate_markdown(summary), MARKDOWN_OUTPUT_PATH)
    except (OSError, ValueError, ReportingProductSummaryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"summary JSON path: {display_path(JSON_OUTPUT_PATH)}")
    print(f"summary report path: {display_path(MARKDOWN_OUTPUT_PATH)}")
    print(f"baseline records: {summary['baseline']['total_records']}")
    print(f"external fixture records: {summary['external_fixtures']['total_scored_records']}")
    print("reporting product summary generation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
