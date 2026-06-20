"""Generate a deterministic evidence quality audit from committed artifacts.

This M40 audit reads local cases, scored traces, fixture manifests,
adjudication artifacts, and report metadata. It does not collect new outputs,
rescore records, call providers, run models, execute agents, inspect private
logs, use networks, or perform external actions.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any

from reporting_utils import load_json_object, load_jsonl_records, percent, write_json_object, write_text


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-20T00:00:00Z"

CASE_PATHS = [
    REPO_ROOT / "evals/cases/safe_task_cases.jsonl",
    REPO_ROOT / "evals/cases/approval_gate_cases.jsonl",
    REPO_ROOT / "evals/cases/refusal_cases.jsonl",
    REPO_ROOT / "evals/cases/uncertainty_cases.jsonl",
]
BASELINE_TRACE_PATH = REPO_ROOT / "traces/scored/baseline_mock_run.jsonl"
FIXTURE_MANIFEST_PATH = REPO_ROOT / "traces/external/fixture_manifest.json"
ADJUDICATION_MANIFEST_PATH = REPO_ROOT / "traces/external/adjudication_manifest.json"
ADJUDICATION_SNAPSHOT_PATH = REPO_ROOT / "reports/comparisons/adjudication_regression_snapshot.json"
REPORT_MANIFEST_PATH = REPO_ROOT / "reports/comparisons/report_manifest.json"
PRODUCT_SUMMARY_PATH = REPO_ROOT / "reports/comparisons/reporting_product_summary.json"
HARNESS_BRIDGE_PLAN_PATH = REPO_ROOT / "traces/external/harness_bridge_plan.example.json"
SCORER_PATH = REPO_ROOT / "src/scorers.py"
SCORER_LIMITATIONS_PATH = REPO_ROOT / "docs/wiki/concepts/v0_scorer_limitations.md"
ROADMAP_PATH = REPO_ROOT / "docs/roadmap.md"

JSON_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/evidence_quality_audit.json"
MARKDOWN_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/evidence_quality_audit.md"


class EvidenceQualityAuditError(Exception):
    """Evidence quality audit generation error."""


def build_audit() -> dict[str, Any]:
    """Build the deterministic M40 evidence quality audit."""

    case_inventory = build_case_inventory()
    baseline_records = load_required_jsonl(BASELINE_TRACE_PATH)
    fixture_manifest = load_json_object(FIXTURE_MANIFEST_PATH)
    adjudication_manifest = load_json_object(ADJUDICATION_MANIFEST_PATH)
    adjudication_snapshot = load_json_object(ADJUDICATION_SNAPSHOT_PATH)
    report_manifest = load_json_object(REPORT_MANIFEST_PATH)

    fixture_inventory = build_fixture_inventory(fixture_manifest)
    scored_trace_inventory = build_scored_trace_inventory(baseline_records, fixture_inventory)
    adjudication_inventory = build_adjudication_inventory(
        adjudication_manifest,
        adjudication_snapshot,
        fixture_inventory,
    )
    report_inventory = build_report_inventory(report_manifest)
    gaps = build_gap_report(
        case_inventory,
        scored_trace_inventory,
        fixture_inventory,
        adjudication_inventory,
        report_inventory,
    )

    return {
        "audit_id": "m40_evidence_quality_audit",
        "generated_at": GENERATED_AT,
        "scope": "Deterministic evidence inventory and gap report for committed local evaluator artifacts.",
        "source_paths": source_paths(),
        "safety": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
            "credentials_required": False,
        },
        "inventory": {
            "eval_cases": case_inventory,
            "scored_traces": scored_trace_inventory,
            "external_fixtures": fixture_inventory,
            "adjudications": adjudication_inventory,
            "reports": report_inventory,
        },
        "gap_report": gaps,
        "recommendations": recommendations(gaps),
        "claim_boundary": [
            "This audit can describe local fixture, scorer, adjudication, and reporting coverage.",
            "This audit cannot rank models, agents, Hermes, OpenClaw, hosted systems, or production behavior.",
            "This audit does not prove live runtime behavior because it uses committed saved artifacts only.",
        ],
    }


def build_case_inventory() -> dict[str, Any]:
    """Summarize committed eval case coverage."""

    by_file = []
    category_counts: Counter[str] = Counter()
    severity_counts: Counter[str] = Counter()
    policy_refs: Counter[str] = Counter()
    expected_failure_modes: Counter[str] = Counter()
    total_cases = 0

    for path in CASE_PATHS:
        records = load_required_jsonl(path)
        total_cases += len(records)
        file_categories: Counter[str] = Counter()
        file_severities: Counter[str] = Counter()
        file_failure_modes: Counter[str] = Counter()
        for record in records:
            category = str(record.get("category", "unknown"))
            severity = str(record.get("severity", "unknown"))
            file_categories[category] += 1
            category_counts[category] += 1
            file_severities[severity] += 1
            severity_counts[severity] += 1
            for policy_ref in record.get("policy_refs", []):
                policy_refs[str(policy_ref)] += 1
            for failure_mode in record.get("expected_failure_modes", []):
                file_failure_modes[str(failure_mode)] += 1
                expected_failure_modes[str(failure_mode)] += 1

        by_file.append(
            {
                "path": display_path(path),
                "cases": len(records),
                "categories": sorted_dict(file_categories),
                "severities": sorted_dict(file_severities),
                "expected_failure_modes": sorted_dict(file_failure_modes),
            }
        )

    return {
        "case_files": len(CASE_PATHS),
        "total_cases": total_cases,
        "by_category": sorted_dict(category_counts),
        "by_severity": sorted_dict(severity_counts),
        "policy_ref_count": len(policy_refs),
        "expected_failure_modes": sorted_dict(expected_failure_modes),
        "files": by_file,
    }


def build_fixture_inventory(fixture_manifest: dict[str, Any]) -> dict[str, Any]:
    """Summarize manifest-backed external fixture evidence."""

    fixtures = fixture_manifest.get("fixtures", [])
    if not isinstance(fixtures, list) or not fixtures:
        raise EvidenceQualityAuditError("fixture manifest must contain fixtures")

    groups = []
    source_type_counts: Counter[str] = Counter()
    provenance_counts: Counter[str] = Counter()
    classification_counts: Counter[str] = Counter()
    total_source_records = 0
    total_scored_records = 0
    total_failed_records = 0
    quality_gate_included = 0

    for fixture in fixtures:
        if not isinstance(fixture, dict):
            raise EvidenceQualityAuditError("fixture manifest entries must be objects")
        source_path = REPO_ROOT / str(fixture["source_path"])
        scored_path = REPO_ROOT / str(fixture["scored_trace_path"])
        source_records = load_required_jsonl(source_path)
        scored_records = load_required_jsonl(scored_path)
        passed = count_passed(scored_records)
        failed = len(scored_records) - passed
        source_type = str(fixture["source_type"])
        provenance_class = str(fixture["provenance_class"])
        data_classification = str(fixture["data_classification"])

        source_type_counts[source_type] += 1
        provenance_counts[provenance_class] += 1
        classification_counts[data_classification] += 1
        total_source_records += len(source_records)
        total_scored_records += len(scored_records)
        total_failed_records += failed
        if fixture["quality_gate_included"] is True:
            quality_gate_included += 1

        groups.append(
            {
                "fixture_id": str(fixture["fixture_id"]),
                "source_type": source_type,
                "provenance_class": provenance_class,
                "data_classification": data_classification,
                "source_path": str(fixture["source_path"]),
                "scored_trace_path": str(fixture["scored_trace_path"]),
                "source_records": len(source_records),
                "scored_records": len(scored_records),
                "passed": passed,
                "failed": failed,
                "pass_rate": percent(passed, len(scored_records)),
                "quality_gate_included": bool(fixture["quality_gate_included"]),
                "limitations": list(fixture.get("limitations", [])),
                "observed_failure_modes": sorted_dict(failure_mode_counts(scored_records)),
            }
        )

    return {
        "fixture_groups": len(groups),
        "quality_gate_included_groups": quality_gate_included,
        "total_source_records": total_source_records,
        "total_scored_records": total_scored_records,
        "failed_records": total_failed_records,
        "pass_rate": percent(total_scored_records - total_failed_records, total_scored_records),
        "source_type_counts": sorted_dict(source_type_counts),
        "provenance_class_counts": sorted_dict(provenance_counts),
        "data_classification_counts": sorted_dict(classification_counts),
        "groups": groups,
    }


def build_scored_trace_inventory(
    baseline_records: list[dict[str, Any]],
    fixture_inventory: dict[str, Any],
) -> dict[str, Any]:
    """Summarize baseline and external scored traces."""

    baseline = trace_summary(BASELINE_TRACE_PATH, baseline_records)
    external_total = int(fixture_inventory["total_scored_records"])
    external_failed = int(fixture_inventory["failed_records"])
    return {
        "baseline": baseline,
        "external_fixture_traces": {
            "trace_groups": int(fixture_inventory["fixture_groups"]),
            "total_records": external_total,
            "passed": external_total - external_failed,
            "failed": external_failed,
            "pass_rate": percent(external_total - external_failed, external_total),
            "trace_paths": [group["scored_trace_path"] for group in fixture_inventory["groups"]],
        },
        "total_scored_records": baseline["total_records"] + external_total,
        "observed_failure_modes": sorted_dict(
            Counter(baseline["failure_modes"]) + fixture_failure_modes(fixture_inventory)
        ),
    }


def build_adjudication_inventory(
    adjudication_manifest: dict[str, Any],
    adjudication_snapshot: dict[str, Any],
    fixture_inventory: dict[str, Any],
) -> dict[str, Any]:
    """Summarize adjudication coverage and unreviewed fixture groups."""

    fixtures = adjudication_manifest.get("adjudication_fixtures", [])
    if not isinstance(fixtures, list):
        raise EvidenceQualityAuditError("adjudication manifest fixtures must be a list")

    covered_source_traces = set(adjudication_snapshot.get("review_coverage_by_source_trace", {}).keys())
    external_trace_paths = [str(group["scored_trace_path"]) for group in fixture_inventory["groups"]]
    unadjudicated_external = [path for path in external_trace_paths if path not in covered_source_traces]

    return {
        "adjudication_fixture_count": int(adjudication_snapshot.get("adjudication_fixture_count", len(fixtures))),
        "adjudication_records": int(adjudication_snapshot.get("adjudication_records", 0)),
        "reviewer_count": int(adjudication_snapshot.get("reviewer_count", 0)),
        "needs_discussion": int(adjudication_snapshot.get("reviewer_decisions", {}).get("needs_discussion", 0)),
        "override_pass": int(adjudication_snapshot.get("reviewer_decisions", {}).get("override_pass", 0)),
        "override_fail": int(adjudication_snapshot.get("reviewer_decisions", {}).get("override_fail", 0)),
        "source_trace_count": int(adjudication_snapshot.get("source_trace_count", len(covered_source_traces))),
        "source_trace_coverage": adjudication_snapshot.get("review_coverage_by_source_trace", {}),
        "category_coverage": adjudication_snapshot.get("review_coverage_by_category", {}),
        "profile_coverage": adjudication_snapshot.get("review_coverage_by_profile", {}),
        "unadjudicated_external_scored_traces": unadjudicated_external,
    }


def build_report_inventory(report_manifest: dict[str, Any]) -> dict[str, Any]:
    """Summarize report artifact manifest coverage."""

    artifacts = report_manifest.get("report_artifacts", [])
    if not isinstance(artifacts, list) or not artifacts:
        raise EvidenceQualityAuditError("report manifest must contain report_artifacts")

    quality_gate_artifacts = [artifact for artifact in artifacts if artifact.get("quality_gate_included") is True]
    return {
        "report_artifacts": len(artifacts),
        "quality_gate_artifacts": len(quality_gate_artifacts),
        "markdown_reports": sum(1 for artifact in artifacts if artifact.get("artifact_type") == "markdown_report"),
        "json_snapshots": sum(1 for artifact in artifacts if artifact.get("artifact_type") == "json_snapshot"),
        "public_safe_artifacts": sum(
            1
            for artifact in artifacts
            if artifact.get("safety_assertions", {}).get("public_safe") is True
        ),
        "artifact_paths": [str(artifact["path"]) for artifact in artifacts],
    }


def build_gap_report(
    case_inventory: dict[str, Any],
    scored_trace_inventory: dict[str, Any],
    fixture_inventory: dict[str, Any],
    adjudication_inventory: dict[str, Any],
    report_inventory: dict[str, Any],
) -> dict[str, Any]:
    """Build source-backed evidence gaps grouped by type."""

    external_group_sizes = [int(group["scored_records"]) for group in fixture_inventory["groups"]]
    min_group = min(external_group_sizes)
    max_group = max(external_group_sizes)
    observed_failure_modes = sorted(scored_trace_inventory["observed_failure_modes"])
    refusal_coverage = adjudication_inventory["category_coverage"].get("refusal_required", {})

    missing_fixture_coverage = [
        gap(
            "no_live_runtime_evidence",
            "high",
            "The committed evidence is saved, sanitized, synthetic, or mock evidence only; it does not prove live runtime behavior.",
            [display_path(FIXTURE_MANIFEST_PATH), display_path(HARNESS_BRIDGE_PLAN_PATH), display_path(ROADMAP_PATH)],
        ),
        gap(
            "small_external_fixture_groups",
            "medium",
            (
                f"External fixture groups contain {min_group}-{max_group} scored records each "
                f"({fixture_inventory['total_scored_records']} total), so they validate paths but are not representative samples."
            ),
            [group["source_path"] for group in fixture_inventory["groups"]],
        ),
        gap(
            "external_fixture_adjudication_absent",
            "medium",
            (
                f"{len(adjudication_inventory['unadjudicated_external_scored_traces'])} external scored traces have no committed "
                "adjudication coverage yet."
            ),
            adjudication_inventory["unadjudicated_external_scored_traces"],
        ),
        gap(
            "refusal_required_review_gap",
            "medium",
            (
                "Refusal-required baseline records have "
                f"{refusal_coverage.get('review_coverage', '0.0%')} adjudication coverage "
                f"({refusal_coverage.get('reviewed_records', 0)} reviewed records)."
            ),
            [display_path(ADJUDICATION_SNAPSHOT_PATH), display_path(ADJUDICATION_MANIFEST_PATH)],
        ),
    ]

    scorer_weakness = [
        gap(
            "heuristic_scorer_not_semantic_judge",
            "high",
            "The v0 scorer uses deterministic phrase and pattern checks, so scores are triage signals rather than ground truth.",
            [display_path(SCORER_PATH), display_path(SCORER_LIMITATIONS_PATH)],
        ),
        gap(
            "limited_adjudication_calibration_set",
            "medium",
            (
                f"{adjudication_inventory['adjudication_records']} adjudications cover "
                f"{adjudication_inventory['source_trace_count']} source trace; external fixture traces are not calibrated yet."
            ),
            [display_path(ADJUDICATION_MANIFEST_PATH), display_path(ADJUDICATION_SNAPSHOT_PATH)],
        ),
        gap(
            "failure_modes_are_taxonomy_bound",
            "medium",
            (
                "Current scored traces surface this fixed failure-mode set: "
                f"{', '.join(observed_failure_modes) if observed_failure_modes else 'none'}; semantic variants still require review."
            ),
            [display_path(BASELINE_TRACE_PATH), *[group["scored_trace_path"] for group in fixture_inventory["groups"]]],
        ),
    ]

    reporting_weakness = [
        gap(
            "no_historical_trend_snapshots_yet",
            "medium",
            "Reports are point-in-time artifacts; M43 is still needed for versioned evaluator-health trends.",
            [display_path(ROADMAP_PATH), display_path(PRODUCT_SUMMARY_PATH)],
        ),
        gap(
            "audit_findings_are_not_gate_thresholds",
            "low",
            "M40 recommendations are descriptive evidence gaps; they do not automatically fail or rewrite scored traces.",
            [display_path(REPORT_MANIFEST_PATH), display_path(JSON_OUTPUT_PATH)],
        ),
        gap(
            "report_artifacts_outpace_review_depth",
            "low",
            (
                f"{report_inventory['report_artifacts']} report artifacts are indexed, while "
                f"{adjudication_inventory['adjudication_records']} adjudication records exist."
            ),
            [display_path(REPORT_MANIFEST_PATH), display_path(ADJUDICATION_SNAPSHOT_PATH)],
        ),
    ]

    return {
        "missing_fixture_coverage": missing_fixture_coverage,
        "scorer_weakness": scorer_weakness,
        "reporting_weakness": reporting_weakness,
        "summary": {
            "gap_count": len(missing_fixture_coverage) + len(scorer_weakness) + len(reporting_weakness),
            "case_count": case_inventory["total_cases"],
            "total_scored_records": scored_trace_inventory["total_scored_records"],
            "external_fixture_records": fixture_inventory["total_scored_records"],
            "adjudication_records": adjudication_inventory["adjudication_records"],
        },
    }


def recommendations(gaps: dict[str, Any]) -> list[dict[str, Any]]:
    """Return public-safe next-step recommendations tied to gap IDs."""

    return [
        {
            "recommendation_id": "expand_public_safe_transcripts",
            "priority": "high",
            "target_phase": "M41",
            "summary": "Add sanitized saved transcript fixtures for the weakest external fixture and adjudication coverage areas.",
            "source_gap_ids": [
                "small_external_fixture_groups",
                "external_fixture_adjudication_absent",
                "refusal_required_review_gap",
            ],
            "public_safe_path": "Use reviewed saved transcripts with tool summaries and approval metadata, not private runtime logs.",
        },
        {
            "recommendation_id": "calibrate_before_scorer_changes",
            "priority": "high",
            "target_phase": "M42",
            "summary": "Add adjudications for external fixtures before accepting scorer refinements.",
            "source_gap_ids": [
                "heuristic_scorer_not_semantic_judge",
                "limited_adjudication_calibration_set",
            ],
            "public_safe_path": "Keep heuristic scores and reviewer decisions separate in committed local artifacts.",
        },
        {
            "recommendation_id": "add_evaluator_health_trends",
            "priority": "medium",
            "target_phase": "M43",
            "summary": "Create versioned trend snapshots after the evidence inventory and fixture expansion are stable.",
            "source_gap_ids": [
                "no_historical_trend_snapshots_yet",
                "report_artifacts_outpace_review_depth",
            ],
            "public_safe_path": "Trend evaluator artifact counts, fixture counts, failure modes, and review coverage without benchmark claims.",
        },
    ]


def trace_summary(path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize one scored trace."""

    if not records:
        raise EvidenceQualityAuditError(f"{display_path(path)} must not be empty")
    passed = count_passed(records)
    case_ids = {str(record.get("case_id", "")) for record in records}
    profiles = Counter(str(record.get("profile_name", "unknown")) for record in records)
    categories = Counter(str(record.get("category", "unknown")) for record in records)
    return {
        "path": display_path(path),
        "total_records": len(records),
        "unique_cases": len(case_ids),
        "profiles": sorted_dict(profiles),
        "categories": sorted_dict(categories),
        "passed": passed,
        "failed": len(records) - passed,
        "pass_rate": percent(passed, len(records)),
        "failure_modes": sorted_dict(failure_mode_counts(records)),
    }


def load_required_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load a non-empty JSONL file."""

    if not path.exists():
        raise EvidenceQualityAuditError(f"{display_path(path)} does not exist")
    records = load_jsonl_records(path)
    if not records:
        raise EvidenceQualityAuditError(f"{display_path(path)} must not be empty")
    return records


def failure_mode_counts(records: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for record in records:
        for failure_mode in record.get("failure_modes", []):
            counts[str(failure_mode)] += 1
    return counts


def fixture_failure_modes(fixture_inventory: dict[str, Any]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for group in fixture_inventory["groups"]:
        counts.update({str(key): int(value) for key, value in group["observed_failure_modes"].items()})
    return counts


def count_passed(records: list[dict[str, Any]]) -> int:
    return sum(1 for record in records if record.get("passed") is True)


def gap(gap_id: str, severity: str, summary: str, source_paths_values: list[str]) -> dict[str, Any]:
    return {
        "gap_id": gap_id,
        "severity": severity,
        "summary": summary,
        "source_paths": source_paths_values,
    }


def sorted_dict(counter: Counter[str] | dict[str, Any]) -> dict[str, Any]:
    return {key: counter[key] for key in sorted(counter)}


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def source_paths() -> list[str]:
    paths = [
        *CASE_PATHS,
        BASELINE_TRACE_PATH,
        FIXTURE_MANIFEST_PATH,
        ADJUDICATION_MANIFEST_PATH,
        ADJUDICATION_SNAPSHOT_PATH,
        REPORT_MANIFEST_PATH,
        PRODUCT_SUMMARY_PATH,
        HARNESS_BRIDGE_PLAN_PATH,
        SCORER_PATH,
        SCORER_LIMITATIONS_PATH,
        ROADMAP_PATH,
    ]
    return [display_path(path) for path in paths]


def generate_markdown(audit: dict[str, Any]) -> str:
    """Generate the reader-facing M40 evidence audit report."""

    inventory = audit["inventory"]
    gaps = audit["gap_report"]
    summary = gaps["summary"]
    lines = [
        "# Evidence Quality Audit",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | ---: |",
        f"| Eval cases | {summary['case_count']} |",
        f"| Total scored records | {summary['total_scored_records']} |",
        f"| External fixture records | {summary['external_fixture_records']} |",
        f"| Adjudication records | {summary['adjudication_records']} |",
        f"| Evidence gaps | {summary['gap_count']} |",
        "",
        "This is an audit of committed local evidence. It is not a live model benchmark, leaderboard, or real-world agent quality claim.",
        "",
        "## Inventory",
        "",
        "### Eval Cases",
        "",
        _case_table(inventory["eval_cases"]["files"]),
        "",
        "### Scored Evidence",
        "",
        _scored_evidence_table(inventory["scored_traces"]),
        "",
        "### External Fixtures",
        "",
        _fixture_table(inventory["external_fixtures"]["groups"]),
        "",
        "### Adjudication Coverage",
        "",
        _coverage_table(inventory["adjudications"]),
        "",
        "### Report Artifacts",
        "",
        _report_table(inventory["reports"]),
        "",
        "## Gap Report",
        "",
        "### Missing Fixture Coverage",
        "",
        _gap_table(gaps["missing_fixture_coverage"]),
        "",
        "### Scorer Weakness",
        "",
        _gap_table(gaps["scorer_weakness"]),
        "",
        "### Reporting Weakness",
        "",
        _gap_table(gaps["reporting_weakness"]),
        "",
        "## Recommendations",
        "",
        _recommendation_table(audit["recommendations"]),
        "",
        "## Boundary",
        "",
        "\n".join(f"- {item}" for item in audit["claim_boundary"]),
        "",
        "## Sources",
        "",
        "\n".join(f"- `{path}`" for path in audit["source_paths"]),
        "",
    ]
    return "\n".join(lines)


def _case_table(files: list[dict[str, Any]]) -> str:
    lines = [
        "| Case file | Cases | Categories |",
        "| --- | ---: | --- |",
    ]
    for file_summary in files:
        lines.append(
            f"| `{file_summary['path']}` | {file_summary['cases']} | {_counts(file_summary['categories'])} |"
        )
    return "\n".join(lines)


def _scored_evidence_table(scored_traces: dict[str, Any]) -> str:
    baseline = scored_traces["baseline"]
    external = scored_traces["external_fixture_traces"]
    lines = [
        "| Evidence set | Records | Passed | Failed | Pass rate |",
        "| --- | ---: | ---: | ---: | ---: |",
        f"| Baseline mock trace | {baseline['total_records']} | {baseline['passed']} | {baseline['failed']} | {baseline['pass_rate']} |",
        f"| External fixture traces | {external['total_records']} | {external['passed']} | {external['failed']} | {external['pass_rate']} |",
    ]
    return "\n".join(lines)


def _fixture_table(groups: list[dict[str, Any]]) -> str:
    lines = [
        "| Fixture group | Source type | Scored | Failed | Pass rate |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for group in groups:
        lines.append(
            f"| `{group['fixture_id']}` | `{group['source_type']}` | {group['scored_records']} | "
            f"{group['failed']} | {group['pass_rate']} |"
        )
    return "\n".join(lines)


def _coverage_table(adjudications: dict[str, Any]) -> str:
    lines = [
        "| Coverage area | Reviewed | Source records | Coverage |",
        "| --- | ---: | ---: | ---: |",
    ]
    for source_path, coverage in adjudications["source_trace_coverage"].items():
        lines.append(
            f"| `{source_path}` | {coverage['reviewed_records']} | {coverage['source_records']} | "
            f"{coverage['review_coverage']} |"
        )
    for category, coverage in adjudications["category_coverage"].items():
        lines.append(
            f"| category `{category}` | {coverage['reviewed_records']} | {coverage['source_records']} | "
            f"{coverage['review_coverage']} |"
        )
    return "\n".join(lines)


def _report_table(reports: dict[str, Any]) -> str:
    return "\n".join(
        [
            "| Metric | Value |",
            "| --- | ---: |",
            f"| Report artifacts | {reports['report_artifacts']} |",
            f"| Quality-gate artifacts | {reports['quality_gate_artifacts']} |",
            f"| Markdown reports | {reports['markdown_reports']} |",
            f"| JSON snapshots | {reports['json_snapshots']} |",
        ]
    )


def _gap_table(gaps: list[dict[str, Any]]) -> str:
    lines = [
        "| Gap | Severity | Summary | Sources |",
        "| --- | --- | --- | --- |",
    ]
    for item in gaps:
        lines.append(
            f"| `{item['gap_id']}` | {item['severity']} | {item['summary']} | "
            f"{_path_list(item['source_paths'])} |"
        )
    return "\n".join(lines)


def _recommendation_table(items: list[dict[str, Any]]) -> str:
    lines = [
        "| Recommendation | Phase | Priority | Summary |",
        "| --- | --- | --- | --- |",
    ]
    for item in items:
        lines.append(
            f"| `{item['recommendation_id']}` | `{item['target_phase']}` | {item['priority']} | {item['summary']} |"
        )
    return "\n".join(lines)


def _counts(values: dict[str, Any]) -> str:
    if not values:
        return "`none`"
    return ", ".join(f"`{key}`: {value}" for key, value in values.items())


def _path_list(paths: list[str]) -> str:
    if not paths:
        return "`none`"
    displayed = paths[:3]
    suffix = "" if len(paths) <= 3 else f", +{len(paths) - 3} more"
    return ", ".join(f"`{path}`" for path in displayed) + suffix


def main() -> int:
    try:
        audit = build_audit()
        write_json_object(audit, JSON_OUTPUT_PATH)
        write_text(generate_markdown(audit), MARKDOWN_OUTPUT_PATH)
    except (OSError, ValueError, EvidenceQualityAuditError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary = audit["gap_report"]["summary"]
    print(f"evidence audit JSON path: {display_path(JSON_OUTPUT_PATH)}")
    print(f"evidence audit report path: {display_path(MARKDOWN_OUTPUT_PATH)}")
    print(f"eval cases audited: {summary['case_count']}")
    print(f"total scored records audited: {summary['total_scored_records']}")
    print(f"evidence gaps identified: {summary['gap_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
