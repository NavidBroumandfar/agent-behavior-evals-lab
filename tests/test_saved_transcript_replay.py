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

from replay_saved_transcripts import INPUT_PATH, load_transcripts, run_replay, validate_transcripts


def valid_transcript_record():
    return {
        "transcript_id": "TEST-TRANSCRIPT-001",
        "case_id": "SAFE-001",
        "target_profile": "generic_assistant",
        "turns": [
            {
                "turn_id": "test-user-001",
                "role": "user",
                "content": "Explain precision and recall in one sentence.",
            },
            {
                "turn_id": "test-assistant-001",
                "role": "assistant",
                "content": "Precision measures selected correctness; recall measures relevant coverage.",
            },
        ],
        "assistant_turn_index": 1,
        "selected_assistant_turn_id": "test-assistant-001",
        "source_label": "unit-test",
        "provenance": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
            "credentials_required": False,
        },
        "provenance_details": {
            "source_origin": "synthetic_fixture",
            "data_classification": "public_safe_fixture",
            "action_evidence": "selected_assistant_text_only",
            "notes": "Public-safe unit-test transcript.",
        },
        "approval": {
            "request_present": False,
            "outcome": "not_requested",
            "summary": "No approval request was needed.",
        },
        "notes": "Public-safe test transcript.",
    }


def write_jsonl(path, records):
    with path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
            output_file.write("\n")


class SavedTranscriptReplayTests(unittest.TestCase):
    def test_committed_saved_transcript_fixture_shape_validates(self):
        records = load_transcripts(INPUT_PATH)

        self.assertEqual(len(records), 5)

    def test_committed_public_safe_transcript_expansion_shape_validates(self):
        records = load_transcripts(REPO_ROOT / "traces/external/public_safe_transcript_expansion.example.jsonl")

        self.assertEqual(len(records), 8)

    def test_replay_supports_custom_public_safe_pilot_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "pilot_transcripts.jsonl"
            output_path = root / "pilot_scored.jsonl"
            report_path = root / "pilot_report.md"
            write_jsonl(input_path, [valid_transcript_record()])

            summary = run_replay(
                input_path=input_path,
                output_path=output_path,
                report_path=report_path,
                run_id="unit_test_saved_transcript_pilot",
                report_title="Unit Test Saved Transcript Pilot",
                report_context="Unit-test public-safe saved transcript pilot.",
            )

            self.assertEqual(summary["total_transcripts"], 1)
            self.assertEqual(summary["pass_count"], 1)
            self.assertTrue(output_path.exists())
            self.assertTrue(report_path.exists())

    def test_schema_rejects_unexpected_transcript_field(self):
        record = valid_transcript_record()
        record["unexpected"] = True

        self.assert_load_fails([record], "unexpected fields: unexpected")

    def test_schema_rejects_invalid_turn_role(self):
        record = valid_transcript_record()
        record["turns"][1]["role"] = "tool"

        self.assert_load_fails([record], r"turns\[1\]\.role must be one of")

    def test_schema_rejects_blank_required_turn_content(self):
        record = valid_transcript_record()
        record["turns"][1]["content"] = " \t "

        self.assert_load_fails([record], r"turns\[1\]\.content must match pattern")

    def test_schema_requires_rich_public_safe_fields(self):
        for field_name in ["selected_assistant_turn_id", "source_label", "provenance", "provenance_details"]:
            with self.subTest(field_name=field_name):
                record = valid_transcript_record()
                del record[field_name]

                self.assert_load_fails([record], f"missing required fields: {field_name}")

    def test_schema_rejects_raw_tool_log_field(self):
        record = valid_transcript_record()
        record["tool_call_summaries"] = [
            {
                "tool_call_id": "tool-001",
                "tool_name": "shell.run",
                "summary": "No command was run.",
                "status": "not_run",
                "external_action": False,
                "raw_log": "private raw logs must not be committed",
            }
        ]

        self.assert_load_fails([record], r"tool_call_summaries\[0\]: unexpected fields: raw_log")

    def test_semantics_reject_duplicate_transcript_id(self):
        first_record = valid_transcript_record()
        second_record = copy.deepcopy(first_record)
        second_record["case_id"] = "SAFE-002"

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "saved_transcripts.jsonl"
            write_jsonl(path, [first_record, second_record])
            records = load_transcripts(path)

            with self.assertRaisesRegex(ValueError, "duplicate transcript_id"):
                validate_transcripts(records, {"SAFE-001": {}, "SAFE-002": {}}, path)

    def test_semantics_reject_selected_non_assistant_turn(self):
        record = valid_transcript_record()
        record["assistant_turn_index"] = 0

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "saved_transcripts.jsonl"
            write_jsonl(path, [record])
            records = load_transcripts(path)

            with self.assertRaisesRegex(ValueError, "points to role 'user'"):
                validate_transcripts(records, {"SAFE-001": {}}, path)

    def test_semantics_reject_selected_turn_id_mismatch(self):
        record = valid_transcript_record()
        record["selected_assistant_turn_id"] = "different-turn-id"

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "saved_transcripts.jsonl"
            write_jsonl(path, [record])
            records = load_transcripts(path)

            with self.assertRaisesRegex(ValueError, "does not match selected turn_id"):
                validate_transcripts(records, {"SAFE-001": {}}, path)

    def test_semantics_reject_unsafe_provenance(self):
        unsafe_values = [
            ("public_safe", False),
            ("live_execution", True),
            ("external_actions", True),
            ("contains_private_data", True),
            ("credentials_required", True),
        ]

        for field_name, field_value in unsafe_values:
            with self.subTest(field_name=field_name):
                record = valid_transcript_record()
                record["provenance"][field_name] = field_value

                self.assert_load_fails([record], f"provenance.{field_name}")

    def test_semantics_reject_approval_outcome_without_request(self):
        record = valid_transcript_record()
        record["approval"]["outcome"] = "approved"

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "saved_transcripts.jsonl"
            write_jsonl(path, [record])
            records = load_transcripts(path)

            with self.assertRaisesRegex(ValueError, "approval.outcome must be not_requested"):
                validate_transcripts(records, {"SAFE-001": {}}, path)

    def assert_load_fails(self, records, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "saved_transcripts.jsonl"
            write_jsonl(path, records)

            with self.assertRaisesRegex(ValueError, message):
                load_transcripts(path)


if __name__ == "__main__":
    unittest.main()
