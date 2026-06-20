import copy
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from historical_trend_snapshot import (  # noqa: E402
    HistoricalTrendSnapshotError,
    build_trend_snapshot,
    generate_markdown,
    trace_trend_point,
)


class HistoricalTrendSnapshotTests(unittest.TestCase):
    def test_build_trend_snapshot_uses_committed_local_artifacts(self):
        snapshot = build_trend_snapshot()

        self.assertEqual(snapshot["snapshot_id"], "m43_historical_trend_snapshot")
        self.assertEqual(snapshot["generated_at"], "2026-06-20T00:00:00Z")
        self.assertTrue(snapshot["safety"]["public_safe"])
        self.assertFalse(snapshot["safety"]["live_execution"])

        current = snapshot["current_snapshot"]
        self.assertEqual(current["pass_rates"]["baseline"]["records"], 126)
        self.assertEqual(current["pass_rates"]["baseline"]["pass_rate"], "91.3%")
        self.assertEqual(current["fixture_counts"]["fixture_groups"], 7)
        self.assertEqual(current["fixture_counts"]["scored_records"], 34)
        self.assertEqual(current["adjudication_outcomes"]["adjudication_records"], 12)
        self.assertEqual(current["adjudication_outcomes"]["changed_result_count"], 2)
        self.assertEqual(current["report_manifest_coverage"]["report_artifacts"], 24)
        self.assertEqual(current["report_manifest_coverage"]["json_snapshots"], 7)
        self.assertEqual(current["report_manifest_coverage"]["markdown_reports"], 17)

    def test_versioned_checkpoints_cover_recent_roadmap_phases(self):
        snapshot = build_trend_snapshot()
        checkpoint_ids = [item["checkpoint_id"] for item in snapshot["versioned_trend_snapshots"]]

        self.assertEqual(
            checkpoint_ids,
            [
                "baseline_mock_run",
                "m40_evidence_quality_audit",
                "m41_public_safe_transcript_expansion",
                "m42_scorer_calibration",
                "m43_historical_trend_snapshot",
            ],
        )

    def test_generate_markdown_contains_trend_sections_and_boundary(self):
        markdown = generate_markdown(build_trend_snapshot())

        self.assertIn("# Historical Trend Report", markdown)
        self.assertIn("## Versioned Trend Snapshots", markdown)
        self.assertIn("## Pass Rates", markdown)
        self.assertIn("## Scorer Calibration Labels", markdown)
        self.assertIn("not live model-performance trends", markdown)

    def test_trace_trend_point_counts_failure_modes(self):
        records = [
            {
                "run_id": "unit",
                "timestamp": "2026-06-20T00:00:00Z",
                "passed": True,
                "failure_modes": [],
            },
            {
                "run_id": "unit",
                "timestamp": "2026-06-20T00:00:00Z",
                "passed": False,
                "failure_modes": ["missing_approval_gate"],
            },
        ]

        point = trace_trend_point("unit", REPO_ROOT / "traces/scored/unit.jsonl", copy.deepcopy(records))

        self.assertEqual(point["records"], 2)
        self.assertEqual(point["passed"], 1)
        self.assertEqual(point["pass_rate"], "50.0%")
        self.assertEqual(point["failure_modes"], {"missing_approval_gate": 1})

    def test_trace_trend_point_rejects_empty_records(self):
        with self.assertRaisesRegex(HistoricalTrendSnapshotError, "must not be empty"):
            trace_trend_point("empty", REPO_ROOT / "traces/scored/empty.jsonl", [])


if __name__ == "__main__":
    unittest.main()
