import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from claim_review_checklist import (  # noqa: E402
    DEFAULT_CHECKLIST_PATH,
    ClaimReviewChecklistError,
    validate_claim_review_checklist,
)


def load_valid_checklist():
    return json.loads(DEFAULT_CHECKLIST_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class ClaimReviewChecklistTests(unittest.TestCase):
    def test_committed_checklist_validates(self):
        summary = validate_claim_review_checklist()

        self.assertEqual(summary["checklist_path"], "traces/external/claim_review_checklist.example.json")
        self.assertEqual(summary["schema_path"], "schemas/claim_review_checklist.schema.json")
        self.assertEqual(summary["checklist_id"], "m86_claim_review_release_checklist")
        self.assertEqual(summary["status"], "public_safe_claim_review_gate")
        self.assertTrue(summary["release_allowed"])
        self.assertEqual(summary["release_label"], "public_safe_local_open_weight_ranking")
        self.assertEqual(summary["ranked_targets"], 2)
        self.assertEqual(summary["allowed_claims"], 1)
        self.assertEqual(summary["blocked_claims"], 8)

    def test_live_execution_in_quality_gate_is_rejected(self):
        checklist = load_valid_checklist()
        checklist["quality_gate"]["live_local_execution_in_quality_gate"] = True

        self.assert_checklist_fails(checklist, "live_local_execution_in_quality_gate must equal False")

    def test_cloud_claim_cannot_be_allowed(self):
        checklist = load_valid_checklist()
        claim = self.claim_outcome(checklist, "cloud_model_ranking")
        claim["allowed"] = True
        claim["outcome"] = "allowed"

        self.assert_checklist_fails(checklist, "must allow only local_open_weight_ranking")

    def test_blocked_claim_requires_concrete_blocker(self):
        checklist = load_valid_checklist()
        claim = self.claim_outcome(checklist, "hosted_provider_comparison")
        claim["blocker_id"] = "none"

        self.assert_checklist_fails(checklist, "blocker_id must name a concrete blocker")

    def test_missing_blocked_gate_is_rejected(self):
        checklist = load_valid_checklist()
        checklist["blocked_gates"] = [
            gate for gate in checklist["blocked_gates"] if gate["claim_id"] != "production_safety"
        ]

        self.assert_checklist_fails(checklist, "missing blockers: m86_block_production_no_production_evidence")

    def test_vague_blocker_is_rejected(self):
        checklist = load_valid_checklist()
        gate = self.blocked_gate(checklist, "m86_block_cloud_ranking_no_cloud_evidence")
        gate["concrete_blocker"] = "Missing context."

        self.assert_checklist_fails(checklist, "must be concrete")

    def test_qwen_smoke_control_cannot_become_ranked_target(self):
        checklist = load_valid_checklist()
        checklist["ranked_targets"].append(
            {
                "benchmark_split": "extended",
                "claim_scope": "current_local_open_weight_ranking",
                "ledger_entry_id": "qwen_fake_entry",
                "model": "qwen3.5:2b-q4_K_M",
                "ranking_eligible": True,
                "runtime": "ollama",
                "sample_size": 210,
            }
        )

        self.assert_checklist_fails(checklist, "ranked_targets must match ranked report models")

    def test_raw_source_path_is_rejected(self):
        checklist = load_valid_checklist()
        checklist["source_paths"].append("traces/raw/m81_mistral_latest_extended.local.jsonl")

        self.assert_checklist_fails(checklist, "must not reference raw or private local artifacts")

    def test_report_status_must_match_current_report(self):
        checklist = load_valid_checklist()
        checklist["reviewed_report"]["report_status"] = "draft"

        self.assert_checklist_fails(checklist, "reviewed_report.report_status must equal 'published_local_ranking'")

    def test_duplicate_release_check_is_rejected(self):
        checklist = load_valid_checklist()
        checklist["release_checks"].append(copy.deepcopy(checklist["release_checks"][0]))

        self.assert_checklist_fails(checklist, "duplicate value")

    def claim_outcome(self, checklist, claim_id):
        for claim in checklist["claim_outcomes"]:
            if claim["claim_id"] == claim_id:
                return claim
        self.fail(f"missing claim outcome: {claim_id}")

    def blocked_gate(self, checklist, blocker_id):
        for gate in checklist["blocked_gates"]:
            if gate["blocker_id"] == blocker_id:
                return gate
        self.fail(f"missing blocked gate: {blocker_id}")

    def assert_checklist_fails(self, checklist, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "claim_review_checklist.example.json"
            write_json(path, checklist)

            with self.assertRaisesRegex(ClaimReviewChecklistError, message):
                validate_claim_review_checklist(path)


if __name__ == "__main__":
    unittest.main()
