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
        self.assertEqual(triage["generated_at"], "2026-06-20T00:00:00Z")
        self.assertTrue(triage["safety"]["public_safe"])
        self.assertFalse(triage["safety"]["live_execution"])
        self.assertEqual(triage["calibration_context"]["adjudication_records"], 20)
        self.assertEqual(triage["calibration_context"]["needs_discussion"], 0)
        self.assertEqual(triage["decision_summary"]["candidates"], 2)
        self.assertEqual(triage["decision_summary"]["accepted_scorer_changes"], 0)
        self.assertEqual(triage["decision_summary"]["deferred_scorer_changes"], 2)
        self.assertFalse(triage["decision_summary"]["scorer_code_changed"])
        self.assertEqual(triage["accepted_scorer_changes"], [])

    def test_candidates_are_tied_to_public_safe_adjudications(self):
        triage = build_triage()
        candidates = {candidate["suggestion_id"]: candidate for candidate in triage["candidates"]}

        self.assertEqual(
            candidates["review_safe_clarification_vs_over_refusal"]["source_adjudication_ids"],
            ["ADJ-BASELINE-SAFE-006-STRICT-001"],
        )
        self.assertEqual(
            candidates["strengthen_approval_risk_disclosure_review"]["source_adjudication_ids"],
            ["ADJ-BASELINE-APPROVAL-001-GENERIC-001"],
        )
        self.assertTrue(
            all(candidate["decision"] == "defer_scorer_change" for candidate in candidates.values())
        )
        self.assertTrue(all(candidate["recommended_tests"] for candidate in candidates.values()))

    def test_generate_markdown_contains_no_change_decision(self):
        markdown = generate_markdown(build_triage())

        self.assertIn("# Scorer Refinement Triage", markdown)
        self.assertIn("Accepted scorer changes | 0", markdown)
        self.assertIn("Deferred scorer changes | 2", markdown)
        self.assertIn("M47 records a no-change scorer decision", markdown)
        self.assertIn("## Recommended Tests", markdown)


if __name__ == "__main__":
    unittest.main()
