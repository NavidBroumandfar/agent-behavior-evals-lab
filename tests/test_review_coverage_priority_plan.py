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
        self.assertEqual(summary["adjudication_records"], 80)
        self.assertEqual(summary["reviewed_records"], 80)
        self.assertEqual(summary["unreviewed_records"], 94)
        self.assertEqual(summary["review_coverage"], "46.0%")
        self.assertEqual(summary["unreviewed_heuristic_failures"], 0)
        self.assertEqual(summary["unreviewed_high_or_critical_records"], 34)

    def test_priority_queue_prefers_unreviewed_failures(self):
        plan = build_review_coverage_priority_plan()
        priority_queue = plan["priority_queue"]

        self.assertEqual(len(priority_queue), 20)
        self.assertTrue(all(record["review_priority"] > 0 for record in priority_queue))
        self.assertTrue(priority_queue[0]["passed"])
        self.assertEqual(priority_queue[0]["severity"], "high")
        self.assertEqual(priority_queue[0]["category"], "approval_gated")
        self.assertEqual(priority_queue[0]["priority_rationale"], "Unreviewed high-severity heuristic pass.")
        self.assertEqual(plan["recommended_batches"][0]["batch_id"], "m91_approval_gate_pass_review_sample")

    def test_source_coverage_includes_baseline_and_fixtures(self):
        plan = build_review_coverage_priority_plan()
        by_source = {row["source_id"]: row for row in plan["coverage_by_source"]}

        self.assertEqual(by_source["baseline_mock_run"]["scored_records"], 126)
        self.assertEqual(by_source["baseline_mock_run"]["reviewed_records"], 34)
        self.assertEqual(by_source["baseline_mock_run"]["unreviewed_heuristic_failures"], 0)
        self.assertEqual(by_source["focused_scorer_evidence"]["review_coverage"], "100.0%")
        self.assertEqual(by_source["hermes_long_running_agent"]["review_coverage"], "100.0%")
        self.assertEqual(by_source["public_safe_transcript_expansion"]["review_coverage"], "75.0%")

    def test_generate_markdown_contains_boundary_sections(self):
        markdown = generate_markdown(build_review_coverage_priority_plan())

        self.assertIn("# Review Coverage Priority Plan", markdown)
        self.assertIn("## Coverage By Source", markdown)
        self.assertIn("## Priority Queue", markdown)
        self.assertIn("The deterministic heuristic scorer remains the quality-gate scorer.", markdown)


if __name__ == "__main__":
    unittest.main()
