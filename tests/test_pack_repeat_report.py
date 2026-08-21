"""Guards for the run-to-run reproducibility report.

Offline and deterministic: every case builds its own tiny pack and run directories under
a temp dir, so nothing here depends on a live model, a gateway, or the held-out corpora.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pack_repeat_report as prr


def _write_pack(root: Path) -> Path:
    pack = root / "evals" / "benchmarks" / "toy_pack"
    pack.mkdir(parents=True)
    cases = [
        {"case_id": "TOY-001", "kind": "temptation", "user_prompt": "x",
         "scoring": {"violating_calls": [{"tool": "bad"}], "required_calls": [],
                     "expected_safe_signal": "escalation_required"}},
        {"case_id": "TOY-002", "kind": "honest_control", "user_prompt": "y",
         "scoring": {"violating_calls": [], "required_calls": [{"tool": "good"}],
                     "expected_safe_signal": "action_required"}},
    ]
    (pack / "cases.jsonl").write_text(
        "\n".join(json.dumps(c) for c in cases) + "\n", encoding="utf-8")
    return pack


def _write_run(run_dir: Path, *, violate: bool) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        {"case_id": "TOY-001",
         "tool_events": ([{"tool_name": "bad", "action": "did it", "status": "succeeded"}]
                         if violate else [])},
        {"case_id": "TOY-002",
         "tool_events": [{"tool_name": "good", "action": "ok", "status": "succeeded"}]},
    ]
    (run_dir / "toy_pack__m1.local.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    # an error sidecar must never be read as a run log
    (run_dir / "toy_pack__m1.errors.local.jsonl").write_text(
        json.dumps({"case_id": "TOY-003", "error": "transport"}) + "\n", encoding="utf-8")


class PackRepeatReportTests(unittest.TestCase):
    def _fixture(self, tmp: Path, *, second_run_violates: bool):
        pack = _write_pack(tmp)
        a, b = tmp / "runA", tmp / "runB"
        _write_run(a, violate=True)
        _write_run(b, violate=second_run_violates)
        collected = prr.collect("toy_pack", [a, b])
        # collect() resolves the pack by slug under REPO_ROOT, so point it at ours
        return pack, a, b, collected

    def test_identical_runs_report_a_zero_flip_rate(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            pack = _write_pack(tmp)
            a, b = tmp / "runA", tmp / "runB"
            _write_run(a, violate=True)
            _write_run(b, violate=True)
            orig = prr._pack_dir
            prr._pack_dir = lambda _slug: pack
            try:
                analysis = prr.analyse(prr.collect("toy_pack", [a, b]))
            finally:
                prr._pack_dir = orig
            row = next(r for r in analysis["rows"] if r["model"] == "m1")
            self.assertTrue(row["scored"])
            self.assertEqual(row["cases_flipped"], 0)
            self.assertEqual(row["flip_rate"], 0.0)

    def test_a_changed_verdict_is_counted_and_named(self) -> None:
        """The guard must actually move when a verdict moves."""

        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            pack = _write_pack(tmp)
            a, b = tmp / "runA", tmp / "runB"
            _write_run(a, violate=True)
            _write_run(b, violate=False)
            orig = prr._pack_dir
            prr._pack_dir = lambda _slug: pack
            try:
                analysis = prr.analyse(prr.collect("toy_pack", [a, b]))
            finally:
                prr._pack_dir = orig
            row = next(r for r in analysis["rows"] if r["model"] == "m1")
            self.assertEqual(row["cases_flipped"], 1)
            self.assertIn("TOY-001", row["flipped_case_ids"])
            self.assertGreater(row["flip_rate"], 0.0)
            self.assertGreater(row["safety_range"], 0.0)

    def test_a_single_run_is_reported_unmeasurable_not_as_zero(self) -> None:
        """One run must never be published as perfect reproducibility."""

        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            pack = _write_pack(tmp)
            a = tmp / "runA"
            _write_run(a, violate=True)
            orig = prr._pack_dir
            prr._pack_dir = lambda _slug: pack
            try:
                analysis = prr.analyse(prr.collect("toy_pack", [a]))
            finally:
                prr._pack_dir = orig
            row = next(r for r in analysis["rows"] if r["model"] == "m1")
            self.assertFalse(row["scored"])
            self.assertNotIn("flip_rate", row)
            self.assertIn("not measurable", row["note"])

    def test_error_sidecars_are_not_scored_as_runs(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            pack = _write_pack(tmp)
            a, b = tmp / "runA", tmp / "runB"
            _write_run(a, violate=True)
            _write_run(b, violate=True)
            orig = prr._pack_dir
            prr._pack_dir = lambda _slug: pack
            try:
                collected = prr.collect("toy_pack", [a, b])
            finally:
                prr._pack_dir = orig
            self.assertEqual(sorted(collected), ["m1"])

    def test_cli_refuses_a_single_run_directory(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            _write_pack(tmp)
            a = tmp / "runA"
            _write_run(a, violate=True)
            rc = prr.main(["--pack", "toy_pack", "--run", str(a)])
            self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
