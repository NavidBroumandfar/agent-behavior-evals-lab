"""Generate deterministic release notes from committed reporting artifacts.

This release-note layer converts the product summary and milestone closeouts
into a release-ready JSON snapshot and Markdown report. It reads local
committed artifacts only. It does not collect outputs, rescore traces, call
providers, run models, execute agents, inspect private logs, use networks, or
perform external actions.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from reporting_utils import load_json_object, write_json_object, write_text


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-21T00:00:00Z"

PRODUCT_SUMMARY_PATH = REPO_ROOT / "reports/comparisons/reporting_product_summary.json"
REPORT_MANIFEST_PATH = REPO_ROOT / "reports/comparisons/report_manifest.json"
ROADMAP_PATH = REPO_ROOT / "docs/roadmap.md"

MILESTONE_PATHS = [
    REPO_ROOT / "docs/milestones/m35-openclaw-saved-transcript-pilot-closeout.md",
    REPO_ROOT / "docs/milestones/m36-controlled-live-agent-sandbox-closeout.md",
    REPO_ROOT / "docs/milestones/m37-optional-harness-integration-decision-closeout.md",
    REPO_ROOT / "docs/milestones/m38-reporting-product-layer-closeout.md",
    REPO_ROOT / "docs/milestones/m39-release-notes-reporting-closeout.md",
    REPO_ROOT / "docs/milestones/m40-evidence-quality-audit-closeout.md",
    REPO_ROOT / "docs/milestones/m41-public-safe-transcript-expansion-closeout.md",
    REPO_ROOT / "docs/milestones/m42-scorer-calibration-closeout.md",
    REPO_ROOT / "docs/milestones/m43-historical-trend-snapshots-closeout.md",
    REPO_ROOT / "docs/milestones/m44-optional-non-gated-runtime-trial-closeout.md",
    REPO_ROOT / "docs/milestones/m45-external-fixture-adjudication-coverage-closeout.md",
    REPO_ROOT / "docs/milestones/m46-needs-discussion-resolution-closeout.md",
    REPO_ROOT / "docs/milestones/m47-deterministic-scorer-refinement-triage-closeout.md",
    REPO_ROOT / "docs/milestones/m48-external-fixture-review-expansion-closeout.md",
    REPO_ROOT / "docs/milestones/m49-scorer-candidate-control-tests-closeout.md",
    REPO_ROOT / "docs/milestones/m50-deterministic-scorer-change-decision-closeout.md",
    REPO_ROOT / "docs/milestones/m51-scorer-versioning-guardrails-closeout.md",
    REPO_ROOT / "docs/milestones/m52-focused-scorer-evidence-expansion-closeout.md",
    REPO_ROOT / "docs/milestones/m53-scorer-promotion-or-rubric-update-closeout.md",
    REPO_ROOT / "docs/milestones/m54-local-benchmark-claim-charter-closeout.md",
]

JSON_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/release_notes_latest.json"
MARKDOWN_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/release_notes_latest.md"


class ReleaseNotesSummaryError(Exception):
    """Release notes summary generation error."""


def build_release_notes() -> dict[str, Any]:
    """Build the deterministic release-notes JSON snapshot."""

    product_summary = load_json_object(PRODUCT_SUMMARY_PATH)
    report_manifest = load_json_object(REPORT_MANIFEST_PATH)
    milestones = [milestone_summary(path) for path in MILESTONE_PATHS]
    report_artifacts = report_manifest.get("report_artifacts", [])
    if not isinstance(report_artifacts, list) or not report_artifacts:
        raise ReleaseNotesSummaryError("report manifest must contain report_artifacts")

    dashboard = dashboard_snapshot(product_summary)
    return {
        "release_id": "release_notes_latest",
        "generated_at": GENERATED_AT,
        "title": "Agent Behavior Evals Lab Release Notes",
        "source_paths": [
            display_path(PRODUCT_SUMMARY_PATH),
            display_path(REPORT_MANIFEST_PATH),
            display_path(ROADMAP_PATH),
            *[display_path(path) for path in MILESTONE_PATHS],
        ],
        "safety": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
            "credentials_required": False,
        },
        "quality_gate": {
            "command": "python3 scripts/dev.py check",
            "deterministic_local_only": True,
            "live_execution": False,
            "report_artifacts_indexed": len(report_artifacts),
            "markdown_reports": count_artifacts(report_artifacts, "markdown_report"),
            "json_snapshots": count_artifacts(report_artifacts, "json_snapshot"),
        },
        "dashboard_snapshot": dashboard,
        "milestones": milestones,
        "highlights": release_highlights(product_summary, dashboard, milestones),
        "release_readiness": {
            "status": "local_quality_gate_ready",
            "summary": "The release notes summarize committed local artifacts and preserve the no-live-execution boundary.",
            "next_step": "Use the release notes as the reader-facing handoff for the completed local roadmap extension.",
        },
        "boundaries": [
            "No live provider APIs or provider SDKs.",
            "No local model execution.",
            "No live Hermes, OpenClaw, CLI-agent, browser, email, shell, network, or external-action execution.",
            "No credentials, secrets, private runtime logs, private memory, or private workspace paths.",
            "No leaderboard or production benchmark claims.",
        ],
    }


def milestone_summary(path: Path) -> dict[str, str]:
    """Extract a small summary from one milestone closeout document."""

    if not path.exists():
        raise ReleaseNotesSummaryError(f"{display_path(path)} does not exist")
    lines = path.read_text(encoding="utf-8").splitlines()
    title = first_prefixed_value(lines, "# ")
    status = first_prefixed_value(lines, "Status:")
    date = first_prefixed_value(lines, "Date:")
    if not title:
        raise ReleaseNotesSummaryError(f"{display_path(path)} missing title")
    return {
        "milestone_id": title.split(" - ", 1)[0].replace("Milestone ", "M"),
        "title": title,
        "date": date,
        "status": status,
        "path": display_path(path),
    }


def first_prefixed_value(lines: list[str], prefix: str) -> str:
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return ""


def dashboard_snapshot(product_summary: dict[str, Any]) -> dict[str, Any]:
    """Extract release-note dashboard signals from the M38 product summary."""

    baseline = product_summary.get("baseline", {})
    external = product_summary.get("external_fixtures", {})
    adjudication = product_summary.get("adjudication", {})
    harness = product_summary.get("harness_bridge", {})
    return {
        "baseline_pass_rate": baseline.get("pass_rate", "0.0%"),
        "baseline_records": baseline.get("total_records", 0),
        "baseline_failed": baseline.get("failed", 0),
        "external_fixture_groups": external.get("fixture_groups", 0),
        "external_fixture_records": external.get("total_scored_records", 0),
        "adjudication_records": adjudication.get("adjudication_records", 0),
        "review_needs_discussion": adjudication.get("needs_discussion", 0),
        "harness_bridge_decision": harness.get("decision", "unknown"),
        "runtime_native_state_required": harness.get("runtime_native_state_required", False),
    }


def release_highlights(
    product_summary: dict[str, Any],
    dashboard: dict[str, Any],
    milestones: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Create concise release-note highlights."""

    release_view = product_summary.get("release_view", {})
    highlights = [
        {
            "area": "Reporting",
            "summary": "Maintains dashboard-ready JSON, product summary Markdown, release-note outputs, and report-manifest coverage from local artifacts.",
        },
        {
            "area": "Quality Gate",
            "summary": str(release_view.get("headline", "Local deterministic gate remains stable.")),
        },
        {
            "area": "Harness Boundary",
            "summary": (
                f"Harness decision remains {dashboard['harness_bridge_decision']}; "
                f"runtime-native state required is {str(dashboard['runtime_native_state_required']).lower()}."
            ),
        },
        {
            "area": "Review",
            "summary": (
                f"{dashboard['adjudication_records']} adjudication records are tracked; "
                f"{dashboard['review_needs_discussion']} still need discussion."
            ),
        },
    ]
    if any(milestone["milestone_id"] == "M40" for milestone in milestones):
        highlights.append(
            {
                "area": "Evidence Quality",
                "summary": "Added a deterministic evidence inventory and gap report for fixture, scorer, adjudication, and reporting coverage.",
            }
        )
    if any(milestone["milestone_id"] == "M41" for milestone in milestones):
        highlights.append(
            {
                "area": "Transcript Expansion",
                "summary": "Added synthetic public-safe saved transcripts covering task-following, approval, refusal, and uncertainty behavior.",
            }
        )
    if any(milestone["milestone_id"] == "M42" for milestone in milestones):
        highlights.append(
            {
                "area": "Scorer Calibration",
                "summary": "Added advisory calibration labels for scorer false positives, false negatives, ambiguous reviews, and upheld outcomes.",
            }
        )
    if any(milestone["milestone_id"] == "M43" for milestone in milestones):
        highlights.append(
            {
                "area": "Historical Trends",
                "summary": "Added versioned evaluator-health trend snapshots for pass rates, failure modes, adjudication outcomes, fixture counts, and report coverage.",
            }
        )
    if any(milestone["milestone_id"] == "M44" for milestone in milestones):
        highlights.append(
            {
                "area": "Runtime Trial",
                "summary": "Added a validation-only optional runtime-trial plan with manual, disposable, non-gated controls and a reviewed-output promotion path.",
            }
        )
    if any(milestone["milestone_id"] == "M45" for milestone in milestones):
        highlights.append(
            {
                "area": "External Fixture Review",
                "summary": "Added public-safe adjudication coverage for selected saved-transcript and normalized adapter-output scored traces.",
            }
        )
    if any(milestone["milestone_id"] == "M46" for milestone in milestones):
        highlights.append(
            {
                "area": "Review Resolution",
                "summary": "Resolved the remaining public-safe needs_discussion adjudications while keeping reviewer decisions separate from heuristic traces.",
            }
        )
    if any(milestone["milestone_id"] == "M47" for milestone in milestones):
        highlights.append(
            {
                "area": "Scorer Triage",
                "summary": "Recorded a no-change deterministic scorer decision and deferred refinement candidates until more focused evidence exists.",
            }
        )
    if any(milestone["milestone_id"] == "M48" for milestone in milestones):
        highlights.append(
            {
                "area": "Review Expansion",
                "summary": "Expanded public-safe adjudication coverage across previously unreviewed external fixture trace families.",
            }
        )
    if any(milestone["milestone_id"] == "M49" for milestone in milestones):
        highlights.append(
            {
                "area": "Scorer Controls",
                "summary": "Added focused deterministic controls for current scorer-refinement candidates without accepting scorer-code changes.",
            }
        )
    if any(milestone["milestone_id"] == "M50" for milestone in milestones):
        highlights.append(
            {
                "area": "Scorer Decision",
                "summary": "Recorded a durable no-change scorer decision from M49 controls while preserving historical adjudication context.",
            }
        )
    if any(milestone["milestone_id"] == "M51" for milestone in milestones):
        highlights.append(
            {
                "area": "Scorer Versioning",
                "summary": "Added optional historical scorer context validation so future scorer changes can preserve pre-change adjudication outcomes.",
            }
        )
    if any(milestone["milestone_id"] == "M52" for milestone in milestones):
        highlights.append(
            {
                "area": "Focused Scorer Evidence",
                "summary": "Added public-safe focused evidence for safe-task clarification and approval-disclosure scorer candidates without accepting scorer-code changes.",
            }
        )
    if any(milestone["milestone_id"] == "M53" for milestone in milestones):
        highlights.append(
            {
                "area": "Scorer Promotion",
                "summary": "Recorded a rubric-only approval-disclosure update while keeping deterministic scorer behavior and scored traces unchanged.",
            }
        )
    if any(milestone["milestone_id"] == "M54" for milestone in milestones):
        highlights.append(
            {
                "area": "Benchmark Claims",
                "summary": "Added an evidence-class claim charter that separates local benchmark, cloud benchmark, manual sample, private audit, promoted public evidence, and unsupported claims.",
            }
        )
    return highlights


def generate_markdown(release_notes: dict[str, Any]) -> str:
    """Generate the reader-facing release notes Markdown."""

    dashboard = release_notes["dashboard_snapshot"]
    quality_gate = release_notes["quality_gate"]
    lines = [
        "# Agent Behavior Evals Lab Release Notes",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Generated at | `{release_notes['generated_at']}` |",
        f"| Release ID | `{release_notes['release_id']}` |",
        f"| Quality gate command | `{quality_gate['command']}` |",
        f"| Indexed report artifacts | {quality_gate['report_artifacts_indexed']} |",
        f"| Baseline pass rate | {dashboard['baseline_pass_rate']} |",
        f"| Harness bridge decision | `{dashboard['harness_bridge_decision']}` |",
        "",
        "## Highlights",
        "",
        _highlights(release_notes["highlights"]),
        "",
        "## Dashboard Snapshot",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Baseline records | {dashboard['baseline_records']} |",
        f"| Baseline failed | {dashboard['baseline_failed']} |",
        f"| External fixture groups | {dashboard['external_fixture_groups']} |",
        f"| External fixture records | {dashboard['external_fixture_records']} |",
        f"| Adjudication records | {dashboard['adjudication_records']} |",
        f"| Review records needing discussion | {dashboard['review_needs_discussion']} |",
        "",
        "## Milestone Rollup",
        "",
        _milestone_table(release_notes["milestones"]),
        "",
        "## Boundaries",
        "",
        "\n".join(f"- {boundary}" for boundary in release_notes["boundaries"]),
        "",
        "## Sources",
        "",
        "\n".join(f"- `{path}`" for path in release_notes["source_paths"]),
        "",
    ]
    return "\n".join(lines)


def _highlights(highlights: list[dict[str, str]]) -> str:
    return "\n".join(f"- **{item['area']}**: {item['summary']}" for item in highlights)


def _milestone_table(milestones: list[dict[str, str]]) -> str:
    lines = [
        "| Milestone | Status | Closeout |",
        "| --- | --- | --- |",
    ]
    for milestone in milestones:
        lines.append(f"| `{milestone['milestone_id']}` | {milestone['status']} | `{milestone['path']}` |")
    return "\n".join(lines)


def count_artifacts(artifacts: list[dict[str, Any]], artifact_type: str) -> int:
    return sum(1 for artifact in artifacts if artifact.get("artifact_type") == artifact_type)


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def main() -> int:
    try:
        release_notes = build_release_notes()
        write_json_object(release_notes, JSON_OUTPUT_PATH)
        write_text(generate_markdown(release_notes), MARKDOWN_OUTPUT_PATH)
    except (OSError, ValueError, ReleaseNotesSummaryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"release notes JSON path: {display_path(JSON_OUTPUT_PATH)}")
    print(f"release notes report path: {display_path(MARKDOWN_OUTPUT_PATH)}")
    print(f"milestones summarized: {len(release_notes['milestones'])}")
    print(f"indexed report artifacts: {release_notes['quality_gate']['report_artifacts_indexed']}")
    print("release notes summary generation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
