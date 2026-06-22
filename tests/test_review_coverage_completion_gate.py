import copy
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from review_coverage_completion_gate import (  # noqa: E402
    ReviewCoverageCompletionGateError,
    build_review_coverage_completion_gate,
    generate_markdown,
    validate_completion_gate,
)


class ReviewCoverageCompletionGateTests(unittest.TestCase):
    def test_build_review_coverage_completion_gate_locks_complete_scope(self):
        gate = build_review_coverage_completion_gate()

        self.assertEqual(gate["gate_id"], "m96_review_coverage_completion_gate")
        self.assertEqual(gate["generated_at"], "2026-06-22T00:00:00Z")
        self.assertTrue(gate["safety"]["public_safe"])
        self.assertFalse(gate["safety"]["live_execution"])
        self.assertFalse(gate["quality_gate_scorer"]["quality_gate_behavior_changed"])
        self.assertFalse(gate["quality_gate_scorer"]["model_assisted_judging_in_quality_gate"])

        summary = gate["completion_summary"]
        self.assertEqual(summary["review_sources"], 11)
        self.assertEqual(summary["scored_records"], 174)
        self.assertEqual(summary["reviewed_records"], 174)
        self.assertEqual(summary["adjudication_records"], 174)
        self.assertEqual(summary["review_coverage"], "100.0%")
        self.assertEqual(summary["unreviewed_records"], 0)
        self.assertEqual(summary["priority_queue_records"], 0)
        self.assertEqual(summary["recommended_batches"], 0)
        self.assertEqual(summary["scorer_review_agreement_rate"], "94.8%")
        self.assertEqual(summary["scorer_false_positive_count"], 1)
        self.assertEqual(summary["scorer_false_negative_count"], 8)

        self.assertTrue(gate["gate_status"]["gate_passed"])
        self.assertFalse(gate["gate_status"]["stale_priority_plan"])
        self.assertEqual(gate["gate_status"]["blocking_findings"], [])
        self.assertEqual(gate["next_phase_recommendation"]["reviewer_work_status"], "paused_until_new_scope")

    def test_validate_completion_gate_rejects_incomplete_coverage(self):
        gate = build_review_coverage_completion_gate()
        broken = copy.deepcopy(gate)
        broken["completion_summary"]["unreviewed_records"] = 1

        with self.assertRaisesRegex(ReviewCoverageCompletionGateError, "unreviewed_records must equal 0"):
            validate_completion_gate(broken)

    def test_validate_completion_gate_rejects_source_with_recommended_review_action(self):
        gate = build_review_coverage_completion_gate()
        broken = copy.deepcopy(gate)
        broken["source_completion"][0]["recommended_action"] = "review_unreviewed_heuristic_failures_first"

        with self.assertRaisesRegex(ReviewCoverageCompletionGateError, "unexpected recommended action"):
            validate_completion_gate(broken)

    def test_validate_completion_gate_rejects_blocking_findings(self):
        gate = build_review_coverage_completion_gate()
        broken = copy.deepcopy(gate)
        broken["gate_status"]["gate_passed"] = False
        broken["gate_status"]["blocking_findings"] = ["review coverage is below 100.0%"]

        with self.assertRaisesRegex(ReviewCoverageCompletionGateError, "blocking findings"):
            validate_completion_gate(broken)

    def test_generate_markdown_reports_next_phase_and_boundary(self):
        markdown = generate_markdown(build_review_coverage_completion_gate())

        self.assertIn("# Review Coverage Completion Gate", markdown)
        self.assertIn("## Source Completion", markdown)
        self.assertIn("No blocking findings.", markdown)
        self.assertIn("new_public_safe_scored_trace_or_case_expansion", markdown)
        self.assertIn("The deterministic heuristic scorer remains the quality-gate scorer.", markdown)


if __name__ == "__main__":
    unittest.main()
