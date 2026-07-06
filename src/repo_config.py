"""Shared repository paths for the public evaluator core.

Single source of truth for the repo root and the canonical eval case set.
Modules with additional module-specific paths keep those locally.
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

CASE_PATHS = [
    REPO_ROOT / "evals/cases/safe_task_cases.jsonl",
    REPO_ROOT / "evals/cases/approval_gate_cases.jsonl",
    REPO_ROOT / "evals/cases/refusal_cases.jsonl",
    REPO_ROOT / "evals/cases/uncertainty_cases.jsonl",
]

BASELINE_TRACE_PATH = REPO_ROOT / "traces/scored/baseline_mock_run.jsonl"
