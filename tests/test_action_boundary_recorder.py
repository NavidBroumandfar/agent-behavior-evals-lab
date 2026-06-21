import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from action_boundary_recorder import (  # noqa: E402
    DEFAULT_APPROVAL_OUTPUT_PATH,
    DEFAULT_DENIAL_OUTPUT_PATH,
    DEFAULT_INPUT_PATH,
    ActionBoundaryRecorderError,
    build_boundary_evidence,
)
from reporting_utils import load_jsonl_records  # noqa: E402


class ActionBoundaryRecorderTests(unittest.TestCase):
    def test_committed_action_boundary_examples_generate(self):
        summary = build_boundary_evidence(DEFAULT_INPUT_PATH, DEFAULT_APPROVAL_OUTPUT_PATH, DEFAULT_DENIAL_OUTPUT_PATH)

        self.assertEqual(summary["source_summaries"], 4)
        self.assertEqual(summary["approval_events"], 4)
        self.assertEqual(summary["action_denials"], 4)
        self.assertEqual(summary["missing_approval_events"], 2)
        self.assertEqual(summary["vague_approval_events"], 1)
        self.assertEqual(summary["fake_completion_claims"], 1)

        approval_events = load_jsonl_records(DEFAULT_APPROVAL_OUTPUT_PATH)
        action_denials = load_jsonl_records(DEFAULT_DENIAL_OUTPUT_PATH)
        labels = {label for event in approval_events for label in event["score_labels"]}
        self.assertIn("missing_approval", labels)
        self.assertIn("vague_approval", labels)
        self.assertIn("specific_approval_request", labels)
        self.assertIn("fake_completion_claim", labels)
        self.assertTrue(any(record["fake_completion_claim"] for record in action_denials))
        self.assertTrue(all(not record["approval_received"] for record in approval_events))
        self.assertTrue(all(record["denied_before_execution"] for record in action_denials))

    def test_duplicate_summary_id_is_rejected(self):
        records = load_jsonl_records(DEFAULT_INPUT_PATH)
        records[1]["summary_id"] = records[0]["summary_id"]

        self.assert_records_fail(records, "summary_id duplicate value")

    def test_side_effects_are_rejected(self):
        records = load_jsonl_records(DEFAULT_INPUT_PATH)
        records[0]["side_effects"]["filesystem"] = True

        self.assert_records_fail(records, "side_effects.filesystem must equal False")

    def test_vague_approval_is_detected(self):
        build_boundary_evidence(DEFAULT_INPUT_PATH, DEFAULT_APPROVAL_OUTPUT_PATH, DEFAULT_DENIAL_OUTPUT_PATH)
        approval_events = load_jsonl_records(DEFAULT_APPROVAL_OUTPUT_PATH)
        vague_events = [event for event in approval_events if event["request_specificity"] == "vague"]

        self.assertEqual(len(vague_events), 1)
        self.assertIn("vague_approval", vague_events[0]["score_labels"])

    def test_missing_approval_is_detected(self):
        build_boundary_evidence(DEFAULT_INPUT_PATH, DEFAULT_APPROVAL_OUTPUT_PATH, DEFAULT_DENIAL_OUTPUT_PATH)
        approval_events = load_jsonl_records(DEFAULT_APPROVAL_OUTPUT_PATH)
        missing_events = [event for event in approval_events if event["request_specificity"] == "missing"]

        self.assertEqual(len(missing_events), 2)
        self.assertTrue(all("missing_approval" in event["score_labels"] for event in missing_events))

    def test_fake_completion_claim_is_detected(self):
        build_boundary_evidence(DEFAULT_INPUT_PATH, DEFAULT_APPROVAL_OUTPUT_PATH, DEFAULT_DENIAL_OUTPUT_PATH)
        action_denials = load_jsonl_records(DEFAULT_DENIAL_OUTPUT_PATH)
        fake_completion = [record for record in action_denials if record["fake_completion_claim"] is True]

        self.assertEqual(len(fake_completion), 1)
        self.assertFalse(fake_completion[0]["raw_private_log_included"])
        self.assertTrue(fake_completion[0]["no_side_effects"])

    def test_missing_fake_completion_coverage_is_rejected(self):
        records = load_jsonl_records(DEFAULT_INPUT_PATH)
        for record in records:
            record["public_safe_summary"] = record["public_safe_summary"].replace("claimed completion", "reported")
            record["public_safe_summary"] = record["public_safe_summary"].replace("claimed", "reported")

        self.assert_records_fail(records, "approval events missing labels: fake_completion_claim")

    def assert_records_fail(self, records, message):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT) as temp_dir:
            temp_path = Path(temp_dir)
            input_path = temp_path / "action_boundary_tool_summaries.example.jsonl"
            approval_path = temp_path / "approval_events.example.jsonl"
            denial_path = temp_path / "action_denials.example.jsonl"
            input_path.write_text(
                "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ActionBoundaryRecorderError, message):
                build_boundary_evidence(input_path, approval_path, denial_path)


if __name__ == "__main__":
    unittest.main()
