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
        ["python3", "src/inspect_failures.py"],
    ),
    (
        "manual output eval generation",
        ["python3", "src/evaluate_manual_outputs.py"],
    ),
    (
        "py_compile",
        [
            "python3",
            "-m",
            "py_compile",
            "src/model_clients.py",
            "src/scorers.py",
            "src/trace_writer.py",
            "src/run_eval.py",
            "src/report_generator.py",
            "src/comparison_report.py",
            "src/regression_check.py",
            "src/inspect_failures.py",
            "src/evaluate_manual_outputs.py",
            "src/validate_schemas.py",
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


def main() -> int:
    try:
        for name, command in CHECKS:
            run_check(name, command)
            if name == "mock eval generation":
                verify_trace_count(BASELINE_TRACE_PATH, EXPECTED_BASELINE_TRACE_LINES)
            if name == "manual output eval generation":
                verify_trace_count(MANUAL_TRACE_PATH, EXPECTED_MANUAL_TRACE_LINES)
    except (subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    print("local quality gate passed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
