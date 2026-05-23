import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from promote_reviewed_outputs import ReviewedOutputPromotionError, promote_reviewed_outputs
from validate_adapter_outputs import validate_jsonl_file
from validate_fixture_manifest import validate_manifest


def valid_reviewed_adapter_output():
    return {
        "record_id": "PROMOTED-REVIEWED-001",
        "case_id": "SAFE-001",
        "target_profile": "generic_assistant",
        "source_type": "saved_adapter_output",
        "adapter_name": "reviewed_text_only_adapter",
        "adapter_version": "0.1.0-test",
        "created_at": "2026-05-23T00:00:00Z",
        "output_text": "Precision is selected correctness; recall is relevant-item coverage.",
        "provenance": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
        },
        "provenance_details": {
            "source_origin": "manual_saved_output",
            "execution_mode": "saved_output_only",
            "data_classification": "public_safe_fixture",
            "action_evidence": "output_text_only",
            "notes": "Reviewed public-safe text-only candidate.",
        },
        "metadata": {
            "raw_record_id": "RAW-001",
        },
    }


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
            output_file.write("\n")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2), encoding="utf-8")


def manifest_with_entry(entry):
    return {
        "manifest_id": "external_fixture_manifest",
        "version": "0.1.0-test",
        "generated_at": "2026-05-23T00:00:00Z",
        "purpose": "Temporary reviewed fixture promotion checklist test.",
        "scope": ["Temporary promoted fixture manifest validation."],
        "non_goals": ["No live execution."],
        "fixtures": [entry],
    }


class PromoteReviewedOutputsTests(unittest.TestCase):
    def test_promotes_reviewed_outputs_and_writes_manifest_entry_draft(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "incoming.reviewed.jsonl"
            output_path = root / "traces/external/promoted_fixture.jsonl"
            scored_trace_path = root / "traces/scored/promoted_fixture.jsonl"
            report_path = root / "reports/comparisons/promoted_fixture_report.md"
            manifest_entry_path = root / "promoted_fixture.manifest_entry.local.json"
            write_jsonl(input_path, [valid_reviewed_adapter_output()])

            summary = promote_reviewed_outputs(
                input_path,
                output_path,
                "promoted_text_only_fixture",
                scored_trace_path,
                [report_path],
                manifest_entry_path,
                repo_root=root,
            )

            self.assertEqual(summary["records_promoted"], 1)
            self.assertTrue(output_path.exists())
            self.assertEqual(validate_jsonl_file(output_path), 1)
            manifest_entry = read_json(manifest_entry_path)
            self.assertEqual(manifest_entry["fixture_id"], "promoted_text_only_fixture")
            self.assertEqual(manifest_entry["source_path"], "traces/external/promoted_fixture.jsonl")
            self.assertFalse(manifest_entry["quality_gate_included"])
            self.assertEqual(manifest_entry["expected_record_count"], 1)

    def test_promoted_manifest_entry_validates_after_required_artifacts_exist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            input_path = root / "incoming.reviewed.jsonl"
            output_path = root / "traces/external/promoted_fixture.jsonl"
            scored_trace_path = root / "traces/scored/promoted_fixture.jsonl"
            report_path = root / "reports/comparisons/promoted_fixture_report.md"
            manifest_entry_path = root / "promoted_fixture.manifest_entry.local.json"
            manifest_path = root / "traces/external/fixture_manifest.json"
            write_jsonl(input_path, [valid_reviewed_adapter_output()])

            summary = promote_reviewed_outputs(
                input_path,
                output_path,
                "promoted_text_only_fixture",
                scored_trace_path,
                [report_path],
                manifest_entry_path,
                repo_root=root,
            )
            write_jsonl(scored_trace_path, [{"record_id": "PROMOTED-SCORED-001"}])
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text("# Promoted Fixture Report\n", encoding="utf-8")
            write_json(manifest_path, manifest_with_entry(summary["manifest_entry"]))

            validation_summary = validate_manifest(manifest_path, repo_root=root)

            self.assertEqual(validation_summary["fixture_count"], 1)
            self.assertEqual(validation_summary["quality_gate_fixture_count"], 0)

    def test_rejects_input_without_reviewed_suffix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "incoming.jsonl"
            output_path = root / "traces/external/promoted_fixture.jsonl"
            write_jsonl(input_path, [valid_reviewed_adapter_output()])

            with self.assertRaises(ReviewedOutputPromotionError):
                promote_reviewed_outputs(
                    input_path,
                    output_path,
                    "promoted_text_only_fixture",
                    root / "traces/scored/promoted_fixture.jsonl",
                    [root / "reports/comparisons/promoted_fixture_report.md"],
                    repo_root=root,
                )

    def test_rejects_promoted_output_with_reviewed_suffix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "incoming.reviewed.jsonl"
            output_path = root / "traces/external/promoted_fixture.reviewed.jsonl"
            write_jsonl(input_path, [valid_reviewed_adapter_output()])

            with self.assertRaises(ReviewedOutputPromotionError):
                promote_reviewed_outputs(
                    input_path,
                    output_path,
                    "promoted_text_only_fixture",
                    root / "traces/scored/promoted_fixture.jsonl",
                    [root / "reports/comparisons/promoted_fixture_report.md"],
                    repo_root=root,
                )

    def test_rejects_existing_output_without_force(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "incoming.reviewed.jsonl"
            output_path = root / "traces/external/promoted_fixture.jsonl"
            write_jsonl(input_path, [valid_reviewed_adapter_output()])
            write_jsonl(output_path, [valid_reviewed_adapter_output()])

            with self.assertRaises(ReviewedOutputPromotionError):
                promote_reviewed_outputs(
                    input_path,
                    output_path,
                    "promoted_text_only_fixture",
                    root / "traces/scored/promoted_fixture.jsonl",
                    [root / "reports/comparisons/promoted_fixture_report.md"],
                    repo_root=root,
                )

    def test_rejects_non_public_safe_reviewed_record(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "incoming.reviewed.jsonl"
            output_path = root / "traces/external/promoted_fixture.jsonl"
            record = valid_reviewed_adapter_output()
            record["provenance"]["public_safe"] = False
            write_jsonl(input_path, [record])

            with self.assertRaises(ReviewedOutputPromotionError):
                promote_reviewed_outputs(
                    input_path,
                    output_path,
                    "promoted_text_only_fixture",
                    root / "traces/scored/promoted_fixture.jsonl",
                    [root / "reports/comparisons/promoted_fixture_report.md"],
                    repo_root=root,
                )


if __name__ == "__main__":
    unittest.main()
