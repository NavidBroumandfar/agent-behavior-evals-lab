import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from redaction_promotion_pipeline import (  # noqa: E402
    DEFAULT_CANDIDATE_PATH,
    RedactionPromotionPipelineError,
    generate_redaction_promotion_summary,
    validate_redaction_promotion_pipeline,
)
from reporting_utils import load_jsonl_records  # noqa: E402


REDACTION_NOTES_PATH = REPO_ROOT / "traces/external/redaction_notes.example.jsonl"
PROMOTED_OUTPUT_PATH = REPO_ROOT / "traces/external/promoted_private_evidence_outputs.example.jsonl"


def load_valid_manifest():
    return json.loads(DEFAULT_CANDIDATE_PATH.read_text(encoding="utf-8"))


def load_valid_note():
    return load_jsonl_records(REDACTION_NOTES_PATH)[0]


def load_valid_promoted_record():
    return load_jsonl_records(PROMOTED_OUTPUT_PATH)[0]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
            output_file.write("\n")


class RedactionPromotionPipelineTests(unittest.TestCase):
    def test_committed_pipeline_generates_public_safe_summary(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "reports" / "comparisons") as temp_dir:
            summary_json = Path(temp_dir) / "redaction_promotion_pipeline_summary.json"
            summary_report = Path(temp_dir) / "redaction_promotion_pipeline_summary.md"

            summary = generate_redaction_promotion_summary(
                DEFAULT_CANDIDATE_PATH,
                summary_json_path=summary_json,
                summary_report_path=summary_report,
            )

            self.assertEqual(summary["pipeline_id"], "m67_redaction_promotion_pipeline")
            self.assertEqual(summary["candidate_count"], 1)
            self.assertEqual(summary["redaction_note_count"], 1)
            self.assertEqual(summary["promoted_record_count"], 1)
            self.assertEqual(summary["reviewer_signoff_count"], 1)
            self.assertFalse(summary["private_artifacts_read"])
            self.assertFalse(summary["public_ranking_eligible"])
            self.assertTrue(summary_json.exists())
            self.assertIn("Redaction And Promotion Pipeline Summary", summary_report.read_text(encoding="utf-8"))

    def test_reviewer_signoff_is_required(self):
        manifest = load_valid_manifest()
        manifest["candidates"][0]["reviewer_signoff"] = False

        self.assert_manifest_fails(manifest, "reviewer_signoff must equal True")

    def test_candidate_must_reference_redaction_note(self):
        manifest = load_valid_manifest()
        manifest["candidates"][0]["redaction_note_id"] = "missing-redaction-note"

        self.assert_manifest_fails(manifest, "redaction_note_id must reference a redaction note")

    def test_redaction_note_cannot_retain_raw_values(self):
        manifest = load_valid_manifest()
        note = load_valid_note()
        note["redaction_actions"][0]["raw_value_retained"] = True

        self.assert_manifest_fails(manifest, "raw_value_retained must equal False", notes=[note])

    def test_promoted_output_rejects_private_markers(self):
        manifest = load_valid_manifest()
        record = load_valid_promoted_record()
        record["output_text"] = "This leaked private_evidence/fake_tool_summary_001/tool_summary.local.jsonl."

        self.assert_manifest_fails(manifest, "blocked private marker: private_evidence/", promoted_records=[record])

    def assert_manifest_fails(self, manifest, message, notes=None, promoted_records=None):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "traces" / "external") as temp_dir:
            temp_root = Path(temp_dir)
            manifest_path = temp_root / "redaction_promotion_candidates.example.json"
            if notes is not None:
                notes_path = temp_root / "redaction_notes.example.jsonl"
                write_jsonl(notes_path, notes)
                manifest["redaction_notes_path"] = str(notes_path.relative_to(REPO_ROOT))
            if promoted_records is not None:
                promoted_path = temp_root / "promoted_private_evidence_outputs.example.jsonl"
                write_jsonl(promoted_path, promoted_records)
                manifest["promoted_output_path"] = str(promoted_path.relative_to(REPO_ROOT))
                manifest["candidates"][0]["public_safe_derivative_path"] = str(promoted_path.relative_to(REPO_ROOT))
                if notes is None:
                    note = load_valid_note()
                    note["public_derivative_path"] = str(promoted_path.relative_to(REPO_ROOT))
                    notes_path = temp_root / "redaction_notes.example.jsonl"
                    write_jsonl(notes_path, [note])
                    manifest["redaction_notes_path"] = str(notes_path.relative_to(REPO_ROOT))
            write_json(manifest_path, manifest)

            with self.assertRaisesRegex(RedactionPromotionPipelineError, message):
                validate_redaction_promotion_pipeline(manifest_path)


if __name__ == "__main__":
    unittest.main()
