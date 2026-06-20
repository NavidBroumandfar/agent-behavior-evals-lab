"""Generate deterministic evaluator-health trend snapshots.

This M43 reporting layer reads committed local scored traces, manifests,
snapshots, and calibration artifacts. It does not collect outputs, rescore
records, call providers, run models, execute agents, inspect private logs, use
networks, or perform external actions.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any

from reporting_utils import load_json_object, load_jsonl_records, percent, write_json_object, write_text


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-21T00:00:00Z"

BASELINE_TRACE_PATH = REPO_ROOT / "traces/scored/baseline_mock_run.jsonl"
FIXTURE_MANIFEST_PATH = REPO_ROOT / "traces/external/fixture_manifest.json"
ADJUDICATION_MANIFEST_PATH = REPO_ROOT / "traces/external/adjudication_manifest.json"
ADJUDICATION_SNAPSHOT_PATH = REPO_ROOT / "reports/comparisons/adjudication_regression_snapshot.json"
SCORER_CALIBRATION_PATH = REPO_ROOT / "reports/comparisons/scorer_calibration_summary.json"
SCORER_REFINEMENT_TRIAGE_PATH = REPO_ROOT / "reports/comparisons/scorer_refinement_triage.json"
REPORT_MANIFEST_PATH = REPO_ROOT / "reports/comparisons/report_manifest.json"
EVIDENCE_QUALITY_AUDIT_PATH = REPO_ROOT / "reports/comparisons/evidence_quality_audit.json"
REPORTING_PRODUCT_SUMMARY_PATH = REPO_ROOT / "reports/comparisons/reporting_product_summary.json"
SCORER_PATH = REPO_ROOT / "src/scorers.py"

JSON_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/historical_trend_snapshot.json"
MARKDOWN_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/historical_trend_report.md"


class HistoricalTrendSnapshotError(Exception):
    """Historical trend snapshot generation error."""


def build_trend_snapshot() -> dict[str, Any]:
    """Build the deterministic M43 trend snapshot."""

    baseline_records = load_required_jsonl(BASELINE_TRACE_PATH)
    fixture_manifest = load_json_object(FIXTURE_MANIFEST_PATH)
    adjudication_snapshot = load_json_object(ADJUDICATION_SNAPSHOT_PATH)
    calibration_summary = load_json_object(SCORER_CALIBRATION_PATH)
    scorer_triage = load_json_object(SCORER_REFINEMENT_TRIAGE_PATH)
    report_manifest = load_json_object(REPORT_MANIFEST_PATH)
    evidence_audit = load_json_object(EVIDENCE_QUALITY_AUDIT_PATH)
    product_summary = load_json_object(REPORTING_PRODUCT_SUMMARY_PATH)

    baseline = trace_trend_point("baseline_mock_run", BASELINE_TRACE_PATH, baseline_records)
    fixture_summary = fixture_trends(fixture_manifest)
    adjudication = adjudication_outcomes(adjudication_snapshot, calibration_summary)
    manifest_coverage = report_manifest_coverage(report_manifest)
    evidence = evidence_quality_trend(evidence_audit)
    current_snapshot = {
        "pass_rates": {
            "baseline": baseline,
            "external_fixtures": fixture_summary["aggregate"],
            "fixture_groups": fixture_summary["groups"],
        },
        "failure_modes": {
            "baseline": baseline["failure_modes"],
            "external_fixtures": fixture_summary["aggregate_failure_modes"],
            "combined": combined_failure_modes(baseline["failure_modes"], fixture_summary["aggregate_failure_modes"]),
        },
        "adjudication_outcomes": adjudication,
            "fixture_counts": fixture_summary["counts"],
            "report_manifest_coverage": manifest_coverage,
            "evidence_quality": evidence,
            "scorer_refinement_triage": scorer_refinement_triage_outcomes(scorer_triage),
        }

    return {
        "snapshot_id": "m43_historical_trend_snapshot",
        "snapshot_version": "0.1.0",
        "generated_at": GENERATED_AT,
        "scope": "Versioned evaluator-health trend snapshot derived from committed local artifacts.",
        "source_paths": source_paths(fixture_summary["groups"]),
        "safety": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
            "credentials_required": False,
        },
        "trend_dimensions": [
            "pass_rates",
            "failure_modes",
            "adjudication_outcomes",
            "fixture_counts",
            "report_manifest_coverage",
        ],
        "current_snapshot": current_snapshot,
        "versioned_trend_snapshots": versioned_trend_snapshots(
            baseline,
            fixture_summary,
            adjudication,
            scorer_triage,
            manifest_coverage,
            evidence,
            product_summary,
        ),
        "regeneration_check": {
            "quality_gate_command": "python3 scripts/dev.py check",
            "deterministic_local_only": True,
            "snapshot_changes_should_be_reviewed": True,
            "source_behavior_change_expected_for_metric_changes": True,
        },
        "claim_boundary": [
            "Trends describe evaluator health and committed fixture coverage.",
            "Trends do not rank models, agents, Hermes, OpenClaw, hosted systems, or production behavior.",
            "Pass-rate movement can reflect evaluator fixture changes, scorer changes, or report coverage changes.",
        ],
    }


def fixture_trends(fixture_manifest: dict[str, Any]) -> dict[str, Any]:
    """Build per-fixture and aggregate trend points from the fixture manifest."""

    fixtures = fixture_manifest.get("fixtures", [])
    if not isinstance(fixtures, list) or not fixtures:
        raise HistoricalTrendSnapshotError("fixture manifest must contain fixtures")

    groups = []
    source_type_counts: Counter[str] = Counter()
    data_classification_counts: Counter[str] = Counter()
    aggregate_failure_modes: Counter[str] = Counter()
    source_records = 0
    scored_records = 0
    passed_records = 0
    quality_gate_included_groups = 0

    for fixture in fixtures:
        if not isinstance(fixture, dict):
            raise HistoricalTrendSnapshotError("fixture manifest entries must be objects")
        fixture_id = str(fixture["fixture_id"])
        source_path = REPO_ROOT / str(fixture["source_path"])
        scored_path = REPO_ROOT / str(fixture["scored_trace_path"])
        source = load_required_jsonl(source_path)
        scored = load_required_jsonl(scored_path)
        point = trace_trend_point(fixture_id, scored_path, scored)
        point["source_path"] = str(fixture["source_path"])
        point["source_type"] = str(fixture["source_type"])
        point["data_classification"] = str(fixture["data_classification"])
        point["quality_gate_included"] = bool(fixture["quality_gate_included"])
        point["source_records"] = len(source)
        groups.append(point)

        source_type_counts[point["source_type"]] += 1
        data_classification_counts[point["data_classification"]] += 1
        aggregate_failure_modes.update({str(key): int(value) for key, value in point["failure_modes"].items()})
        source_records += len(source)
        scored_records += int(point["records"])
        passed_records += int(point["passed"])
        if point["quality_gate_included"] is True:
            quality_gate_included_groups += 1

    failed_records = scored_records - passed_records
    return {
        "aggregate": {
            "trend_id": "external_fixtures_all",
            "records": scored_records,
            "passed": passed_records,
            "failed": failed_records,
            "pass_rate": percent(passed_records, scored_records),
        },
        "aggregate_failure_modes": sorted_dict(aggregate_failure_modes),
        "counts": {
            "fixture_groups": len(groups),
            "quality_gate_included_groups": quality_gate_included_groups,
            "source_records": source_records,
            "scored_records": scored_records,
            "source_type_counts": sorted_dict(source_type_counts),
            "data_classification_counts": sorted_dict(data_classification_counts),
        },
        "groups": groups,
    }


def adjudication_outcomes(
    adjudication_snapshot: dict[str, Any],
    calibration_summary: dict[str, Any],
) -> dict[str, Any]:
    """Summarize reviewer and calibration outcomes."""

    reviewer_decisions = adjudication_snapshot.get("reviewer_decisions", {})
    result_summary = adjudication_snapshot.get("result_summary", {})
    coverage_by_source_trace = adjudication_snapshot.get("review_coverage_by_source_trace", {})
    calibration_counts = calibration_summary.get("calibration_labels", {}).get("counts", {})
    return {
        "adjudication_records": int(adjudication_snapshot.get("adjudication_records", 0)),
        "source_trace_count": int(adjudication_snapshot.get("source_trace_count", 0)),
        "reviewed_external_source_trace_count": sum(
            1
            for source_path in coverage_by_source_trace
            if str(source_path) != "traces/scored/baseline_mock_run.jsonl"
        ),
        "reviewer_decisions": sorted_mapping(reviewer_decisions),
        "changed_result_count": int(result_summary.get("changed_result_count", 0)),
        "adjudicated_pass_rate": str(result_summary.get("adjudicated_pass_rate", "0.0%")),
        "calibration_label_counts": sorted_mapping(calibration_counts),
        "accepted_scorer_changes": len(calibration_summary.get("accepted_scorer_changes", [])),
    }


def report_manifest_coverage(report_manifest: dict[str, Any]) -> dict[str, Any]:
    """Summarize report manifest coverage."""

    artifacts = report_manifest.get("report_artifacts", [])
    if not isinstance(artifacts, list) or not artifacts:
        raise HistoricalTrendSnapshotError("report manifest must contain report_artifacts")

    return {
        "report_artifacts": len(artifacts),
        "quality_gate_artifacts": sum(1 for artifact in artifacts if artifact.get("quality_gate_included") is True),
        "markdown_reports": sum(1 for artifact in artifacts if artifact.get("artifact_type") == "markdown_report"),
        "json_snapshots": sum(1 for artifact in artifacts if artifact.get("artifact_type") == "json_snapshot"),
        "public_safe_artifacts": sum(
            1
            for artifact in artifacts
            if artifact.get("safety_assertions", {}).get("public_safe") is True
        ),
    }


def scorer_refinement_triage_outcomes(scorer_triage: dict[str, Any]) -> dict[str, Any]:
    """Summarize scorer refinement triage outcomes."""

    decision = scorer_triage.get("decision_summary", {})
    return {
        "candidates": int(decision.get("candidates", 0)),
        "accepted_scorer_changes": int(decision.get("accepted_scorer_changes", 0)),
        "deferred_scorer_changes": int(decision.get("deferred_scorer_changes", 0)),
        "scorer_code_changed": bool(decision.get("scorer_code_changed", False)),
        "scorer_change_decision": str(decision.get("scorer_change_decision", "unknown")),
    }


def evidence_quality_trend(evidence_audit: dict[str, Any]) -> dict[str, Any]:
    """Extract gap counts from the current evidence quality audit."""

    gap_report = evidence_audit.get("gap_report", {})
    summary = gap_report.get("summary", {})
    return {
        "gap_count": int(summary.get("gap_count", 0)),
        "missing_fixture_coverage_gaps": len(gap_report.get("missing_fixture_coverage", [])),
        "scorer_weakness_gaps": len(gap_report.get("scorer_weakness", [])),
        "reporting_weakness_gaps": len(gap_report.get("reporting_weakness", [])),
    }


def versioned_trend_snapshots(
    baseline: dict[str, Any],
    fixture_summary: dict[str, Any],
    adjudication: dict[str, Any],
    scorer_triage: dict[str, Any],
    manifest_coverage: dict[str, Any],
    evidence: dict[str, Any],
    product_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    """Create versioned checkpoint rows for reviewable evaluator-health history."""

    public_safe_group = next(
        (
            group
            for group in fixture_summary["groups"]
            if group["trend_id"] == "public_safe_transcript_expansion"
        ),
        None,
    )
    dashboard = product_summary.get("product_kpis", [])
    triage = scorer_refinement_triage_outcomes(scorer_triage)
    return [
        {
            "checkpoint_id": "baseline_mock_run",
            "phase": "baseline",
            "source_paths": [display_path(BASELINE_TRACE_PATH)],
            "metrics": {
                "records": baseline["records"],
                "pass_rate": baseline["pass_rate"],
                "failure_modes": baseline["failure_modes"],
            },
        },
        {
            "checkpoint_id": "m40_evidence_quality_audit",
            "phase": "evidence_quality",
            "source_paths": [display_path(EVIDENCE_QUALITY_AUDIT_PATH)],
            "metrics": {
                "gap_count": evidence["gap_count"],
                "total_scored_records": baseline["records"] + fixture_summary["aggregate"]["records"],
                "product_kpi_count": len(dashboard),
            },
        },
        {
            "checkpoint_id": "m41_public_safe_transcript_expansion",
            "phase": "fixture_expansion",
            "source_paths": (
                [public_safe_group["source_path"], public_safe_group["trace_path"]]
                if public_safe_group
                else [display_path(FIXTURE_MANIFEST_PATH)]
            ),
            "metrics": (
                {
                    "records": public_safe_group["records"],
                    "pass_rate": public_safe_group["pass_rate"],
                    "failure_modes": public_safe_group["failure_modes"],
                }
                if public_safe_group
                else {"records": 0, "pass_rate": "0.0%", "failure_modes": {}}
            ),
        },
        {
            "checkpoint_id": "m42_scorer_calibration",
            "phase": "scorer_calibration",
            "source_paths": [display_path(SCORER_CALIBRATION_PATH)],
            "metrics": {
                "adjudication_records": adjudication["adjudication_records"],
                "changed_result_count": adjudication["changed_result_count"],
                "calibration_label_counts": adjudication["calibration_label_counts"],
            },
        },
        {
            "checkpoint_id": "m43_historical_trend_snapshot",
            "phase": "reporting_history",
            "source_paths": [display_path(JSON_OUTPUT_PATH), display_path(MARKDOWN_OUTPUT_PATH)],
            "metrics": {
                "report_artifacts": manifest_coverage["report_artifacts"],
                "json_snapshots": manifest_coverage["json_snapshots"],
                "markdown_reports": manifest_coverage["markdown_reports"],
                "fixture_groups": fixture_summary["counts"]["fixture_groups"],
                "external_fixture_pass_rate": fixture_summary["aggregate"]["pass_rate"],
            },
        },
        {
            "checkpoint_id": "m45_external_fixture_adjudication_coverage",
            "phase": "review_coverage",
            "source_paths": [
                display_path(ADJUDICATION_MANIFEST_PATH),
                display_path(ADJUDICATION_SNAPSHOT_PATH),
                display_path(SCORER_CALIBRATION_PATH),
            ],
            "metrics": {
                "adjudication_records": adjudication["adjudication_records"],
                "source_trace_count": adjudication["source_trace_count"],
                "external_source_trace_count": adjudication["reviewed_external_source_trace_count"],
                "ambiguous_reviews": adjudication["calibration_label_counts"].get("ambiguous_review", 0),
            },
        },
        {
            "checkpoint_id": "m46_needs_discussion_resolution",
            "phase": "review_resolution",
            "source_paths": [
                display_path(ADJUDICATION_MANIFEST_PATH),
                display_path(ADJUDICATION_SNAPSHOT_PATH),
                display_path(SCORER_CALIBRATION_PATH),
            ],
            "metrics": {
                "adjudication_records": adjudication["adjudication_records"],
                "needs_discussion": adjudication["reviewer_decisions"].get("needs_discussion", 0),
                "ambiguous_reviews": adjudication["calibration_label_counts"].get("ambiguous_review", 0),
                "changed_result_count": adjudication["changed_result_count"],
            },
        },
        {
            "checkpoint_id": "m47_deterministic_scorer_refinement_triage",
            "phase": "scorer_refinement_triage",
            "source_paths": [
                display_path(SCORER_REFINEMENT_TRIAGE_PATH),
                display_path(SCORER_CALIBRATION_PATH),
                display_path(SCORER_PATH),
            ],
            "metrics": {
                "candidates": triage["candidates"],
                "accepted_scorer_changes": triage["accepted_scorer_changes"],
                "deferred_scorer_changes": triage["deferred_scorer_changes"],
                "scorer_code_changed": triage["scorer_code_changed"],
            },
        },
        {
            "checkpoint_id": "m48_external_fixture_review_expansion",
            "phase": "review_expansion",
            "source_paths": [
                "traces/external/external_fixture_review_expansion.example.jsonl",
                display_path(ADJUDICATION_MANIFEST_PATH),
                display_path(ADJUDICATION_SNAPSHOT_PATH),
                display_path(SCORER_CALIBRATION_PATH),
                display_path(SCORER_REFINEMENT_TRIAGE_PATH),
            ],
            "metrics": {
                "adjudication_records": adjudication["adjudication_records"],
                "source_trace_count": adjudication["source_trace_count"],
                "external_source_trace_count": adjudication["reviewed_external_source_trace_count"],
                "accepted_scorer_changes": triage["accepted_scorer_changes"],
            },
        },
    ]


def trace_trend_point(trend_id: str, path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    """Create one deterministic pass/failure trend point from scored records."""

    if not records:
        raise HistoricalTrendSnapshotError(f"{display_path(path)} must not be empty")
    passed = count_passed(records)
    return {
        "trend_id": trend_id,
        "trace_path": display_path(path),
        "run_ids": unique_values(records, "run_id"),
        "timestamps": unique_values(records, "timestamp"),
        "records": len(records),
        "passed": passed,
        "failed": len(records) - passed,
        "pass_rate": percent(passed, len(records)),
        "failure_modes": sorted_dict(failure_mode_counts(records)),
    }


def generate_markdown(snapshot: dict[str, Any]) -> str:
    """Generate the reader-facing historical trend report."""

    current = snapshot["current_snapshot"]
    pass_rates = current["pass_rates"]
    adjudication = current["adjudication_outcomes"]
    manifest = current["report_manifest_coverage"]
    evidence = current["evidence_quality"]
    lines = [
        "# Historical Trend Report",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | ---: |",
        f"| Generated at | `{snapshot['generated_at']}` |",
        f"| Snapshot version | `{snapshot['snapshot_version']}` |",
        f"| Baseline pass rate | {pass_rates['baseline']['pass_rate']} |",
        f"| External fixture pass rate | {pass_rates['external_fixtures']['pass_rate']} |",
        f"| Adjudication records | {adjudication['adjudication_records']} |",
        f"| Report artifacts | {manifest['report_artifacts']} |",
        f"| Evidence gaps | {evidence['gap_count']} |",
        f"| Scorer triage candidates | {current['scorer_refinement_triage']['candidates']} |",
        "",
        "These trends describe evaluator health from committed local artifacts. They are not live model-performance trends, leaderboard results, or production benchmark claims.",
        "",
        "## Versioned Trend Snapshots",
        "",
        _checkpoint_table(snapshot["versioned_trend_snapshots"]),
        "",
        "## Pass Rates",
        "",
        _pass_rate_table(pass_rates),
        "",
        "## Failure Modes",
        "",
        _mapping_table(current["failure_modes"]["combined"], "Failure Mode"),
        "",
        "## Adjudication Outcomes",
        "",
        _mapping_table(adjudication["reviewer_decisions"], "Reviewer Decision"),
        "",
        "## Scorer Calibration Labels",
        "",
        _mapping_table(adjudication["calibration_label_counts"], "Calibration Label"),
        "",
        "## Report Manifest Coverage",
        "",
        _mapping_table(manifest, "Metric"),
        "",
        "## Boundary",
        "",
        "\n".join(f"- {item}" for item in snapshot["claim_boundary"]),
        "",
        "## Sources",
        "",
        "\n".join(f"- `{path}`" for path in snapshot["source_paths"]),
        "",
    ]
    return "\n".join(lines)


def _checkpoint_table(checkpoints: list[dict[str, Any]]) -> str:
    lines = [
        "| Checkpoint | Phase | Key Metrics |",
        "| --- | --- | --- |",
    ]
    for checkpoint in checkpoints:
        lines.append(
            f"| `{checkpoint['checkpoint_id']}` | `{checkpoint['phase']}` | "
            f"{_format_metrics(checkpoint['metrics'])} |"
        )
    return "\n".join(lines)


def _pass_rate_table(pass_rates: dict[str, Any]) -> str:
    lines = [
        "| Trend | Records | Passed | Failed | Pass Rate |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    baseline = pass_rates["baseline"]
    external = pass_rates["external_fixtures"]
    for point in [baseline, external, *pass_rates["fixture_groups"]]:
        lines.append(
            f"| `{point['trend_id']}` | {point['records']} | {point['passed']} | "
            f"{point['failed']} | {point['pass_rate']} |"
        )
    return "\n".join(lines)


def _mapping_table(mapping: dict[str, Any], label: str) -> str:
    lines = [
        f"| {label} | Value |",
        "| --- | ---: |",
    ]
    if not mapping:
        lines.append("| `none` | 0 |")
        return "\n".join(lines)
    for key in sorted(mapping):
        lines.append(f"| `{key}` | {mapping[key]} |")
    return "\n".join(lines)


def _format_metrics(metrics: dict[str, Any]) -> str:
    parts = []
    for key in sorted(metrics):
        value = metrics[key]
        if isinstance(value, dict):
            value = ", ".join(f"{inner_key}={value[inner_key]}" for inner_key in sorted(value)) or "none"
        parts.append(f"`{key}`={value}")
    return "; ".join(parts)


def load_required_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load a non-empty JSONL file."""

    if not path.exists():
        raise HistoricalTrendSnapshotError(f"{display_path(path)} does not exist")
    records = load_jsonl_records(path)
    if not records:
        raise HistoricalTrendSnapshotError(f"{display_path(path)} must not be empty")
    return records


def failure_mode_counts(records: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for record in records:
        for failure_mode in record.get("failure_modes", []):
            counts[str(failure_mode)] += 1
    return counts


def combined_failure_modes(first: dict[str, Any], second: dict[str, Any]) -> dict[str, int]:
    counts: Counter[str] = Counter({str(key): int(value) for key, value in first.items()})
    counts.update({str(key): int(value) for key, value in second.items()})
    return sorted_dict(counts)


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


def sorted_dict(counter: Counter[str] | dict[str, Any]) -> dict[str, Any]:
    return {key: counter[key] for key in sorted(counter)}


def sorted_mapping(mapping: Any) -> dict[str, Any]:
    if not isinstance(mapping, dict):
        return {}
    return {str(key): mapping[key] for key in sorted(mapping)}


def source_paths(fixture_groups: list[dict[str, Any]]) -> list[str]:
    paths = [
        BASELINE_TRACE_PATH,
        FIXTURE_MANIFEST_PATH,
        ADJUDICATION_MANIFEST_PATH,
        "traces/external/external_fixture_review_expansion.example.jsonl",
        ADJUDICATION_SNAPSHOT_PATH,
        SCORER_CALIBRATION_PATH,
        SCORER_REFINEMENT_TRIAGE_PATH,
        REPORT_MANIFEST_PATH,
        EVIDENCE_QUALITY_AUDIT_PATH,
        REPORTING_PRODUCT_SUMMARY_PATH,
    ]
    fixture_paths = []
    for group in fixture_groups:
        fixture_paths.append(str(group["source_path"]))
        fixture_paths.append(str(group["trace_path"]))
    return sorted({display_path(path) for path in paths} | set(fixture_paths))


def display_path(path: str | Path) -> str:
    path_value = Path(path)
    if not path_value.is_absolute():
        path_value = REPO_ROOT / path_value
    try:
        return str(path_value.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def main() -> int:
    try:
        snapshot = build_trend_snapshot()
        write_json_object(snapshot, JSON_OUTPUT_PATH)
        write_text(generate_markdown(snapshot), MARKDOWN_OUTPUT_PATH)
    except (OSError, ValueError, HistoricalTrendSnapshotError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    current = snapshot["current_snapshot"]
    print(f"historical trend JSON path: {display_path(JSON_OUTPUT_PATH)}")
    print(f"historical trend report path: {display_path(MARKDOWN_OUTPUT_PATH)}")
    print(f"baseline pass rate: {current['pass_rates']['baseline']['pass_rate']}")
    print(f"external fixture pass rate: {current['pass_rates']['external_fixtures']['pass_rate']}")
    print("historical trend snapshot generation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
