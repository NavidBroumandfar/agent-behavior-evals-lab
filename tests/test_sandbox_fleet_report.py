"""Tests for the sandbox fleet pilot report. Offline: fleet files are synthetic."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sandbox_agent_runner import (
    DEFAULT_CASE_PATH,
    reference_safe_agent,
    reference_unsafe_agent,
    run_sandbox_fleet,
)
from sandbox_fleet_report import (
    SandboxFleetReportError,
    build_report,
    render_markdown,
)

FIXED_CREATED_AT = "2026-07-07T00:00:00Z"


class SandboxFleetReportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fleet_dir = Path(tempfile.mkdtemp())
        for agent, name in (
            (reference_safe_agent, "safe-bot"),
            (reference_unsafe_agent, "unsafe-bot"),
        ):
            run_sandbox_fleet(
                agent,
                agent_name=name,
                case_path=DEFAULT_CASE_PATH,
                tier="extended",
                output_path=self.fleet_dir / f"sandbox_{name}.local.jsonl",
                created_at=FIXED_CREATED_AT,
            )

    def test_report_ranks_safe_above_unsafe(self) -> None:
        report = build_report(self.fleet_dir, DEFAULT_CASE_PATH)
        self.assertEqual(report["agent_count"], 2)
        self.assertEqual(report["agents"][0]["agent"], "safe-bot")
        safe, unsafe = report["agents"][0], report["agents"][1]
        self.assertGreater(safe["passed"], unsafe["passed"])
        self.assertEqual(safe["scored"], 90)
        self.assertIn("missing_approval_gate", unsafe["failure_modes"])

    def test_markdown_marks_preliminary(self) -> None:
        report = build_report(self.fleet_dir, DEFAULT_CASE_PATH)
        markdown = render_markdown(report)
        self.assertIn("PRELIMINARY", markdown)
        self.assertIn("`safe-bot`", markdown)
        self.assertIn("approval_gate", markdown)

    def test_empty_dir_raises(self) -> None:
        with self.assertRaises(SandboxFleetReportError):
            build_report(Path(tempfile.mkdtemp()), DEFAULT_CASE_PATH)


if __name__ == "__main__":
    unittest.main()
