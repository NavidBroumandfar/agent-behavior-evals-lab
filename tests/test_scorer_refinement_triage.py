import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scorer_refinement_triage import build_triage, generate_markdown  # noqa: E402


class ScorerRefinementTriageTests(unittest.TestCase):
    def test_build_triage_defers_scorer_changes_from_current_evidence(self):
        triage = build_triage()

        self.assertEqual(triage["triage_id"], "m47_scorer_refinement_triage")
        self.assertEqual(triage["generated_at"], "2026-06-21T00:00:00Z")
        self.assertTrue(triage["safety"]["public_safe"])
        self.assertFalse(triage["safety"]["live_execution"])
        self.assertEqual(triage["calibration_context"]["adjudication_records"], 190)
        self.assertEqual(triage["calibration_context"]["needs_discussion"], 0)
        self.assertEqual(triage["decision_summary"]["candidates"], 2)
        self.assertEqual(triage["decision_summary"]["accepted_scorer_changes"], 1)
        self.assertEqual(triage["decision_summary"]["deferred_scorer_changes"], 1)
        self.assertFalse(triage["decision_summary"]["scorer_code_changed"])
        self.assertEqual(len(triage["accepted_scorer_changes"]), 1)

    def test_candidates_are_tied_to_public_safe_adjudications(self):
        triage = build_triage()
        candidates = {candidate["suggestion_id"]: candidate for candidate in triage["candidates"]}

        self.assertEqual(
            candidates["review_safe_clarification_vs_over_refusal"]["source_adjudication_ids"],
            ["ADJ-BASELINE-SAFE-006-STRICT-001"],
        )
        self.assertEqual(
            candidates["strengthen_approval_risk_disclosure_review"]["source_adjudication_ids"],
            [
                "ADJ-BASELINE-APPROVAL-001-GENERIC-001",
                "ADJ-M92-BASELINE-APPROVAL-003-GENERIC-001",
                "ADJ-M91-BASELINE-APPROVAL-005-GENERIC-001",
                "ADJ-M92-BASELINE-APPROVAL-007-GENERIC-001",
                "ADJ-M91-BASELINE-APPROVAL-009-GENERIC-001",
                "ADJ-M91-BASELINE-APPROVAL-011-GENERIC-001",
                "ADJ-M92-BASELINE-APPROVAL-013-GENERIC-001",
                "ADJ-M99-FOCUSED-APPROVAL-001-GENERIC-001",
            ],
        )
        self.assertEqual(candidates["review_safe_clarification_vs_over_refusal"]["decision"], "defer_scorer_change")
        self.assertEqual(candidates["strengthen_approval_risk_disclosure_review"]["decision"], "accept_scorer_change")
        self.assertTrue(all(candidate["recommended_tests"] for candidate in candidates.values()))

    def test_generate_markdown_contains_no_change_decision(self):
        markdown = generate_markdown(build_triage())

        self.assertIn("# Scorer Refinement Triage", markdown)
        self.assertIn("Accepted scorer changes | 1", markdown)
        self.assertIn("Deferred scorer changes | 1", markdown)
        self.assertIn("M99 accepts the approval-disclosure scorer change", markdown)
        self.assertIn("## Recommended Tests", markdown)


if __name__ == "__main__":
    unittest.main()
