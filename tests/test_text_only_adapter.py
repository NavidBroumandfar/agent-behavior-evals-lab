import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from import_adapter_outputs import import_adapter_outputs
from text_only_adapter import TextOnlyAdapterError, adapt_text_only_outputs
from validate_adapter_outputs import AdapterOutputValidationError, validate_jsonl_file


ADAPTER_RUN_METADATA_PATH = REPO_ROOT / "traces/external/adapter_run_metadata.example.json"
CHECK_ALL_PATH = REPO_ROOT / "scripts/check_all.py"


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path, records):
    with path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
            output_file.write("\n")


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def m33_metadata():
    metadata = json.loads(ADAPTER_RUN_METADATA_PATH.read_text(encoding="utf-8"))
    metadata["metadata_id"] = "M33-TEXT-ONLY-ADAPTER-TEST"
    metadata["created_at"] = "2026-06-20T00:00:00Z"
    metadata["run_id"] = "m33_text_only_adapter_test"
    metadata["status"] = "saved_output_review_only"
    metadata["adapter"] = {
        "adapter_name": "controlled_text_only_adapter",
        "adapter_version": "0.1.0-test",
        "adapter_type": "hosted_model_text_only",
    }
    metadata["target"] = {
        "target_profile": "text_only_adapter_candidate",
        "profile_path": "targets/profiles/generic_assistant.md",
    }
    metadata["case_selection"] = {
        "case_source_paths": ["evals/cases/safe_task_cases.jsonl"],
        "case_ids": ["SAFE-001"],
        "case_count": 1,
    }
    metadata["sandbox"] = {
        "execution_mode": "saved_output_review_only",
        "network_access": "not_applicable",
        "tool_execution": "none",
        "external_actions": False,
        "credentials_required": False,
        "human_approval_required": True,
        "risk_level": "low",
    }
    metadata["outputs"] = {
        "raw_output_path": "traces/raw/m33_text_only_adapter_test.local.jsonl",
        "normalized_output_path": "traces/external/m33_text_only_adapter_test.reviewed.jsonl",
        "scored_trace_path": "traces/scored/m33_text_only_adapter_test.local.jsonl",
        "commit_policy": "reviewed_public_safe_outputs_only",
    }
    metadata["review"]["notes"] = "M33 unit-test metadata for approved final text only; no live run is executed."
    return metadata


def approved_text_record():
    return {
        "case_id": "SAFE-001",
        "target_profile": "text_only_adapter_candidate",
        "output_text": "Precision measures selected correctness; recall measures coverage of all relevant items.",
        "review_status": "approved_public_safe",
        "provenance": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
            "credentials_required": False,
        },
        "source_label": "unit_test_reviewed_final_text",
        "notes": "Public-safe final text for M33 adapter path coverage.",
    }


def load_check_all_module():
    spec = importlib.util.spec_from_file_location("check_all_for_m33_test", CHECK_ALL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TextOnlyAdapterTests(unittest.TestCase):
    def test_text_only_adapter_writes_valid_normalized_output_and_imports_to_scored_trace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            metadata_path = root / "adapter_run_metadata.json"
            input_path = root / "reviewed_text_inputs.jsonl"
            output_path = root / "m33_text_only_adapter.reviewed.jsonl"
            scored_path = root / "m33_text_only_adapter_scored.jsonl"
            write_json(metadata_path, m33_metadata())
            write_jsonl(input_path, [approved_text_record()])

            summary = adapt_text_only_outputs(metadata_path, input_path, output_path)

            self.assertEqual(summary["run_id"], "m33_text_only_adapter_test")
            self.assertEqual(summary["adapter_records_written"], 1)
            self.assertEqual(validate_jsonl_file(output_path), 1)

            adapter_records = read_jsonl(output_path)
            self.assertEqual(adapter_records[0]["record_id"], "m33_text_only_adapter_test-TEXT-ONLY-001")
            self.assertEqual(adapter_records[0]["source_type"], "saved_adapter_output")
            self.assertEqual(adapter_records[0]["target_profile"], "text_only_adapter_candidate")
            self.assertEqual(adapter_records[0]["adapter_name"], "controlled_text_only_adapter")
            self.assertEqual(adapter_records[0]["provenance_details"]["source_origin"], "future_controlled_adapter_output")
            self.assertEqual(adapter_records[0]["provenance_details"]["execution_mode"], "saved_output_only")

            import_summary = import_adapter_outputs(output_path, scored_path)

            self.assertEqual(import_summary["total_adapter_output_records"], 1)
            self.assertEqual(import_summary["pass_count"], 1)
            scored_records = read_jsonl(scored_path)
            self.assertEqual(scored_records[0]["profile_name"], "text_only_adapter_candidate")
            self.assertEqual(scored_records[0]["adapter_name"], "controlled_text_only_adapter")
            self.assertTrue(scored_records[0]["passed"])

    def test_text_only_adapter_rejects_unapproved_final_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            metadata_path = root / "adapter_run_metadata.json"
            input_path = root / "reviewed_text_inputs.jsonl"
            output_path = root / "m33_text_only_adapter.reviewed.jsonl"
            record = approved_text_record()
            record["review_status"] = "pending_review"
            write_json(metadata_path, m33_metadata())
            write_jsonl(input_path, [record])

            with self.assertRaisesRegex(TextOnlyAdapterError, "review_status must be approved_public_safe"):
                adapt_text_only_outputs(metadata_path, input_path, output_path)

    def test_text_only_adapter_rejects_unsafe_provenance(self):
        invalid_values = [
            ("public_safe", False),
            ("live_execution", True),
            ("external_actions", True),
            ("contains_private_data", True),
            ("credentials_required", True),
        ]

        for field_name, field_value in invalid_values:
            with self.subTest(field_name=field_name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    root = Path(temp_dir)
                    metadata_path = root / "adapter_run_metadata.json"
                    input_path = root / "reviewed_text_inputs.jsonl"
                    output_path = root / "m33_text_only_adapter.reviewed.jsonl"
                    record = copy.deepcopy(approved_text_record())
                    record["provenance"][field_name] = field_value
                    write_json(metadata_path, m33_metadata())
                    write_jsonl(input_path, [record])

                    with self.assertRaisesRegex(TextOnlyAdapterError, f"provenance.{field_name}"):
                        adapt_text_only_outputs(metadata_path, input_path, output_path)

    def test_adapter_output_validator_rejects_future_only_live_review_claims(self):
        record = {
            "record_id": "M33-FUTURE-LIVE-CLAIM",
            "case_id": "SAFE-001",
            "target_profile": "text_only_adapter_candidate",
            "source_type": "saved_adapter_output",
            "adapter_name": "controlled_text_only_adapter",
            "adapter_version": "0.1.0-test",
            "created_at": "2026-06-20T00:00:00Z",
            "output_text": "Precision measures selected correctness; recall measures relevant coverage.",
            "provenance": {
                "public_safe": True,
                "live_execution": False,
                "external_actions": False,
                "contains_private_data": False,
            },
            "provenance_details": {
                "source_origin": "future_controlled_adapter_output",
                "execution_mode": "future_live_execution_not_in_quality_gate",
                "data_classification": "public_safe_fixture",
                "action_evidence": "output_text_only",
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "future_live_claim.reviewed.jsonl"
            write_jsonl(input_path, [record])

            with self.assertRaisesRegex(AdapterOutputValidationError, "future_live_execution_not_in_quality_gate"):
                validate_jsonl_file(input_path)

    def test_quality_gate_does_not_execute_text_only_adapter_collection(self):
        check_all = load_check_all_module()
        live_adapter_commands = [
            command
            for _name, command in check_all.CHECKS
            if len(command) >= 2 and command[0] == "python3" and command[1] == "src/text_only_adapter.py"
        ]

        self.assertEqual(live_adapter_commands, [])


if __name__ == "__main__":
    unittest.main()
