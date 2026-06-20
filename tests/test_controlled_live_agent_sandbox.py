import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from controlled_live_agent_sandbox import (  # noqa: E402
    ControlledLiveSandboxError,
    run_controlled_live_agent_sandbox,
)
from validate_adapter_run_metadata import validate_metadata  # noqa: E402


M36_METADATA_PATH = REPO_ROOT / "traces/external/controlled_live_agent_sandbox_metadata.example.json"


def load_metadata():
    return json.loads(M36_METADATA_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2), encoding="utf-8")


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class ControlledLiveAgentSandboxTests(unittest.TestCase):
    def test_committed_m36_metadata_validates(self):
        summary = validate_metadata(M36_METADATA_PATH)

        self.assertEqual(summary["metadata_path"], "traces/external/controlled_live_agent_sandbox_metadata.example.json")
        self.assertEqual(summary["run_id"], "m36_controlled_live_agent_sandbox")
        self.assertEqual(summary["adapter_name"], "local_no_tool_agent_sandbox")
        self.assertEqual(summary["target_profile"], "openclaw_reference_agent")
        self.assertEqual(summary["case_count"], 3)
        self.assertFalse(summary["live_run_in_quality_gate"])

    def test_run_writes_pending_local_raw_records_for_m36_case_subset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "m36_controlled_live_agent_sandbox.local.jsonl"

            summary = run_controlled_live_agent_sandbox(M36_METADATA_PATH, output_path)

            self.assertEqual(summary["run_id"], "m36_controlled_live_agent_sandbox")
            self.assertEqual(summary["raw_records_written"], 3)
            self.assertEqual(summary["review_status"], "pending_review")
            self.assertFalse(summary["quality_gate_included"])

            records = read_jsonl(output_path)
            self.assertEqual([record["case_id"] for record in records], ["APPROVAL-014", "REFUSAL-007", "UNCERTAINTY-008"])
            self.assertEqual({record["review_status"] for record in records}, {"pending_review"})
            self.assertTrue(all(record["review_required"] is True for record in records))
            self.assertEqual({record["target_profile"] for record in records}, {"openclaw_reference_agent"})
            self.assertEqual({record["metadata"]["tool_execution"] for record in records}, {"external_actions_blocked"})
            self.assertTrue(all(record["metadata"]["external_actions_blocked"] is True for record in records))
            self.assertTrue(all(record["provenance"]["public_safe"] is False for record in records))
            self.assertTrue(all(record["provenance"]["external_actions"] is False for record in records))
            self.assertIn("No action has been taken.", records[0]["output_text"])

    def test_rejects_output_path_without_local_jsonl_suffix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "m36_controlled_live_agent_sandbox.jsonl"

            with self.assertRaisesRegex(ControlledLiveSandboxError, "must end with .local.jsonl"):
                run_controlled_live_agent_sandbox(M36_METADATA_PATH, output_path)

    def test_rejects_repo_local_output_outside_traces_raw(self):
        output_path = REPO_ROOT / "traces/external/m36_bad_output.local.jsonl"

        with self.assertRaisesRegex(ControlledLiveSandboxError, "must stay under traces/raw"):
            run_controlled_live_agent_sandbox(M36_METADATA_PATH, output_path)

        self.assertFalse(output_path.exists())

    def test_rejects_metadata_that_allows_manual_network_collection(self):
        metadata = load_metadata()
        metadata["sandbox"]["network_access"] = "allowed_for_manual_collection_only"

        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_path = Path(temp_dir) / "metadata.json"
            output_path = Path(temp_dir) / "sandbox.local.jsonl"
            write_json(metadata_path, metadata)

            with self.assertRaisesRegex(ControlledLiveSandboxError, "must not allow manual collection"):
                run_controlled_live_agent_sandbox(metadata_path, output_path)

    def test_rejects_metadata_with_unblocked_text_generation_tooling(self):
        metadata = load_metadata()
        metadata["sandbox"]["tool_execution"] = "text_generation_only"

        with tempfile.TemporaryDirectory() as temp_dir:
            metadata_path = Path(temp_dir) / "metadata.json"
            output_path = Path(temp_dir) / "sandbox.local.jsonl"
            write_json(metadata_path, metadata)

            with self.assertRaisesRegex(ControlledLiveSandboxError, "tool_execution must be one of"):
                run_controlled_live_agent_sandbox(metadata_path, output_path)


if __name__ == "__main__":
    unittest.main()
