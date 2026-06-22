import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scorer_reliability_report import build_reliability_report, generate_markdown, risk_areas_for_policy_refs  # noqa: E402


class ScorerReliabilityReportTests(unittest.TestCase):
    def test_build_reliability_report_tracks_core_metrics(self):
        report = build_reliability_report()

        self.assertEqual(report["report_id"], "scorer_v1_reliability_report")
        self.assertEqual(report["generated_at"], "2026-06-22T00:00:00Z")
        self.assertTrue(report["safety"]["public_safe"])
        self.assertFalse(report["safety"]["live_execution"])
        self.assertFalse(report["quality_gate_scorer"]["quality_gate_behavior_changed"])
        self.assertFalse(report["quality_gate_scorer"]["model_assisted_judging_in_quality_gate"])

        summary = report["reliability_summary"]
        self.assertEqual(summary["reviewed_records"], 174)
        self.assertEqual(summary["source_trace_count"], 11)
        self.assertEqual(summary["reviewer_count"], 1)
        self.assertEqual(summary["scorer_reviewer_agreements"], 165)
        self.assertEqual(summary["scorer_reviewer_disagreements"], 9)
        self.assertEqual(summary["scorer_review_agreement_rate"], "94.8%")
        self.assertEqual(summary["scorer_false_positive_count"], 1)
        self.assertEqual(summary["scorer_false_negative_count"], 8)
        self.assertEqual(summary["ambiguous_review_count"], 0)
        self.assertEqual(summary["failure_precision"], "96.4%")
        self.assertEqual(summary["failure_recall"], "77.1%")
        self.assertEqual(summary["failure_specificity"], "99.3%")

    def test_reliability_report_slices_by_category_and_risk_area(self):
        report = build_reliability_report()

        self.assertEqual(report["calibration_by_category"]["safe_direct_response"]["scorer_false_positives"], 1)
        self.assertEqual(report["calibration_by_category"]["safe_direct_response"]["scorer_false_negatives"], 0)
        self.assertEqual(report["calibration_by_category"]["approval_gated"]["scorer_false_positives"], 0)
        self.assertEqual(report["calibration_by_category"]["approval_gated"]["scorer_false_negatives"], 8)

        self.assertEqual(report["calibration_by_risk_area"]["safe_task"]["scorer_false_positives"], 1)
        self.assertEqual(report["calibration_by_risk_area"]["approval_gate"]["scorer_false_negatives"], 8)
        self.assertIn("refusal_boundary", report["calibration_by_risk_area"])
        self.assertIn("uncertainty_handling", report["calibration_by_risk_area"])

    def test_reviewer_agreement_is_not_invented_without_overlaps(self):
        report = build_reliability_report()
        reviewer = report["reviewer_agreement"]

        self.assertEqual(reviewer["reviewer_count"], 1)
        self.assertEqual(reviewer["overlapping_review_targets"], 0)
        self.assertEqual(
            reviewer["inter_reviewer_agreement"]["status"],
            "not_available_no_overlapping_review_targets",
        )
        self.assertIsNone(reviewer["inter_reviewer_agreement"]["agreement_rate"])

    def test_risk_area_mapping_uses_policy_prefixes(self):
        self.assertEqual(
            risk_areas_for_policy_refs(["ABP-APPROVAL-001", "ABP-APPROVAL-004"]),
            ["approval_gate"],
        )
        self.assertEqual(
            risk_areas_for_policy_refs(["ABP-UNCERTAINTY-002", "ABP-SAFE-004"]),
            ["safe_task", "uncertainty_handling"],
        )
        self.assertEqual(risk_areas_for_policy_refs([]), ["unknown"])

    def test_generate_markdown_contains_reliability_sections(self):
        markdown = generate_markdown(build_reliability_report())

        self.assertIn("# Scorer Reliability Report", markdown)
        self.assertIn("## Calibration By Risk Area", markdown)
        self.assertIn("## Reviewer Agreement", markdown)
        self.assertIn("## Optional Review Contract", markdown)
        self.assertIn("The deterministic heuristic scorer remains the default quality-gate scorer.", markdown)


if __name__ == "__main__":
    unittest.main()
