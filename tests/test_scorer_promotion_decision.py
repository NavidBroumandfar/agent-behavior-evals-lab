import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scorer_promotion_decision import build_promotion_decision, generate_markdown  # noqa: E402


class ScorerPromotionDecisionTests(unittest.TestCase):
    def test_build_promotion_decision_accepts_rubric_only_update(self):
        decision = build_promotion_decision()

        self.assertEqual(decision["decision_id"], "m53_future_scorer_promotion_or_rubric_update")
        self.assertEqual(decision["generated_at"], "2026-06-21T00:00:00Z")
        self.assertTrue(decision["safety"]["public_safe"])
        self.assertFalse(decision["safety"]["live_execution"])
        self.assertEqual(decision["decision_summary"]["candidate_decisions"], 2)
        self.assertEqual(decision["decision_summary"]["accepted_scorer_promotions"], 0)
        self.assertEqual(decision["decision_summary"]["accepted_rubric_updates"], 1)
        self.assertEqual(decision["decision_summary"]["no_change_decisions"], 1)
        self.assertFalse(decision["decision_summary"]["scorer_code_changed"])
        self.assertFalse(decision["decision_summary"]["scored_trace_behavior_changed"])
        self.assertFalse(decision["decision_summary"]["historical_context_migration_required"])
        self.assertEqual(
            decision["decision_summary"]["decision"],
            "rubric_only_update_no_scorer_change",
        )

    def test_candidate_decisions_distinguish_safe_and_approval_paths(self):
        decision = build_promotion_decision()
        candidates = {item["candidate_id"]: item for item in decision["candidate_decisions"]}

        safe = candidates["triage_review_safe_clarification_vs_over_refusal"]
        self.assertEqual(safe["decision"], "no_change_current_scorer_supported")
        self.assertFalse(safe["accepted_scorer_promotion"])
        self.assertFalse(safe["accepted_rubric_update"])
        self.assertEqual(safe["review_scorer_result_mismatches"], 0)

        approval = candidates["triage_strengthen_approval_risk_disclosure_review"]
        self.assertEqual(approval["decision"], "rubric_update_review_guidance")
        self.assertFalse(approval["accepted_scorer_promotion"])
        self.assertTrue(approval["accepted_rubric_update"])
        self.assertEqual(approval["review_scorer_result_mismatches"], 1)

    def test_generate_markdown_contains_m53_decision_sections(self):
        markdown = generate_markdown(build_promotion_decision())

        self.assertIn("# Scorer Promotion Decision", markdown)
        self.assertIn("Decision | `rubric_only_update_no_scorer_change`", markdown)
        self.assertIn("## Rubric Updates", markdown)
        self.assertIn("approval_disclosure_specificity_review_guidance", markdown)
        self.assertIn("M53 updates rubric guidance but does not modify scorer behavior", markdown)


if __name__ == "__main__":
    unittest.main()
