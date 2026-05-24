"""Run the local v0 quality gate for the eval harness.

This script uses only local standard-library subprocess calls. It does not call
real model APIs, perform network requests, execute OpenClaw, or trigger browser,
email, or other external actions.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_TRACE_PATH = REPO_ROOT / "traces/scored/baseline_mock_run.jsonl"
EXPECTED_BASELINE_TRACE_LINES = 90
MANUAL_TRACE_PATH = REPO_ROOT / "traces/scored/manual_output_eval.jsonl"
EXPECTED_MANUAL_TRACE_LINES = 4
OPENCLAW_MANUAL_TRACE_PATH = REPO_ROOT / "traces/scored/openclaw_manual_eval.jsonl"
EXPECTED_OPENCLAW_MANUAL_TRACE_LINES = 6
SAVED_TRANSCRIPT_TRACE_PATH = REPO_ROOT / "traces/scored/saved_transcript_replay_eval.jsonl"
EXPECTED_SAVED_TRANSCRIPT_TRACE_LINES = 5
ADAPTER_OUTPUT_TRACE_PATH = REPO_ROOT / "traces/scored/adapter_output_fixture_import.jsonl"
EXPECTED_ADAPTER_OUTPUT_TRACE_LINES = 4
DRY_RUN_ADAPTER_OUTPUT_PATH = REPO_ROOT / "traces/external/dry_run_adapter_outputs.jsonl"
EXPECTED_DRY_RUN_ADAPTER_OUTPUT_LINES = 4
DRY_RUN_ADAPTER_TRACE_PATH = REPO_ROOT / "traces/scored/dry_run_adapter_output_import.jsonl"
EXPECTED_DRY_RUN_ADAPTER_TRACE_LINES = 4
EXTERNAL_FIXTURE_COMPARISON_REPORT_PATH = REPO_ROOT / "reports/comparisons/external_fixture_comparison_report.md"
BASELINE_SELF_COMPARISON_REPORT_PATH = REPO_ROOT / "reports/comparisons/baseline_self_comparison_report.md"
ADJUDICATION_SUMMARY_REPORT_PATH = REPO_ROOT / "reports/comparisons/adjudication_summary_report.md"
ADJUDICATED_AGGREGATE_REPORT_PATH = REPO_ROOT / "reports/comparisons/adjudicated_aggregate_report.md"
ADJUDICATION_REGRESSION_SNAPSHOT_PATH = REPO_ROOT / "reports/comparisons/adjudication_regression_snapshot.json"
OPENCLAW_MANUAL_REPORT_CONTEXT = (
    "This public-safe sample treats sanitized OpenClaw-inspired outputs as one system under test. "
    "The records are fictional examples based on behavior principles such as approval gates, safe stopping, "
    "uncertainty handling, refusal boundaries, no fabricated tool use, and no fake completion claims; "
    "no live execution or private runtime data is used."
)

CHECKS = [
    (
        "unit tests",
        ["python3", "-m", "unittest", "discover", "-s", "tests"],
    ),
    (
        "schema validation",
        ["python3", "src/validate_schemas.py"],
    ),
    (
        "target registry validation",
        ["python3", "src/target_registry.py"],
    ),
    (
        "adapter output fixture validation",
        ["python3", "src/validate_adapter_outputs.py", "traces/external/adapter_outputs.example.jsonl"],
    ),
    (
        "adapter output fixture import",
        ["python3", "src/import_adapter_outputs.py", "traces/external/adapter_outputs.example.jsonl"],
    ),
    (
        "dry-run adapter generation",
        ["python3", "src/dry_run_adapter.py"],
    ),
    (
        "dry-run adapter output validation",
        ["python3", "src/validate_adapter_outputs.py", "traces/external/dry_run_adapter_outputs.jsonl"],
    ),
    (
        "dry-run adapter output import",
        [
            "python3",
            "src/import_adapter_outputs.py",
            "traces/external/dry_run_adapter_outputs.jsonl",
            "traces/scored/dry_run_adapter_output_import.jsonl",
        ],
    ),
    (
        "mock eval generation",
        ["python3", "src/run_eval.py"],
    ),
    (
        "report generation",
        ["python3", "src/report_generator.py"],
    ),
    (
        "comparison report generation",
        ["python3", "src/comparison_report.py"],
    ),
    (
        "regression snapshot check",
        ["python3", "src/regression_check.py"],
    ),
    (
        "failure inspection generation",
        [
            "python3",
            "src/inspect_failures.py",
            "--adjudication-manifest",
            "traces/external/adjudication_manifest.json",
        ],
    ),
    (
        "manual output eval generation",
        ["python3", "src/evaluate_manual_outputs.py"],
    ),
    (
        "openclaw-style manual eval generation",
        [
            "python3",
            "src/evaluate_manual_outputs.py",
            "--input",
            "traces/external/openclaw_manual_samples.example.jsonl",
            "--output",
            "traces/scored/openclaw_manual_eval.jsonl",
            "--report",
            "reports/comparisons/openclaw_manual_eval_report.md",
            "--run-id",
            "openclaw_manual_eval_example",
            "--report-title",
            "Public OpenClaw-Style Manual Evaluation Report",
            "--report-context",
            OPENCLAW_MANUAL_REPORT_CONTEXT,
        ],
    ),
    (
        "saved transcript replay generation",
        ["python3", "src/replay_saved_transcripts.py"],
    ),
    (
        "external fixture comparison report generation",
        ["python3", "src/compare_external_fixtures.py"],
    ),
    (
        "fixture manifest validation",
        ["python3", "src/validate_fixture_manifest.py"],
    ),
    (
        "adapter run metadata validation",
        ["python3", "src/validate_adapter_run_metadata.py"],
    ),
    (
        "adjudication validation",
        ["python3", "src/validate_adjudications.py"],
    ),
    (
        "followup adjudication validation",
        ["python3", "src/validate_adjudications.py", "traces/external/adjudications.followup.example.jsonl"],
    ),
    (
        "adjudication report generation",
        ["python3", "src/adjudication_report.py", "--manifest", "traces/external/adjudication_manifest.json"],
    ),
    (
        "adjudication regression snapshot check",
        [
            "python3",
            "src/adjudication_regression_check.py",
            "--manifest",
            "traces/external/adjudication_manifest.json",
        ],
    ),
    (
        "baseline self trace comparison",
        [
            "python3",
            "src/compare_scored_traces.py",
            "--before",
            "traces/scored/baseline_mock_run.jsonl",
            "--after",
            "traces/scored/baseline_mock_run.jsonl",
            "--output",
            "reports/comparisons/baseline_self_comparison_report.md",
            "--title",
            "Baseline Self Comparison Report",
        ],
    ),
    (
        "py_compile",
        [
            "python3",
            "-m",
            "py_compile",
            "src/model_clients.py",
            "src/target_registry.py",
            "src/scorers.py",
            "src/trace_writer.py",
            "src/reporting_utils.py",
            "src/run_eval.py",
            "src/report_generator.py",
            "src/comparison_report.py",
            "src/regression_check.py",
            "src/inspect_failures.py",
            "src/evaluate_manual_outputs.py",
            "src/replay_saved_transcripts.py",
            "src/validate_schemas.py",
            "src/validate_adapter_outputs.py",
            "src/import_adapter_outputs.py",
            "src/dry_run_adapter.py",
            "src/compare_external_fixtures.py",
            "src/validate_fixture_manifest.py",
            "src/validate_adapter_run_metadata.py",
            "src/collect_text_only_outputs.py",
            "src/review_text_only_outputs.py",
            "src/promote_reviewed_outputs.py",
            "src/validate_adjudications.py",
            "src/adjudication_report.py",
            "src/adjudication_regression_check.py",
            "src/compare_scored_traces.py",
        ],
    ),
]


def run_check(name: str, command: list[str]) -> None:
    """Run one quality-gate command and raise on failure."""

    print(f"==> {name}", flush=True)
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def verify_trace_count(path: Path, expected_lines: int) -> None:
    """Verify a generated scored trace exists and has the expected length."""

    print("==> trace count verification", flush=True)
    if not path.exists():
        raise RuntimeError(f"missing trace file: {path.relative_to(REPO_ROOT)}")

    with path.open("r", encoding="utf-8") as trace_file:
        line_count = sum(1 for _ in trace_file)

    if line_count != expected_lines:
        raise RuntimeError(
            f"expected {expected_lines} trace lines, found {line_count} in {path.relative_to(REPO_ROOT)}"
        )

    print(f"{path.relative_to(REPO_ROOT)} trace lines: {line_count}", flush=True)


def verify_jsonl_count(path: Path, expected_lines: int) -> None:
    """Verify a generated JSONL file exists and has the expected length."""

    print("==> JSONL count verification", flush=True)
    if not path.exists():
        raise RuntimeError(f"missing JSONL file: {path.relative_to(REPO_ROOT)}")

    with path.open("r", encoding="utf-8") as jsonl_file:
        line_count = sum(1 for _ in jsonl_file)

    if line_count != expected_lines:
        raise RuntimeError(
            f"expected {expected_lines} JSONL lines, found {line_count} in {path.relative_to(REPO_ROOT)}"
        )

    print(f"{path.relative_to(REPO_ROOT)} JSONL lines: {line_count}", flush=True)


def verify_report_exists(path: Path) -> None:
    """Verify a generated report exists and is non-empty."""

    print("==> report verification", flush=True)
    if not path.exists():
        raise RuntimeError(f"missing report file: {path.relative_to(REPO_ROOT)}")
    if path.stat().st_size == 0:
        raise RuntimeError(f"empty report file: {path.relative_to(REPO_ROOT)}")
    print(f"{path.relative_to(REPO_ROOT)} exists", flush=True)


def main() -> int:
    try:
        for name, command in CHECKS:
            run_check(name, command)
            if name == "adapter output fixture import":
                verify_trace_count(ADAPTER_OUTPUT_TRACE_PATH, EXPECTED_ADAPTER_OUTPUT_TRACE_LINES)
            if name == "dry-run adapter generation":
                verify_jsonl_count(DRY_RUN_ADAPTER_OUTPUT_PATH, EXPECTED_DRY_RUN_ADAPTER_OUTPUT_LINES)
            if name == "dry-run adapter output import":
                verify_trace_count(DRY_RUN_ADAPTER_TRACE_PATH, EXPECTED_DRY_RUN_ADAPTER_TRACE_LINES)
            if name == "mock eval generation":
                verify_trace_count(BASELINE_TRACE_PATH, EXPECTED_BASELINE_TRACE_LINES)
            if name == "manual output eval generation":
                verify_trace_count(MANUAL_TRACE_PATH, EXPECTED_MANUAL_TRACE_LINES)
            if name == "openclaw-style manual eval generation":
                verify_trace_count(OPENCLAW_MANUAL_TRACE_PATH, EXPECTED_OPENCLAW_MANUAL_TRACE_LINES)
            if name == "saved transcript replay generation":
                verify_trace_count(SAVED_TRANSCRIPT_TRACE_PATH, EXPECTED_SAVED_TRANSCRIPT_TRACE_LINES)
            if name == "external fixture comparison report generation":
                verify_report_exists(EXTERNAL_FIXTURE_COMPARISON_REPORT_PATH)
            if name == "adjudication report generation":
                verify_report_exists(ADJUDICATION_SUMMARY_REPORT_PATH)
                verify_report_exists(ADJUDICATED_AGGREGATE_REPORT_PATH)
            if name == "adjudication regression snapshot check":
                verify_report_exists(ADJUDICATION_REGRESSION_SNAPSHOT_PATH)
            if name == "baseline self trace comparison":
                verify_report_exists(BASELINE_SELF_COMPARISON_REPORT_PATH)
    except (subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    print("local quality gate passed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
