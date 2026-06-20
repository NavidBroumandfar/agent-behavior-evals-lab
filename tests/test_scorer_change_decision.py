import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from scorer_change_decision import build_scorer_change_decision, generate_markdown  # noqa: E402


class ScorerChangeDecisionTests(unittest.TestCase):
    def test_build_scorer_change_decision_records_no_change(self):
        decision = build_scorer_change_decision()

        self.assertEqual(decision["decision_id"], "m50_deterministic_scorer_change_decision")
        self.assertEqual(decision["generated_at"], "2026-06-21T00:00:00Z")
        self.assertTrue(decision["safety"]["public_safe"])
        self.assertFalse(decision["safety"]["live_execution"])
        self.assertEqual(decision["decision_summary"]["candidates_evaluated"], 2)
        self.assertEqual(decision["decision_summary"]["accepted_scorer_changes"], 0)
        self.assertEqual(decision["decision_summary"]["rubric_only_no_change_decisions"], 2)
        self.assertFalse(decision["decision_summary"]["scorer_code_changed"])
        self.assertFalse(decision["decision_summary"]["scored_trace_behavior_changed"])
        self.assertEqual(decision["decision_summary"]["decision"], "rubric_only_no_scorer_change")
        self.assertFalse(decision["historical_context"]["historical_scorer_version_metadata_present"])

    def test_safe_candidate_records_conflicting_same_output_reviews(self):
        decision = build_scorer_change_decision()
        candidates = {candidate["candidate_id"]: candidate for candidate in decision["candidate_decisions"]}
        safe_candidate = candidates["triage_review_safe_clarification_vs_over_refusal"]
        conflict = safe_candidate["evidence_findings"][0]

        self.assertEqual(conflict["finding_id"], "same_output_conflicting_safe_reviews")
        self.assertEqual(conflict["same_output_reviewed_records"], 4)
        self.assertEqual(conflict["adjudicated_passes"], 1)
        self.assertEqual(conflict["adjudicated_failures"], 3)
        self.assertIn(
            "ADJ-BASELINE-SAFE-006-STRICT-001",
            {record["adjudication_id"] for record in conflict["records"]},
        )
        self.assertIn(
            "ADJ-FOLLOWUP-SAFE-009-STRICT-001",
            {record["adjudication_id"] for record in conflict["records"]},
        )

    def test_approval_candidate_requires_historical_guardrails_before_change(self):
        decision = build_scorer_change_decision()
        candidates = {candidate["candidate_id"]: candidate for candidate in decision["candidate_decisions"]}
        approval_candidate = candidates["triage_strengthen_approval_risk_disclosure_review"]

        self.assertFalse(approval_candidate["accepted_scorer_change"])
        self.assertEqual(approval_candidate["decision"], "rubric_only_no_scorer_change")
        self.assertIn(
            "historical_trace_versioning_needed",
            {finding["finding_id"] for finding in approval_candidate["evidence_findings"]},
        )

    def test_generate_markdown_contains_decision_sections(self):
        markdown = generate_markdown(build_scorer_change_decision())

        self.assertIn("# Scorer Change Decision", markdown)
        self.assertIn("Decision | `rubric_only_no_scorer_change`", markdown)
        self.assertIn("Accepted scorer changes | 0", markdown)
        self.assertIn("## Candidate Decisions", markdown)
        self.assertIn("## Required Follow-Up", markdown)


if __name__ == "__main__":
    unittest.main()
