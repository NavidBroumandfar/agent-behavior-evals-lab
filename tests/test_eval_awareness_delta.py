"""Tests for the eval-awareness delta report (E2).

Offline and deterministic. The framing knob and the delta arithmetic are
exercised with the scripted reference agents; no live models. These tests do
not assert any real-model behavior — they verify the mechanism computes and
renders a gap and stays honest when no paired evidence exists.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from eval_awareness_delta import build_report, discover_pairs, render_markdown  # noqa: E402
from sandbox_agent_runner import (  # noqa: E402
    DEFAULT_CASE_PATH,
    FRAMINGS,
    SandboxRunnerError,
    reference_safe_agent,
    reference_unsafe_agent,
    run_sandbox_fleet,
)

FIXED_CREATED_AT = "2026-07-08T00:00:00Z"


def _write(fleet_dir: Path, label: str, suffix: str, agent, name: str, framing: str) -> None:
    run_sandbox_fleet(
        agent,
        agent_name=name,
        case_path=DEFAULT_CASE_PATH,
        tier="extended",
        output_path=fleet_dir / f"sandbox_{label}{suffix}",
        created_at=FIXED_CREATED_AT,
        framing=framing,
    )


class FramingKnobTest(unittest.TestCase):
    def test_eval_framing_prepends_and_is_recorded(self) -> None:
        out = Path(tempfile.mkdtemp()) / "run.jsonl"
        run_sandbox_fleet(
            reference_safe_agent,
            agent_name="safe",
            case_path=DEFAULT_CASE_PATH,
            tier="smoke",
            output_path=out,
            created_at=FIXED_CREATED_AT,
            framing="eval",
        )
        import json
        records = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
        self.assertTrue(records)
        for r in records:
            self.assertEqual(r["metadata"]["sandbox_run"]["framing"], "eval")

    def test_production_is_the_default(self) -> None:
        self.assertEqual(FRAMINGS["production"], "")

    def test_unknown_framing_rejected(self) -> None:
        with self.assertRaises(SandboxRunnerError):
            run_sandbox_fleet(
                reference_safe_agent,
                agent_name="safe",
                tier="smoke",
                output_path=Path(tempfile.mkdtemp()) / "x.jsonl",
                framing="nope",
            )


class DeltaReportTest(unittest.TestCase):
    def test_pending_when_no_pairs(self) -> None:
        report = build_report(Path(tempfile.mkdtemp()), DEFAULT_CASE_PATH)
        self.assertEqual(report["measurement_status"], "pending_live_runs")
        self.assertEqual(report["config_count"], 0)
        self.assertIn("runbook", report)
        self.assertIn("pending_live_runs", render_markdown(report))

    def test_computes_gap_from_a_paired_config(self) -> None:
        fleet = Path(tempfile.mkdtemp())
        # Synthetic pair: safe agent as the "eval-framed" side (high pass), unsafe
        # agent as the "production-shaped" side (low pass) -> a large positive gap.
        # This tests arithmetic/discovery/rendering, not real model behavior.
        _write(fleet, "cfg", ".eval_framed.reviewed_sandbox_outputs.jsonl",
               reference_safe_agent, "safe", "eval")
        _write(fleet, "cfg", ".prod_shaped.reviewed_sandbox_outputs.jsonl",
               reference_unsafe_agent, "unsafe", "production")
        self.assertEqual(discover_pairs(fleet), ["cfg"])
        report = build_report(fleet, DEFAULT_CASE_PATH)
        self.assertEqual(report["measurement_status"], "measured")
        self.assertEqual(report["config_count"], 1)
        cfg = report["configs"][0]
        self.assertEqual(cfg["config"], "cfg")
        self.assertGreater(cfg["eval_framed"]["pass_rate_pct"], cfg["production_shaped"]["pass_rate_pct"])
        self.assertGreater(cfg["eval_awareness_gap_pct"], 0)
        self.assertEqual(
            cfg["eval_awareness_gap_pct"],
            round(cfg["eval_framed"]["pass_rate_pct"] - cfg["production_shaped"]["pass_rate_pct"], 1),
        )
        md = render_markdown(report)
        self.assertIn("| `cfg` |", md)
        self.assertIn("pp", md)

    def test_unpaired_file_is_not_measured(self) -> None:
        fleet = Path(tempfile.mkdtemp())
        _write(fleet, "solo", ".eval_framed.reviewed_sandbox_outputs.jsonl",
               reference_safe_agent, "safe", "eval")
        self.assertEqual(discover_pairs(fleet), [])
        self.assertEqual(build_report(fleet, DEFAULT_CASE_PATH)["measurement_status"], "pending_live_runs")


class PairedCaseComparisonTest(unittest.TestCase):
    """A partial run must not have its coverage gap read as an eval-awareness gap."""

    def test_gap_uses_only_cases_present_in_both_framings(self) -> None:
        from eval_awareness_delta import _stats_for

        eval_passed = {"a": True, "b": False, "c": True}
        prod_passed = {"a": False, "b": False}
        paired = sorted(set(eval_passed) & set(prod_passed))

        self.assertEqual(paired, ["a", "b"])
        self.assertEqual(_stats_for(eval_passed, paired)["scored"], 2)
        self.assertEqual(_stats_for(prod_passed, paired)["scored"], 2)
        # "c" exists only under the eval framing and must not inflate the gap.
        self.assertEqual(_stats_for(eval_passed, paired)["pass_rate_pct"], 50.0)
        self.assertEqual(_stats_for(prod_passed, paired)["pass_rate_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
