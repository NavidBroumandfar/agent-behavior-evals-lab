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

from dry_run_adapter import dry_run_records, write_records
from import_adapter_outputs import AdapterOutputImportError, import_adapter_outputs
from validate_adapter_outputs import AdapterOutputValidationError, validate_jsonl_file


ADAPTER_OUTPUT_FIXTURE_PATH = REPO_ROOT / "traces/external/adapter_outputs.example.jsonl"
DRY_RUN_ADAPTER_OUTPUT_PATH = REPO_ROOT / "traces/external/dry_run_adapter_outputs.jsonl"
LOCAL_PUBLIC_CASE_PATH = REPO_ROOT / "evals/benchmarks/local_public_v1/cases.jsonl"


def valid_adapter_output_record():
    return {
        "record_id": "TEST-ADAPTER-OUTPUT-001",
        "case_id": "SAFE-001",
        "target_profile": "generic_assistant",
        "source_type": "saved_adapter_output",
        "adapter_name": "unit_test_adapter_fixture",
        "adapter_version": "0.1.0-test",
        "created_at": "2026-05-10T00:00:00Z",
        "output_text": "Precision is selected correctness; recall is coverage of all correct items.",
        "provenance": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
        },
        "provenance_details": {
            "source_origin": "synthetic_fixture",
            "execution_mode": "saved_output_only",
            "data_classification": "public_safe_fixture",
            "action_evidence": "output_text_only",
            "notes": "Unit-test fixture with no live target execution.",
        },
        "metadata": {
            "fixture_only": True,
            "test_case": "adapter_output_conformance",
        },
    }


def valid_live_local_adapter_output_record():
    record = valid_adapter_output_record()
    record["record_id"] = "TEST-LIVE-LOCAL-ADAPTER-OUTPUT-001"
    record["case_id"] = "LPB-SAFE-001"
    record["target_profile"] = "text_only_adapter_candidate"
    record["adapter_name"] = "ollama_text_only"
    record["output_text"] = "Precision is about correctness among selected items; recall is about coverage."
    record["provenance"]["live_execution"] = True
    record["provenance_details"] = {
        "source_origin": "live_local_model",
        "execution_mode": "live_local_text_only",
        "data_classification": "public_safe_fixture",
        "action_evidence": "output_text_only",
        "notes": "Reviewed live-local unit-test fixture generated with a fake client.",
    }
    record["metadata"] = {
        "source_metadata": {
            "harness_id": "live_local_text_only_harness",
            "tools_enabled": False,
            "external_actions_allowed": False,
            "credentials_required": False,
            "quality_gate_execution": False,
            "run_status": "succeeded",
        }
    }
    return record


def write_jsonl(path, records):
    with path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
            output_file.write("\n")


class AdapterOutputConformanceTests(unittest.TestCase):
    def test_committed_adapter_output_fixture_validates(self):
        self.assertEqual(validate_jsonl_file(ADAPTER_OUTPUT_FIXTURE_PATH), 4)

    def test_committed_dry_run_adapter_output_validates(self):
        self.assertEqual(validate_jsonl_file(DRY_RUN_ADAPTER_OUTPUT_PATH), 4)

    def test_dry_run_adapter_emits_records_that_validate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "dry_run_adapter_outputs.jsonl"

            records = dry_run_records()
            self.assertTrue(all("provenance_details" in record for record in records))
            self.assertEqual({record["provenance_details"]["source_origin"] for record in records}, {"dry_run_contract"})
            self.assertEqual({record["provenance_details"]["execution_mode"] for record in records}, {"dry_run_only"})

            write_records(records, output_path)

            self.assertEqual(validate_jsonl_file(output_path), 4)

    def test_importer_accepts_valid_adapter_outputs_to_temporary_scored_trace(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "adapter_output_import.jsonl"

            summary = import_adapter_outputs(ADAPTER_OUTPUT_FIXTURE_PATH, output_path)

            self.assertEqual(summary["run_id"], "m4_adapter_output_fixture_import")
            self.assertEqual(summary["total_adapter_output_records"], 4)
            self.assertEqual(summary["pass_count"], 2)
            self.assertEqual(summary["fail_count"], 2)
            self.assertTrue(output_path.exists())

            records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 4)
            self.assertEqual(
                [(record["case_id"], record["passed"]) for record in records],
                [
                    ("SAFE-001", True),
                    ("APPROVAL-004", True),
                    ("REFUSAL-003", False),
                    ("UNCERTAINTY-002", False),
                ],
            )
            self.assertEqual({record["timestamp"] for record in records}, {"2026-05-10T00:00:00Z"})
            self.assertEqual({record["run_id"] for record in records}, {"m4_adapter_output_fixture_import"})
            self.assertTrue(all("provenance_details=" in record["mock_behavior_notes"] for record in records))
            self.assertTrue(all("source_record_id" in record for record in records))
            self.assertTrue(all("adapter_name" in record for record in records))
            self.assertTrue(all("adapter_provenance" in record for record in records))
            self.assertTrue(all("adapter_provenance_details" in record for record in records))

    def test_importer_accepts_registered_text_only_adapter_candidate_profile(self):
        record = valid_adapter_output_record()
        record["target_profile"] = "text_only_adapter_candidate"

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "text_only_adapter_output.jsonl"
            output_path = Path(temp_dir) / "text_only_adapter_import.jsonl"
            write_jsonl(input_path, [record])

            summary = import_adapter_outputs(input_path, output_path)

            self.assertEqual(summary["total_adapter_output_records"], 1)
            records = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(records[0]["profile_name"], "text_only_adapter_candidate")
            self.assertEqual(records[0]["source_record_id"], "TEST-ADAPTER-OUTPUT-001")
            self.assertEqual(records[0]["adapter_name"], "unit_test_adapter_fixture")
            self.assertTrue(records[0]["passed"])

    def test_m4_style_record_without_provenance_details_still_validates(self):
        record = valid_adapter_output_record()
        del record["provenance_details"]

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "m4_style_adapter_output.jsonl"
            write_jsonl(input_path, [record])

            self.assertEqual(validate_jsonl_file(input_path), 1)

    def test_missing_required_fields_are_rejected_before_import(self):
        for field_name in [
            "record_id",
            "case_id",
            "target_profile",
            "source_type",
            "adapter_name",
            "created_at",
            "provenance",
        ]:
            with self.subTest(field_name=field_name):
                record = valid_adapter_output_record()
                del record[field_name]

                self.assert_validation_fails(record)

    def test_unknown_source_type_is_rejected_before_import(self):
        record = valid_adapter_output_record()
        record["source_type"] = "hosted_provider_output"

        self.assert_validation_fails(record, "source_type must be one of")

    def test_unexpected_record_field_is_rejected_before_import(self):
        record = valid_adapter_output_record()
        record["unexpected"] = True

        self.assert_validation_fails(record, "unexpected fields: unexpected")

    def test_created_at_without_z_suffix_is_rejected_before_import(self):
        record = valid_adapter_output_record()
        record["created_at"] = "2026-05-10T00:00:00"

        self.assert_validation_fails(record)

    def test_empty_output_text_after_stripping_is_rejected_before_import(self):
        record = valid_adapter_output_record()
        record["output_text"] = " \t\n "

        self.assert_validation_fails(record)

    def test_invalid_provenance_values_are_rejected_before_import(self):
        invalid_values = [
            ("public_safe", False),
            ("live_execution", True),
            ("external_actions", True),
            ("contains_private_data", True),
        ]

        for field_name, field_value in invalid_values:
            with self.subTest(field_name=field_name):
                record = copy.deepcopy(valid_adapter_output_record())
                record["provenance"][field_name] = field_value

                self.assert_validation_fails(record)

    def test_live_local_adapter_output_requires_explicit_validation_opt_in(self):
        record = valid_live_local_adapter_output_record()

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "live_local_adapter_output.jsonl"
            write_jsonl(input_path, [record])

            with self.assertRaisesRegex(AdapterOutputValidationError, "allow-live-local"):
                validate_jsonl_file(input_path)
            self.assertEqual(validate_jsonl_file(input_path, allow_live_local=True), 1)

    def test_live_local_adapter_output_imports_with_explicit_case_path(self):
        record = valid_live_local_adapter_output_record()

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "live_local_adapter_output.jsonl"
            output_path = Path(temp_dir) / "live_local_scored_trace.jsonl"
            write_jsonl(input_path, [record])

            with self.assertRaises(AdapterOutputValidationError):
                import_adapter_outputs(input_path, output_path)

            summary = import_adapter_outputs(
                input_path,
                output_path,
                allow_live_local=True,
                case_paths=[LOCAL_PUBLIC_CASE_PATH],
            )

            self.assertEqual(summary["total_adapter_output_records"], 1)
            traces = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(traces[0]["case_id"], "LPB-SAFE-001")
            self.assertEqual(traces[0]["adapter_provenance"]["live_execution"], True)
            self.assertTrue(traces[0]["passed"])

    def test_provenance_details_must_be_an_object(self):
        record = valid_adapter_output_record()
        record["provenance_details"] = "not an object"

        self.assert_validation_fails(record)

    def test_invalid_provenance_detail_enum_values_are_rejected_before_import(self):
        invalid_values = [
            ("source_origin", "provider_api_response"),
            ("execution_mode", "live_provider_execution"),
            ("data_classification", "private_fixture"),
            ("action_evidence", "browser_log"),
        ]

        for field_name, field_value in invalid_values:
            with self.subTest(field_name=field_name):
                record = copy.deepcopy(valid_adapter_output_record())
                record["provenance_details"][field_name] = field_value

                self.assert_validation_fails(record)

    def test_provenance_details_notes_must_be_a_string(self):
        record = valid_adapter_output_record()
        record["provenance_details"]["notes"] = ["not", "a", "string"]

        self.assert_validation_fails(record)

    def test_private_or_sensitive_classification_is_rejected_before_import(self):
        record = valid_adapter_output_record()
        record["provenance_details"]["data_classification"] = "private_or_sensitive_blocked"

        self.assert_validation_fails(record, "private_or_sensitive_blocked")

    def test_future_live_execution_mode_is_rejected_before_import(self):
        record = valid_adapter_output_record()
        record["provenance_details"]["execution_mode"] = "future_live_execution_not_in_quality_gate"

        self.assert_validation_fails(record, "future_live_execution_not_in_quality_gate")

    def test_unknown_case_id_fails_during_import_not_validation(self):
        record = valid_adapter_output_record()
        record["case_id"] = "UNKNOWN-ADAPTER-CASE"

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "unknown_case_adapter_output.jsonl"
            output_path = Path(temp_dir) / "should_not_be_written.jsonl"
            write_jsonl(input_path, [record])

            self.assertEqual(validate_jsonl_file(input_path), 1)
            with self.assertRaises(AdapterOutputImportError):
                import_adapter_outputs(input_path, output_path)
            self.assertFalse(output_path.exists())

    def assert_validation_fails(self, record, message=None):
        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "invalid_adapter_output.jsonl"
            write_jsonl(input_path, [record])

            context = (
                self.assertRaisesRegex(AdapterOutputValidationError, message)
                if message
                else self.assertRaises(AdapterOutputValidationError)
            )
            with context:
                validate_jsonl_file(input_path)


if __name__ == "__main__":
    unittest.main()
