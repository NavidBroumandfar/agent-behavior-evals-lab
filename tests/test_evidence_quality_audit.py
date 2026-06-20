import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from evidence_quality_audit import build_audit, generate_markdown  # noqa: E402


class EvidenceQualityAuditTests(unittest.TestCase):
    def test_build_audit_inventory_uses_committed_artifacts(self):
        audit = build_audit()

        self.assertEqual(audit["audit_id"], "m40_evidence_quality_audit")
        self.assertEqual(audit["generated_at"], "2026-06-21T00:00:00Z")
        self.assertTrue(audit["safety"]["public_safe"])
        self.assertFalse(audit["safety"]["live_execution"])
        self.assertEqual(audit["inventory"]["eval_cases"]["total_cases"], 42)
        self.assertEqual(audit["inventory"]["scored_traces"]["baseline"]["total_records"], 126)
        self.assertEqual(audit["inventory"]["external_fixtures"]["total_scored_records"], 34)
        self.assertEqual(audit["inventory"]["adjudications"]["adjudication_records"], 42)
        self.assertEqual(
            len(audit["inventory"]["adjudications"]["unadjudicated_external_scored_traces"]),
            0,
        )
        self.assertEqual(audit["inventory"]["reports"]["report_artifacts"], 30)

    def test_gap_report_separates_gap_types_with_source_paths(self):
        audit = build_audit()
        gaps = audit["gap_report"]

        self.assertEqual(gaps["summary"]["gap_count"], 9)
        self.assertEqual(gaps["summary"]["case_count"], 42)
        self.assertEqual(gaps["summary"]["total_scored_records"], 160)
        self.assertIn("missing_fixture_coverage", gaps)
        self.assertIn("scorer_weakness", gaps)
        self.assertIn("reporting_weakness", gaps)

        all_gaps = gaps["missing_fixture_coverage"] + gaps["scorer_weakness"] + gaps["reporting_weakness"]
        gap_by_id = {gap["gap_id"]: gap for gap in all_gaps}
        self.assertNotIn("external_fixture_adjudication_absent", gap_by_id)
        self.assertIn("heuristic_scorer_not_semantic_judge", gap_by_id)
        self.assertIn("trend_snapshots_are_descriptive_not_gates", gap_by_id)
        for item in all_gaps:
            self.assertTrue(item["source_paths"])

    def test_generate_markdown_contains_inventory_gaps_and_boundary(self):
        markdown = generate_markdown(build_audit())

        self.assertIn("# Evidence Quality Audit", markdown)
        self.assertIn("## Inventory", markdown)
        self.assertIn("## Gap Report", markdown)
        self.assertIn("### Scorer Weakness", markdown)
        self.assertIn("## Recommendations", markdown)
        self.assertIn("not a live model benchmark", markdown)


if __name__ == "__main__":
    unittest.main()
