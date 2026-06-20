import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from focused_scorer_evidence_expansion import build_evidence_expansion, generate_markdown  # noqa: E402


class FocusedScorerEvidenceExpansionTests(unittest.TestCase):
    def test_build_evidence_expansion_records_no_scorer_change(self):
        evidence = build_evidence_expansion()

        self.assertEqual(evidence["evidence_id"], "m52_focused_scorer_evidence_expansion")
        self.assertEqual(evidence["generated_at"], "2026-06-21T00:00:00Z")
        self.assertTrue(evidence["safety"]["public_safe"])
        self.assertFalse(evidence["safety"]["live_execution"])
        self.assertEqual(evidence["focused_fixture"]["input_records"], 6)
        self.assertEqual(evidence["focused_fixture"]["scored_trace_records"], 6)
        self.assertEqual(evidence["focused_fixture"]["adjudication_records"], 6)
        self.assertEqual(evidence["decision_summary"]["focused_controls"], 6)
        self.assertEqual(evidence["decision_summary"]["candidate_groups"], 2)
        self.assertEqual(evidence["decision_summary"]["review_scorer_result_mismatches"], 1)
        self.assertEqual(evidence["decision_summary"]["accepted_scorer_changes"], 0)
        self.assertFalse(evidence["decision_summary"]["scorer_code_changed"])
        self.assertFalse(evidence["decision_summary"]["scored_trace_behavior_changed"])

    def test_candidate_evidence_maps_to_current_scorer_candidates(self):
        evidence = build_evidence_expansion()
        candidates = {item["candidate_id"]: item for item in evidence["candidate_evidence"]}

        self.assertEqual(
            candidates["triage_review_safe_clarification_vs_over_refusal"]["record_count"],
            3,
        )
        self.assertEqual(
            candidates["triage_review_safe_clarification_vs_over_refusal"]["review_scorer_result_mismatches"],
            0,
        )
        self.assertEqual(
            candidates["triage_strengthen_approval_risk_disclosure_review"]["record_count"],
            3,
        )
        self.assertEqual(
            candidates["triage_strengthen_approval_risk_disclosure_review"]["review_scorer_result_mismatches"],
            1,
        )
        approval_ids = {
            record["adjudication_id"]
            for record in candidates["triage_strengthen_approval_risk_disclosure_review"]["records"]
        }
        self.assertIn("ADJ-M52-FOCUSED-APPROVAL-007-GENERIC-001", approval_ids)

    def test_generate_markdown_contains_m52_decision_sections(self):
        markdown = generate_markdown(build_evidence_expansion())

        self.assertIn("# Focused Scorer Evidence Expansion", markdown)
        self.assertIn("Focused controls | 6", markdown)
        self.assertIn("Decision | `evidence_expanded_no_scorer_change`", markdown)
        self.assertIn("## Candidate Evidence", markdown)
        self.assertIn("No scorer code changes are accepted in M52", markdown)


if __name__ == "__main__":
    unittest.main()
