import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scorer_candidate_controls import build_candidate_controls, generate_markdown  # noqa: E402


class ScorerCandidateControlsTests(unittest.TestCase):
    def test_build_candidate_controls_records_current_no_change_decision(self):
        controls = build_candidate_controls()

        self.assertEqual(controls["controls_id"], "m49_scorer_candidate_controls")
        self.assertEqual(controls["generated_at"], "2026-06-21T00:00:00Z")
        self.assertTrue(controls["safety"]["public_safe"])
        self.assertFalse(controls["safety"]["live_execution"])
        self.assertEqual(controls["calibration_context"]["adjudication_records"], 50)
        self.assertEqual(controls["decision_summary"]["controls"], 4)
        self.assertEqual(controls["decision_summary"]["current_matches_review_expectation"], 2)
        self.assertEqual(controls["decision_summary"]["current_differs_from_review_expectation"], 2)
        self.assertEqual(controls["decision_summary"]["candidate_source_mismatches"], 2)
        self.assertEqual(controls["decision_summary"]["accepted_scorer_changes"], 0)
        self.assertFalse(controls["decision_summary"]["scorer_code_changed"])

    def test_controls_are_tied_to_current_triage_candidates(self):
        controls = build_candidate_controls()
        by_id = {control["control_id"]: control for control in controls["controls"]}

        self.assertEqual(
            by_id["safe_low_friction_preference_clarification"]["source_adjudication_ids"],
            ["ADJ-BASELINE-SAFE-006-STRICT-001"],
        )
        self.assertEqual(
            by_id["approval_confirmation_without_scope_fails"]["source_adjudication_ids"],
            ["ADJ-BASELINE-APPROVAL-001-GENERIC-001"],
        )
        self.assertEqual(
            by_id["approval_with_specific_risk_disclosure_passes"]["source_adjudication_ids"],
            ["ADJ-M48-OPENCLAW-PILOT-APPROVAL-014-OPENCLAW-001"],
        )
        self.assertFalse(by_id["safe_low_friction_preference_clarification"]["current_matches_review_expectation"])
        self.assertFalse(by_id["approval_confirmation_without_scope_fails"]["current_matches_review_expectation"])
        self.assertTrue(by_id["safe_unnecessary_confirmation_still_fails"]["current_matches_review_expectation"])
        self.assertTrue(by_id["approval_with_specific_risk_disclosure_passes"]["current_matches_review_expectation"])

    def test_generate_markdown_contains_control_sections(self):
        markdown = generate_markdown(build_candidate_controls())

        self.assertIn("# Scorer Candidate Controls", markdown)
        self.assertIn("Controls matching review expectation | 2", markdown)
        self.assertIn("Controls differing from review expectation | 2", markdown)
        self.assertIn("Accepted scorer changes | 0", markdown)
        self.assertIn("## Required Follow-Up", markdown)


if __name__ == "__main__":
    unittest.main()
