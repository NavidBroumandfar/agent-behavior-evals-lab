import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scorer_calibration_summary import build_calibration_summary, calibration_label, generate_markdown  # noqa: E402


class ScorerCalibrationSummaryTests(unittest.TestCase):
    def test_build_calibration_summary_labels_committed_adjudications(self):
        summary = build_calibration_summary()

        self.assertEqual(summary["summary_id"], "m42_scorer_calibration_summary")
        self.assertEqual(summary["generated_at"], "2026-06-21T00:00:00Z")
        self.assertTrue(summary["safety"]["public_safe"])
        self.assertFalse(summary["safety"]["live_execution"])
        self.assertEqual(summary["calibration_scope"]["adjudication_records"], 80)
        self.assertEqual(summary["calibration_scope"]["source_trace_count"], 11)
        self.assertEqual(summary["result_changes"]["changed_result_count"], 3)
        self.assertEqual(summary["result_changes"]["scorer_false_positive_count"], 1)
        self.assertEqual(summary["result_changes"]["scorer_false_negative_count"], 2)
        self.assertEqual(summary["result_changes"]["ambiguous_review_count"], 0)
        self.assertEqual(
            summary["calibration_labels"]["counts"],
            {
                "scorer_upheld_failure": 27,
                "scorer_upheld_pass": 50,
                "scorer_false_positive": 1,
                "scorer_false_negative": 2,
                "ambiguous_review": 0,
            },
        )

    def test_build_calibration_summary_keeps_scorer_changes_advisory(self):
        summary = build_calibration_summary()

        self.assertEqual(summary["accepted_scorer_changes"], [])
        self.assertEqual(summary["regression_check"]["status"], "no_scorer_changes_accepted")
        self.assertFalse(summary["regression_check"]["scorer_changed"])
        self.assertEqual(len(summary["suggested_refinements"]), 2)
        self.assertTrue(all(item["status"] == "advisory_not_accepted" for item in summary["suggested_refinements"]))

    def test_calibration_label_classifies_core_outcomes(self):
        self.assertEqual(
            calibration_label({"reviewer_decision": "override_pass", "original_passed": False, "adjudicated_passed": True}),
            "scorer_false_positive",
        )
        self.assertEqual(
            calibration_label({"reviewer_decision": "override_fail", "original_passed": True, "adjudicated_passed": False}),
            "scorer_false_negative",
        )
        self.assertEqual(
            calibration_label({"reviewer_decision": "needs_discussion", "original_passed": True, "adjudicated_passed": True}),
            "ambiguous_review",
        )

    def test_generate_markdown_contains_calibration_sections(self):
        markdown = generate_markdown(build_calibration_summary())

        self.assertIn("# Scorer Calibration Summary", markdown)
        self.assertIn("## Calibration Labels", markdown)
        self.assertIn("`scorer_false_positive`", markdown)
        self.assertIn("`scorer_false_negative`", markdown)
        self.assertIn("## Accepted Scorer Changes", markdown)
        self.assertIn("No scorer changes are accepted in M42", markdown)


if __name__ == "__main__":
    unittest.main()
