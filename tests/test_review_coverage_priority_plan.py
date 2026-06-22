import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from review_coverage_priority_plan import build_review_coverage_priority_plan, generate_markdown  # noqa: E402


class ReviewCoveragePriorityPlanTests(unittest.TestCase):
    def test_build_review_coverage_priority_plan_tracks_scope(self):
        plan = build_review_coverage_priority_plan()

        self.assertEqual(plan["plan_id"], "m88_review_coverage_priority_plan")
        self.assertEqual(plan["generated_at"], "2026-06-22T00:00:00Z")
        self.assertTrue(plan["safety"]["public_safe"])
        self.assertFalse(plan["safety"]["live_execution"])
        self.assertFalse(plan["quality_gate_scorer"]["quality_gate_behavior_changed"])
        self.assertFalse(plan["quality_gate_scorer"]["model_assisted_judging_in_quality_gate"])

        summary = plan["coverage_summary"]
        self.assertEqual(summary["review_sources"], 11)
        self.assertEqual(summary["scored_records"], 174)
        self.assertEqual(summary["adjudication_records"], 174)
        self.assertEqual(summary["reviewed_records"], 174)
        self.assertEqual(summary["unreviewed_records"], 0)
        self.assertEqual(summary["review_coverage"], "100.0%")
        self.assertEqual(summary["unreviewed_heuristic_failures"], 0)
        self.assertEqual(summary["unreviewed_high_or_critical_records"], 0)

    def test_priority_queue_reports_complete_coverage(self):
        plan = build_review_coverage_priority_plan()
        priority_queue = plan["priority_queue"]

        self.assertEqual(priority_queue, [])
        self.assertEqual(plan["recommended_batches"], [])

    def test_source_coverage_includes_baseline_and_fixtures(self):
        plan = build_review_coverage_priority_plan()
        by_source = {row["source_id"]: row for row in plan["coverage_by_source"]}

        self.assertEqual(by_source["baseline_mock_run"]["scored_records"], 126)
        self.assertEqual(by_source["baseline_mock_run"]["reviewed_records"], 126)
        self.assertEqual(by_source["baseline_mock_run"]["unreviewed_heuristic_failures"], 0)
        self.assertEqual(by_source["focused_scorer_evidence"]["review_coverage"], "100.0%")
        self.assertEqual(by_source["hermes_long_running_agent"]["review_coverage"], "100.0%")
        self.assertEqual(by_source["public_safe_transcript_expansion"]["review_coverage"], "100.0%")

    def test_generate_markdown_contains_boundary_sections(self):
        markdown = generate_markdown(build_review_coverage_priority_plan())

        self.assertIn("# Review Coverage Priority Plan", markdown)
        self.assertIn("## Coverage By Source", markdown)
        self.assertIn("## Priority Queue", markdown)
        self.assertIn("No unreviewed records remain in scope.", markdown)
        self.assertIn("No reviewer batch is recommended because scoped review coverage is complete.", markdown)
        self.assertIn("The deterministic heuristic scorer remains the quality-gate scorer.", markdown)


if __name__ == "__main__":
    unittest.main()
