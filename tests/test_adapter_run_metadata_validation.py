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

from validate_adapter_run_metadata import AdapterRunMetadataValidationError, validate_metadata


ADAPTER_RUN_METADATA_PATH = REPO_ROOT / "traces/external/adapter_run_metadata.example.json"


def load_valid_metadata():
    return json.loads(ADAPTER_RUN_METADATA_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2), encoding="utf-8")


class AdapterRunMetadataValidationTests(unittest.TestCase):
    def test_committed_adapter_run_metadata_validates(self):
        summary = validate_metadata(ADAPTER_RUN_METADATA_PATH)

        self.assertEqual(summary["metadata_path"], "traces/external/adapter_run_metadata.example.json")
        self.assertEqual(summary["run_id"], "m6_non_gated_adapter_sandbox_example")
        self.assertEqual(summary["adapter_name"], "example_text_only_adapter")
        self.assertEqual(summary["target_profile"], "generic_assistant")
        self.assertEqual(summary["case_count"], 1)
        self.assertFalse(summary["live_run_in_quality_gate"])

    def test_missing_top_level_fields_are_rejected(self):
        for field_name in ["run_id", "adapter", "target", "case_selection", "sandbox", "provenance"]:
            with self.subTest(field_name=field_name):
                metadata = load_valid_metadata()
                del metadata[field_name]

                self.assert_metadata_fails(metadata, f"missing required fields: {field_name}")

    def test_unexpected_nested_fields_are_rejected(self):
        metadata = load_valid_metadata()
        metadata["adapter"]["provider_account_id"] = "should-not-be-present"

        self.assert_metadata_fails(metadata, "adapter: unexpected fields: provider_account_id")

    def test_invalid_status_is_rejected_by_schema(self):
        metadata = load_valid_metadata()
        metadata["status"] = "live_run"

        self.assert_metadata_fails(metadata, "status must be one of")

    def test_blank_required_text_is_rejected_by_schema(self):
        metadata = load_valid_metadata()
        metadata["review"]["notes"] = "   "

        self.assert_metadata_fails(metadata, "review.notes must match pattern")

    def test_empty_case_ids_are_rejected_by_schema(self):
        metadata = load_valid_metadata()
        metadata["case_selection"]["case_ids"] = []

        self.assert_metadata_fails(metadata, "case_selection.case_ids must contain at least 1 item")

    def test_invalid_created_at_shape_is_rejected_by_schema(self):
        metadata = load_valid_metadata()
        metadata["created_at"] = "2026-05-23"

        self.assert_metadata_fails(metadata, "created_at must match pattern")

    def test_invalid_created_at_date_is_rejected_locally(self):
        metadata = load_valid_metadata()
        metadata["created_at"] = "2026-99-23T00:00:00Z"

        self.assert_metadata_fails(metadata, "created_at must be a valid UTC timestamp")

    def test_unknown_target_profile_is_rejected(self):
        metadata = load_valid_metadata()
        metadata["target"]["target_profile"] = "unknown_real_model"

        self.assert_metadata_fails(metadata, "target_profile must be one of")

    def test_missing_profile_path_is_rejected(self):
        metadata = load_valid_metadata()
        metadata["target"]["profile_path"] = "targets/profiles/missing_profile.md"

        self.assert_metadata_fails(metadata, "profile_path does not exist")

    def test_case_count_must_match_case_ids(self):
        metadata = load_valid_metadata()
        metadata["case_selection"]["case_count"] = 2

        self.assert_metadata_fails(metadata, "case_count must match the number of case_ids")

    def test_unknown_case_id_is_rejected(self):
        metadata = load_valid_metadata()
        metadata["case_selection"]["case_ids"] = ["UNKNOWN-001"]

        self.assert_metadata_fails(metadata, "case_ids contains unknown case IDs")

    def test_live_execution_provenance_is_rejected_for_committed_metadata(self):
        metadata = load_valid_metadata()
        metadata["provenance"]["live_execution"] = True

        self.assert_metadata_fails(metadata, "provenance.live_execution must be false")

    def test_external_actions_are_rejected_for_committed_metadata(self):
        metadata = load_valid_metadata()
        metadata["sandbox"]["external_actions"] = True

        self.assert_metadata_fails(metadata, "sandbox.external_actions must be false for M6 metadata")

    def test_credentials_are_rejected_for_committed_metadata(self):
        metadata = load_valid_metadata()
        metadata["provenance"]["credentials_required"] = True

        self.assert_metadata_fails(metadata, "provenance.credentials_required must be false")

    def test_boolean_shape_is_rejected_by_schema(self):
        metadata = load_valid_metadata()
        metadata["sandbox"]["external_actions"] = "false"

        self.assert_metadata_fails(metadata, "sandbox.external_actions must be boolean")

    def test_live_run_must_stay_out_of_quality_gate(self):
        metadata = load_valid_metadata()
        metadata["quality_gate"]["live_run_in_quality_gate"] = True

        self.assert_metadata_fails(metadata, "quality_gate.live_run_in_quality_gate must be false")

    def test_raw_output_path_must_be_local_jsonl_under_traces_raw(self):
        invalid_paths = [
            "traces/raw/example.jsonl",
            "traces/external/example.local.jsonl",
            "../outside.local.jsonl",
        ]

        for raw_output_path in invalid_paths:
            with self.subTest(raw_output_path=raw_output_path):
                metadata = load_valid_metadata()
                metadata["outputs"]["raw_output_path"] = raw_output_path

                self.assert_metadata_fails(metadata, "raw_output_path")

    def test_normalized_output_path_must_not_be_local(self):
        metadata = load_valid_metadata()
        metadata["outputs"]["normalized_output_path"] = "traces/external/example.local.jsonl"

        self.assert_metadata_fails(metadata, "normalized_output_path must describe a reviewed public-safe candidate")

    def test_raw_outputs_are_never_committable(self):
        metadata = load_valid_metadata()
        metadata["review"]["raw_outputs_committable"] = True

        self.assert_metadata_fails(metadata, "review.raw_outputs_committable must be false")

    def assert_metadata_fails(self, metadata, message=None):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "adapter_run_metadata.json"
            write_json(path, metadata)

            if message is None:
                with self.assertRaises(AdapterRunMetadataValidationError):
                    validate_metadata(path)
            else:
                with self.assertRaisesRegex(AdapterRunMetadataValidationError, message):
                    validate_metadata(path)


if __name__ == "__main__":
    unittest.main()
