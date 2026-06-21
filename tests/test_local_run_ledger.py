import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from local_run_ledger import (  # noqa: E402
    DEFAULT_LEDGER_PATH,
    DEFAULT_METADATA_PATH,
    DEFAULT_NORMALIZED_OUTPUT_PATH,
    DEFAULT_SCORED_TRACE_PATH,
    generate_example_artifacts,
)
from validate_local_run_ledger import (  # noqa: E402
    DEFAULT_SCHEMA_PATH,
    LocalRunLedgerValidationError,
    validate_local_run_ledger,
)


def load_ledger():
    return json.loads(DEFAULT_LEDGER_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class LocalRunLedgerTests(unittest.TestCase):
    def assert_ledger_error(self, ledger, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "local_run_ledger.json"
            write_json(path, ledger)
            with self.assertRaisesRegex(LocalRunLedgerValidationError, message):
                validate_local_run_ledger(path, DEFAULT_SCHEMA_PATH)

    def test_committed_local_run_ledger_validates(self):
        summary = validate_local_run_ledger(DEFAULT_LEDGER_PATH, DEFAULT_SCHEMA_PATH)

        self.assertEqual(summary["ledger_path"], "traces/external/local_run_ledger.example.json")
        self.assertEqual(summary["schema_path"], "schemas/local_run_ledger.schema.json")
        self.assertEqual(summary["ledger_id"], "m58_reproducible_local_run_ledger_example")
        self.assertEqual(summary["ledger_kind"], "dry_run_public_safe_example")
        self.assertEqual(summary["entry_count"], 1)
        self.assertEqual(summary["normalized_output_records"], 4)
        self.assertEqual(summary["scored_trace_records"], 4)

    def test_generator_can_write_fake_public_safe_artifacts_to_temp_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary = generate_example_artifacts(
                ledger_path=root / "ledger.json",
                normalized_output_path=root / "outputs.jsonl",
                scored_trace_path=root / "scored.jsonl",
                metadata_path=root / "metadata.json",
            )

            self.assertEqual(summary["entry_count"], 1)
            self.assertEqual(summary["normalized_output_records"], 4)
            self.assertEqual(summary["scored_trace_records"], 4)
            self.assertTrue((root / "ledger.json").exists())
            self.assertTrue((root / "outputs.jsonl").exists())
            self.assertTrue((root / "scored.jsonl").exists())
            self.assertTrue((root / "metadata.json").exists())

    def test_committed_example_artifacts_exist(self):
        for path in [
            DEFAULT_LEDGER_PATH,
            DEFAULT_METADATA_PATH,
            DEFAULT_NORMALIZED_OUTPUT_PATH,
            DEFAULT_SCORED_TRACE_PATH,
        ]:
            self.assertTrue(path.exists(), path)

    def test_rejects_normalized_output_hash_mismatch(self):
        ledger = load_ledger()
        ledger["entries"][0]["outputs"]["normalized_output_sha256"] = "0" * 64

        self.assert_ledger_error(ledger, "normalized_output_sha256")

    def test_rejects_scorer_artifact_hash_mismatch(self):
        ledger = load_ledger()
        ledger["entries"][0]["scorer"]["scorer_artifact_sha256"] = "0" * 64

        self.assert_ledger_error(ledger, "scorer_artifact_sha256")

    def test_rejects_case_not_in_declared_split(self):
        ledger = load_ledger()
        ledger["entries"][0]["case_set"]["case_ids"][0] = "LPB-SAFE-004"

        self.assert_ledger_error(ledger, "not in split smoke")

    def test_rejects_quality_gate_execution_allowed(self):
        ledger = load_ledger()
        ledger["entries"][0]["execution_controls"]["quality_gate_execution_allowed"] = True

        self.assert_ledger_error(ledger, "quality_gate_execution_allowed")

    def test_rejects_scored_trace_record_count_mismatch(self):
        ledger = load_ledger()
        ledger["entries"][0]["outputs"]["scored_trace_record_count"] = 99

        self.assert_ledger_error(ledger, "scored_trace_record_count")

    def test_rejects_raw_outputs_included(self):
        ledger = load_ledger()
        ledger["entries"][0]["safety_assertions"]["raw_outputs_included"] = True

        self.assert_ledger_error(ledger, "raw_outputs_included")


if __name__ == "__main__":
    unittest.main()
