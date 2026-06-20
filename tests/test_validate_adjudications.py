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

from validate_adjudications import AdjudicationValidationError, validate_adjudication_file


ADJUDICATIONS_PATH = REPO_ROOT / "traces/external/adjudications.example.jsonl"
FOLLOWUP_ADJUDICATIONS_PATH = REPO_ROOT / "traces/external/adjudications.followup.example.jsonl"
EXTERNAL_FIXTURE_ADJUDICATIONS_PATH = REPO_ROOT / "traces/external/external_fixture_adjudications.example.jsonl"
EXTERNAL_FIXTURE_REVIEW_EXPANSION_PATH = (
    REPO_ROOT / "traces/external/external_fixture_review_expansion.example.jsonl"
)


def load_example_records():
    return [json.loads(line) for line in ADJUDICATIONS_PATH.read_text(encoding="utf-8").splitlines()]


def write_jsonl(path, records):
    with path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
            output_file.write("\n")


class ValidateAdjudicationsTests(unittest.TestCase):
    def test_committed_adjudication_fixture_validates(self):
        self.assertEqual(validate_adjudication_file(ADJUDICATIONS_PATH), 8)

    def test_followup_adjudication_fixture_validates(self):
        self.assertEqual(validate_adjudication_file(FOLLOWUP_ADJUDICATIONS_PATH), 4)

    def test_external_fixture_adjudication_fixture_validates(self):
        self.assertEqual(validate_adjudication_file(EXTERNAL_FIXTURE_ADJUDICATIONS_PATH), 8)

    def test_external_fixture_review_expansion_fixture_validates(self):
        self.assertEqual(validate_adjudication_file(EXTERNAL_FIXTURE_REVIEW_EXPANSION_PATH), 22)

    def test_missing_required_field_is_rejected(self):
        record = load_example_records()[0]
        del record["rationale"]

        self.assert_adjudication_fails([record], "missing required fields: rationale")

    def test_unexpected_field_is_rejected_by_schema(self):
        record = load_example_records()[0]
        record["unexpected"] = "value"

        self.assert_adjudication_fails([record], "unexpected fields: unexpected")

    def test_invalid_reviewer_decision_is_rejected_by_schema(self):
        record = load_example_records()[0]
        record["reviewer_decision"] = "dismiss"

        self.assert_adjudication_fails([record], "reviewer_decision must be one of")

    def test_blank_required_text_is_rejected_by_schema(self):
        record = load_example_records()[0]
        record["rationale"] = "   "

        self.assert_adjudication_fails([record], "rationale must match pattern")

    def test_invalid_reviewed_at_is_rejected_by_schema(self):
        record = load_example_records()[0]
        record["reviewed_at"] = "2026-05-23"

        self.assert_adjudication_fails([record], "reviewed_at must match pattern")

    def test_duplicate_adjudication_id_is_rejected(self):
        records = load_example_records()
        records[1]["adjudication_id"] = records[0]["adjudication_id"]

        self.assert_adjudication_fails(records, "adjudication_id duplicate value")

    def test_original_failure_modes_must_match_source_trace(self):
        record = load_example_records()[0]
        record["original_failure_modes"] = ["missing_approval_gate"]

        self.assert_adjudication_fails([record], "original_failure_modes does not match source trace")

    def test_uphold_score_must_preserve_original_result(self):
        record = load_example_records()[0]
        record["adjudicated_passed"] = True
        record["adjudicated_failure_modes"] = []

        self.assert_adjudication_fails([record], "uphold_score must preserve original_passed")

    def test_override_pass_requires_passing_adjudicated_result(self):
        record = load_example_records()[0]
        record["reviewer_decision"] = "override_pass"
        record["adjudicated_passed"] = True
        record["adjudicated_failure_modes"] = []

        self.assert_adjudication_passes([record])

    def test_override_fail_requires_failure_modes(self):
        record = load_example_records()[0]
        record["reviewer_decision"] = "override_fail"
        record["adjudicated_passed"] = False
        record["adjudicated_failure_modes"] = []

        self.assert_adjudication_fails([record], "override_fail requires adjudicated failure modes")

    def test_non_public_safe_adjudication_is_rejected(self):
        record = load_example_records()[0]
        record["public_safe"] = False

        self.assert_adjudication_fails([record], "public_safe must equal True")

    def assert_adjudication_passes(self, records):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "adjudications.jsonl"
            write_jsonl(path, records)

            self.assertEqual(validate_adjudication_file(path), len(records))

    def assert_adjudication_fails(self, records, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "adjudications.jsonl"
            write_jsonl(path, records)

            with self.assertRaisesRegex(AdjudicationValidationError, message):
                validate_adjudication_file(path)


if __name__ == "__main__":
    unittest.main()
