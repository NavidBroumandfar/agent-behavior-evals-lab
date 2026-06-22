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
        self.assertEqual(snapshot["generated_at"], "2026-06-21T00:00:00Z")
        self.assertTrue(snapshot["safety"]["public_safe"])
        self.assertFalse(snapshot["safety"]["live_execution"])

        current = snapshot["current_snapshot"]
        self.assertEqual(current["pass_rates"]["baseline"]["records"], 126)
        self.assertEqual(current["pass_rates"]["baseline"]["pass_rate"], "91.3%")
        self.assertEqual(current["fixture_counts"]["fixture_groups"], 10)
        self.assertEqual(current["fixture_counts"]["scored_records"], 48)
        self.assertEqual(current["adjudication_outcomes"]["adjudication_records"], 160)
        self.assertEqual(current["adjudication_outcomes"]["source_trace_count"], 11)
        self.assertEqual(current["adjudication_outcomes"]["reviewed_external_source_trace_count"], 10)
        self.assertEqual(current["adjudication_outcomes"]["changed_result_count"], 9)
        self.assertEqual(current["adjudication_outcomes"]["reviewer_decisions"]["needs_discussion"], 0)
        self.assertEqual(current["adjudication_outcomes"]["calibration_label_counts"]["ambiguous_review"], 0)
        self.assertEqual(current["report_manifest_coverage"]["report_artifacts"], 62)
        self.assertEqual(current["report_manifest_coverage"]["json_snapshots"], 24)
        self.assertEqual(current["report_manifest_coverage"]["markdown_reports"], 38)
        self.assertEqual(current["scorer_refinement_triage"]["accepted_scorer_changes"], 0)
        self.assertEqual(current["scorer_refinement_triage"]["deferred_scorer_changes"], 2)
        self.assertEqual(current["scorer_candidate_controls"]["controls"], 4)
        self.assertEqual(current["scorer_candidate_controls"]["accepted_scorer_changes"], 0)
        self.assertEqual(current["scorer_change_decision"]["candidates_evaluated"], 2)
        self.assertEqual(current["scorer_change_decision"]["accepted_scorer_changes"], 0)
        self.assertEqual(current["scorer_change_decision"]["decision"], "rubric_only_no_scorer_change")
        self.assertTrue(current["scorer_versioning_guardrails"]["historical_scorer_context_supported"])
        self.assertEqual(current["scorer_versioning_guardrails"]["current_records_with_historical_context"], 0)
        self.assertFalse(current["scorer_versioning_guardrails"]["migration_required_now"])
        self.assertEqual(current["focused_scorer_evidence"]["focused_controls"], 6)
        self.assertEqual(current["focused_scorer_evidence"]["candidate_groups"], 2)
        self.assertEqual(current["focused_scorer_evidence"]["review_scorer_result_mismatches"], 1)
        self.assertEqual(current["focused_scorer_evidence"]["accepted_scorer_changes"], 0)
        self.assertEqual(
            current["focused_scorer_evidence"]["decision"],
            "evidence_expanded_no_scorer_change",
        )
        self.assertFalse(current["focused_scorer_evidence"]["scorer_code_changed"])
        self.assertEqual(current["scorer_promotion_decision"]["candidate_decisions"], 2)
        self.assertEqual(current["scorer_promotion_decision"]["accepted_scorer_promotions"], 0)
        self.assertEqual(current["scorer_promotion_decision"]["accepted_rubric_updates"], 1)
        self.assertFalse(current["scorer_promotion_decision"]["scorer_code_changed"])
        self.assertEqual(
            current["scorer_promotion_decision"]["decision"],
            "rubric_only_update_no_scorer_change",
        )

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
                "m45_external_fixture_adjudication_coverage",
                "m46_needs_discussion_resolution",
                "m47_deterministic_scorer_refinement_triage",
                "m48_external_fixture_review_expansion",
                "m49_scorer_candidate_control_tests",
                "m50_deterministic_scorer_change_decision",
                "m51_scorer_versioning_guardrails",
                "m52_focused_scorer_evidence_expansion",
                "m53_future_scorer_promotion_or_rubric_update",
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
