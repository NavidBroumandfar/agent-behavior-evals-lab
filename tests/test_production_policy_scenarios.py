import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from production_policy_scenarios import (  # noqa: E402
    DEFAULT_PACK_PATH,
    ProductionPolicyScenarioError,
    generate_production_policy_fixtures,
)
from reporting_utils import load_jsonl_records  # noqa: E402


def load_valid_pack():
    return json.loads(DEFAULT_PACK_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class ProductionPolicyScenarioTests(unittest.TestCase):
    def test_committed_pack_generates_public_safe_scenario_fixtures(self):
        summary = generate_production_policy_fixtures(DEFAULT_PACK_PATH)

        self.assertEqual(summary["pack_id"], "m65_production_policy_scenario_pack")
        self.assertEqual(summary["evidence_class"], "production_policy_scenario_evidence")
        self.assertTrue(summary["scenario_evidence_not_production_proof"])
        self.assertEqual(summary["scenario_families"], 6)
        self.assertEqual(summary["scenarios"], 6)
        self.assertFalse(summary["production_system_access"])
        self.assertFalse(summary["external_actions"])

        transcripts = load_jsonl_records(REPO_ROOT / summary["transcript_path"])
        checks = load_jsonl_records(REPO_ROOT / summary["check_path"])
        self.assertEqual(len(transcripts), 6)
        self.assertEqual(len(checks), 6)
        self.assertEqual(
            {check["family"] for check in checks},
            {
                "database_changes",
                "deployments",
                "credentials",
                "payments",
                "external_messaging",
                "customer_data",
            },
        )
        self.assertTrue(all(check["scenario_evidence_not_production_proof"] for check in checks))
        self.assertTrue(all(not check["safety_assertions"]["production_system_access"] for check in checks))

    def test_live_production_access_is_rejected(self):
        pack = load_valid_pack()
        pack["safety_assertions"]["production_system_access"] = True

        self.assert_pack_fails(pack, "safety_assertions.production_system_access must equal False")

    def test_scenario_notes_must_reject_production_proof(self):
        pack = load_valid_pack()
        pack["scenarios"][0]["notes"] = "Synthetic database-change scenario evidence."

        self.assert_pack_fails(pack, "notes must state not production proof")

    def test_all_required_families_must_be_present(self):
        pack = load_valid_pack()
        pack["scenarios"] = [
            scenario for scenario in pack["scenarios"] if scenario["family"] != "customer_data"
        ]

        self.assert_pack_fails(pack, "scenarios missing required families: customer_data")

    def test_expected_controls_must_require_approval_or_refusal_but_not_both(self):
        pack = load_valid_pack()
        pack["scenarios"][0]["expected_controls"]["refusal_required"] = True

        self.assert_pack_fails(pack, "must require exactly one of approval_required or refusal_required")

    def assert_pack_fails(self, pack, message):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "traces" / "external") as temp_dir:
            path = Path(temp_dir) / "production_policy_scenario_pack.example.json"
            output_prefix = str(path.parent.relative_to(REPO_ROOT))
            pack["outputs"]["transcript_path"] = f"{output_prefix}/production_policy_scenario_transcripts.example.jsonl"
            pack["outputs"]["check_path"] = f"{output_prefix}/production_policy_scenario_checks.example.jsonl"
            write_json(path, pack)

            with self.assertRaisesRegex(ProductionPolicyScenarioError, message):
                generate_production_policy_fixtures(path)


if __name__ == "__main__":
    unittest.main()
