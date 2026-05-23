import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from collect_text_only_outputs import TextOnlyOutputCollectionError, collect_text_only_outputs
from review_text_only_outputs import TextOnlyOutputReviewError, review_text_only_outputs
from validate_adapter_outputs import validate_jsonl_file


METADATA_PATH = REPO_ROOT / "traces/external/adapter_run_metadata.example.json"


def write_jsonl(path, records):
    with path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
            output_file.write("\n")


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def valid_text_input():
    return {
        "case_id": "SAFE-001",
        "target_profile": "generic_assistant",
        "output_text": "Precision is selected correctness; recall is coverage of relevant items.",
        "source_label": "unit_test_saved_text",
        "notes": "Temporary public-safe text-only workflow test.",
    }


class TextOnlyOutputWorkflowTests(unittest.TestCase):
    def test_collect_text_only_outputs_writes_pending_local_raw_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "text_inputs.jsonl"
            output_path = root / "raw_outputs.local.jsonl"
            write_jsonl(input_path, [valid_text_input()])

            summary = collect_text_only_outputs(METADATA_PATH, input_path, output_path)

            self.assertEqual(summary["run_id"], "m6_non_gated_adapter_sandbox_example")
            self.assertEqual(summary["raw_records_written"], 1)
            records = read_jsonl(output_path)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["review_status"], "pending_review")
            self.assertFalse(records[0]["provenance"]["public_safe"])
            self.assertTrue(records[0]["review_required"])

    def test_collect_rejects_output_path_without_local_suffix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "text_inputs.jsonl"
            output_path = root / "raw_outputs.jsonl"
            write_jsonl(input_path, [valid_text_input()])

            with self.assertRaises(TextOnlyOutputCollectionError):
                collect_text_only_outputs(METADATA_PATH, input_path, output_path)

    def test_collect_rejects_case_outside_metadata_selection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "text_inputs.jsonl"
            output_path = root / "raw_outputs.local.jsonl"
            record = valid_text_input()
            record["case_id"] = "SAFE-002"
            write_jsonl(input_path, [record])

            with self.assertRaises(TextOnlyOutputCollectionError):
                collect_text_only_outputs(METADATA_PATH, input_path, output_path)

    def test_review_converts_approved_raw_records_to_adapter_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "text_inputs.jsonl"
            raw_path = root / "raw_outputs.local.jsonl"
            reviewed_path = root / "adapter_outputs.reviewed.jsonl"
            write_jsonl(input_path, [valid_text_input()])
            collect_text_only_outputs(METADATA_PATH, input_path, raw_path)

            raw_records = read_jsonl(raw_path)
            raw_records[0]["review_status"] = "approved_public_safe"
            raw_records[0]["provenance"]["public_safe"] = True
            write_jsonl(raw_path, raw_records)

            summary = review_text_only_outputs(raw_path, reviewed_path)

            self.assertEqual(summary["raw_records_loaded"], 1)
            self.assertEqual(summary["approved_records_written"], 1)
            self.assertEqual(validate_jsonl_file(reviewed_path), 1)
            adapter_records = read_jsonl(reviewed_path)
            self.assertEqual(adapter_records[0]["source_type"], "saved_adapter_output")
            self.assertEqual(adapter_records[0]["target_profile"], "generic_assistant")
            self.assertEqual(adapter_records[0]["provenance_details"]["execution_mode"], "saved_output_only")

    def test_review_rejects_pending_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "text_inputs.jsonl"
            raw_path = root / "raw_outputs.local.jsonl"
            reviewed_path = root / "adapter_outputs.reviewed.jsonl"
            write_jsonl(input_path, [valid_text_input()])
            collect_text_only_outputs(METADATA_PATH, input_path, raw_path)

            with self.assertRaises(TextOnlyOutputReviewError):
                review_text_only_outputs(raw_path, reviewed_path)

    def test_review_requires_approved_records_to_be_public_safe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "text_inputs.jsonl"
            raw_path = root / "raw_outputs.local.jsonl"
            reviewed_path = root / "adapter_outputs.reviewed.jsonl"
            write_jsonl(input_path, [valid_text_input()])
            collect_text_only_outputs(METADATA_PATH, input_path, raw_path)

            raw_records = read_jsonl(raw_path)
            raw_records[0]["review_status"] = "approved_public_safe"
            write_jsonl(raw_path, raw_records)

            with self.assertRaises(TextOnlyOutputReviewError):
                review_text_only_outputs(raw_path, reviewed_path)

    def test_review_rejects_output_path_without_reviewed_suffix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw_path = root / "raw_outputs.local.jsonl"
            reviewed_path = root / "adapter_outputs.jsonl"
            write_jsonl(raw_path, [])

            with self.assertRaises(TextOnlyOutputReviewError):
                review_text_only_outputs(raw_path, reviewed_path)


if __name__ == "__main__":
    unittest.main()
