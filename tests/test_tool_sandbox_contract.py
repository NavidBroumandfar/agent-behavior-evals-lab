import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from validate_tool_sandbox_contract import (  # noqa: E402
    DEFAULT_SUMMARY_SCHEMA_PATH,
    ToolSandboxContractValidationError,
    validate_contract,
)


CONTRACT_PATH = REPO_ROOT / "traces/external/tool_sandbox_contract.example.json"
CONTRACT_SCHEMA_PATH = REPO_ROOT / "schemas/tool_sandbox_contract.schema.json"


def load_valid_contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class ToolSandboxContractTests(unittest.TestCase):
    def test_committed_contract_and_summaries_validate(self):
        summary = validate_contract(CONTRACT_PATH, CONTRACT_SCHEMA_PATH, DEFAULT_SUMMARY_SCHEMA_PATH)

        self.assertEqual(summary["contract_path"], "traces/external/tool_sandbox_contract.example.json")
        self.assertEqual(summary["contract_id"], "m61_sandboxed_tool_runtime_contract")
        self.assertEqual(summary["sandbox_mode"], "default_deny_metadata_only")
        self.assertEqual(summary["tool_surface_count"], 6)
        self.assertEqual(summary["summary_count"], 3)
        self.assertIn("blocked_by_default_policy", summary["summary_statuses"])
        self.assertIn("approval_requested_not_executed", summary["summary_statuses"])
        self.assertFalse(summary["runtime_execution_in_quality_gate"])
        self.assertFalse(summary["tool_execution_in_quality_gate"])

    def test_missing_surface_is_rejected(self):
        contract = load_valid_contract()
        contract["tool_surfaces"] = [
            policy for policy in contract["tool_surfaces"] if policy["surface"] != "network"
        ]

        self.assert_contract_fails(contract, "tool_surfaces must contain at least 6 item")

    def test_surface_execution_is_rejected(self):
        contract = load_valid_contract()
        contract["tool_surfaces"][0]["execution_allowed"] = True

        self.assert_contract_fails(contract, "execution_allowed must be false")

    def test_raw_log_capture_is_rejected(self):
        contract = load_valid_contract()
        contract["tool_surfaces"][0]["raw_log_capture_allowed"] = True

        self.assert_contract_fails(contract, "raw_log_capture_allowed must be false")

    def test_default_real_actions_are_rejected(self):
        contract = load_valid_contract()
        contract["default_deny_policy"]["real_actions_allowed_by_default"] = True

        self.assert_contract_fails(contract, "real_actions_allowed_by_default must be false")

    def test_quality_gate_tool_execution_is_rejected(self):
        contract = load_valid_contract()
        contract["quality_gate"]["tool_execution_in_quality_gate"] = True

        self.assert_contract_fails(contract, "tool_execution_in_quality_gate must be false")

    def test_approval_cannot_grant_execution(self):
        contract = load_valid_contract()
        contract["approval_policy"]["approval_grants_execution"] = True

        self.assert_contract_fails(contract, "approval_grants_execution must be false")

    def test_missing_blocked_capability_is_rejected(self):
        contract = load_valid_contract()
        contract["blocked_capabilities"].remove("email_send")

        self.assert_contract_fails(contract, "missing required blocked capabilities: email_send")

    def test_summary_side_effect_is_rejected(self):
        contract = load_valid_contract()
        records = load_summary_records()
        records[0]["side_effects"]["filesystem"] = True

        self.assert_contract_and_summaries_fail(contract, records, "side_effects.filesystem must equal False")

    def test_summary_wrong_contract_id_is_rejected(self):
        contract = load_valid_contract()
        records = load_summary_records()
        records[0]["contract_id"] = "other_contract"

        self.assert_contract_and_summaries_fail(
            contract,
            records,
            "contract_id must equal m61_sandboxed_tool_runtime_contract",
        )

    def test_approval_summary_must_not_execute(self):
        contract = load_valid_contract()
        records = load_summary_records()
        records[2]["approval_request"]["status"] = "not_requested"

        self.assert_contract_and_summaries_fail(contract, records, "approval_request must record requested_not_granted")

    def assert_contract_fails(self, contract, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tool_sandbox_contract.json"
            write_json(path, contract)

            with self.assertRaisesRegex(ToolSandboxContractValidationError, message):
                validate_contract(path, CONTRACT_SCHEMA_PATH, DEFAULT_SUMMARY_SCHEMA_PATH)

    def assert_contract_and_summaries_fail(self, contract, records, message):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as repo_temp_dir:
            repo_temp_path = Path(repo_temp_dir)
            summary_path = repo_temp_path / "tool_call_summaries.example.jsonl"
            summary_path.write_text(
                "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
                encoding="utf-8",
            )
            contract_path = repo_temp_path / "tool_sandbox_contract.json"
            contract["summary_schema"]["example_path"] = str(summary_path.relative_to(REPO_ROOT))
            for example in contract["public_safe_examples"]:
                if example["example_type"] == "tool_call_summary_jsonl":
                    example["path"] = str(summary_path.relative_to(REPO_ROOT))
            write_json(contract_path, contract)

            with self.assertRaisesRegex(ToolSandboxContractValidationError, message):
                validate_contract(contract_path, CONTRACT_SCHEMA_PATH, DEFAULT_SUMMARY_SCHEMA_PATH)


def load_summary_records():
    summary_path = REPO_ROOT / "traces/external/tool_call_summaries.example.jsonl"
    return [json.loads(line) for line in summary_path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    unittest.main()
