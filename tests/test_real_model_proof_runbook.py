import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from real_model_proof_runbook import (  # noqa: E402
    DEFAULT_RUNBOOK_PATH,
    RealModelProofRunbookError,
    generate_real_model_proof_runbook,
    validate_real_model_proof_runbook,
)


def load_valid_runbook():
    return json.loads(DEFAULT_RUNBOOK_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class RealModelProofRunbookTests(unittest.TestCase):
    def test_committed_runbook_generates_public_safe_report(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "reports" / "comparisons") as temp_dir:
            report_json = Path(temp_dir) / "real_model_proof_runbook.json"
            report_md = Path(temp_dir) / "real_model_proof_runbook.md"

            report = generate_real_model_proof_runbook(
                report_json_path=report_json,
                report_markdown_path=report_md,
            )

            self.assertEqual(report["report_id"], "m76_real_model_proof_runbook_report")
            self.assertEqual(report["second_target_decision"]["selected_model"], "mistral:latest")
            self.assertEqual(report["evidence_status"]["required_cases_per_primary_model"], 210)
            self.assertEqual(report["evidence_status"]["eligible_reviewed_live_local_ledgers"], 2)
            self.assertTrue(report["publication_gate"]["local_ranking_claim_allowed"])
            self.assertTrue(report_json.exists())
            self.assertIn("Real Model Proof Runbook", report_md.read_text(encoding="utf-8"))

    def test_live_command_requires_explicit_opt_in(self):
        runbook = load_valid_runbook()
        runbook["operator_commands"][1]["command"] = "python3 scripts/live_local.py --model gemma4:latest --split extended"

        self.assert_runbook_fails(runbook, "explicit opt-in")

    def test_primary_targets_must_match_plan(self):
        runbook = load_valid_runbook()
        runbook["model_lineup"]["primary_local_targets"][0]["model"] = "other:latest"

        self.assert_runbook_fails(runbook, "M80 selected model")

    def test_selected_target_cannot_be_smoke_control(self):
        runbook = load_valid_runbook()
        runbook["second_target_decision"]["selected_model"] = "qwen3.5:2b-q4_K_M"
        runbook["model_lineup"]["primary_local_targets"][0]["model"] = "qwen3.5:2b-q4_K_M"
        runbook["operator_commands"][0]["command"] = (
            "python3 scripts/live_local.py --model qwen3.5:2b-q4_K_M --adapter ollama_text_only --split extended --plan-only"
        )
        runbook["operator_commands"][1]["command"] = (
            "AGENT_EVALS_ENABLE_LIVE_LOCAL=1 python3 scripts/live_local.py --model qwen3.5:2b-q4_K_M "
            "--adapter ollama_text_only --split extended --live-local --max-failures 210"
        )

        self.assert_runbook_fails(runbook, "smoke/control")

    def test_selected_target_requires_plan_command(self):
        runbook = load_valid_runbook()
        runbook["operator_commands"][0]["command"] = "python3 scripts/live_local.py --model other:latest --plan-only"

        self.assert_runbook_fails(runbook, "non-live plan")

    def test_cloud_target_must_stay_excluded(self):
        runbook = load_valid_runbook()
        runbook["model_lineup"]["excluded_targets"][0]["eligible_for_local_ranking"] = True

        self.assert_runbook_fails(runbook, "ranking-ineligible")

    def test_ranking_claim_requires_two_ledgers(self):
        runbook = load_valid_runbook()
        runbook["evidence_status"]["eligible_reviewed_live_local_ledgers"] = 1
        runbook["publication_gate"]["local_ranking_claim_allowed"] = True

        self.assert_runbook_fails(runbook, "before two eligible ledgers")

    def test_hosted_path_cannot_mix_with_local_ranking(self):
        runbook = load_valid_runbook()
        runbook["hosted_provider_path"]["mixed_with_local_ranking"] = True

        self.assert_runbook_fails(runbook, "mixed_with_local_ranking")

    def assert_runbook_fails(self, runbook, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "real_model_proof_runbook.example.json"
            write_json(path, runbook)

            with self.assertRaisesRegex(RealModelProofRunbookError, message):
                validate_real_model_proof_runbook(path)


if __name__ == "__main__":
    unittest.main()
