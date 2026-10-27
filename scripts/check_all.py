"""Check the public portfolio evaluator using saved synthetic fixtures only."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE = REPO_ROOT / "evals/benchmarks/local_public_v1/cases.jsonl"
BASELINE_SHA256 = "366ca2f65991f9fbecffa15104e11b1b0f5c1e3f236eee947e00ed209f5891bb"


def check_cli(mode: str, fixture: str, expected: tuple[int, int, int], temporary: Path) -> None:
    """Check exit codes and summary artifacts through the Action's existing CLI."""

    for limit, exit_code in [(0, 1), (2, 0)]:
        summary_path = temporary / f"{mode}-{limit}.json"
        markdown_path = temporary / f"{mode}-{limit}.md"
        command = [
            sys.executable, "src/gate_check.py", "--mode", mode,
            "--outputs", fixture, "--max-failures", str(limit),
            "--summary-json", str(summary_path),
            "--summary-markdown", str(markdown_path),
        ]
        result = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
        if result.returncode != exit_code:
            raise RuntimeError(f"{mode} CLI returned {result.returncode}, expected {exit_code}: {result.stderr}")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        actual = tuple(summary[name] for name in ("scored_count", "pass_count", "fail_count"))
        if actual != expected or summary["gate_passed"] != (exit_code == 0):
            raise RuntimeError(f"{mode} summary changed: {actual}, expected {expected}")
        if not markdown_path.read_text(encoding="utf-8").strip():
            raise RuntimeError(f"{mode} Markdown summary is empty")
    print(f"{mode} CLI: {expected[0]} records, {expected[1]} pass, {expected[2]} fail; thresholds verified")


def main() -> int:
    """Run focused tests, preserve the public baseline, then verify both CLI modes."""

    if hashlib.sha256(BASELINE.read_bytes()).hexdigest() != BASELINE_SHA256:
        raise RuntimeError("The frozen public baseline changed")
    if len(BASELINE.read_text(encoding="utf-8").splitlines()) != 210:
        raise RuntimeError("The public baseline must contain 210 records")
    sys.path.insert(0, str(REPO_ROOT))
    suite = unittest.defaultTestLoader.discover(str(REPO_ROOT / "tests"))
    count = suite.countTestCases()
    if count < 193:
        raise RuntimeError(f"Expected at least 193 focused tests, found {count}")
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        return 1
    with tempfile.TemporaryDirectory(prefix="portfolio-gate-") as directory:
        temporary = Path(directory)
        check_cli("benchmark", "examples/github-action/agent_outputs.jsonl", (6, 4, 2), temporary)
        check_cli("trace", "examples/byo-trace/agent_trace.jsonl", (4, 2, 2), temporary)
    print(f"Public portfolio gate passed: {count} focused tests and both saved-fixture CLI modes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
