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

from replay_saved_transcripts import INPUT_PATH, load_transcripts, validate_transcripts


def valid_transcript_record():
    return {
        "transcript_id": "TEST-TRANSCRIPT-001",
        "case_id": "SAFE-001",
        "target_profile": "generic_assistant",
        "turns": [
            {
                "role": "user",
                "content": "Explain precision and recall in one sentence.",
            },
            {
                "role": "assistant",
                "content": "Precision measures selected correctness; recall measures relevant coverage.",
            },
        ],
        "assistant_turn_index": 1,
        "source_label": "unit-test",
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

    def assert_load_fails(self, records, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "saved_transcripts.jsonl"
            write_jsonl(path, records)

            with self.assertRaisesRegex(ValueError, message):
                load_transcripts(path)


if __name__ == "__main__":
    unittest.main()
