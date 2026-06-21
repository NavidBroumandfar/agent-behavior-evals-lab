import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from long_running_agent_adapter import (  # noqa: E402
    DEFAULT_PLAN_PATH,
    LongRunningAgentAdapterError,
    generate_session_fixture,
)
from reporting_utils import load_jsonl_records  # noqa: E402


def load_valid_plan():
    return json.loads(DEFAULT_PLAN_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class LongRunningAgentAdapterTests(unittest.TestCase):
    def test_committed_plan_generates_public_safe_session_fixture(self):
        summary = generate_session_fixture(DEFAULT_PLAN_PATH)

        self.assertEqual(summary["adapter_id"], "m64_hermes_long_running_agent_adapter")
        self.assertEqual(summary["target_runtime"], "hermes")
        self.assertEqual(summary["target_profile"], "hermes_long_running_agent")
        self.assertEqual(summary["transcripts"], 2)
        self.assertEqual(summary["session_boundaries"], 2)
        self.assertEqual(summary["memory_checks"], 4)
        self.assertFalse(summary["live_hermes_execution_in_quality_gate"])
        self.assertFalse(summary["private_memory_read_in_quality_gate"])

        transcripts = load_jsonl_records(REPO_ROOT / summary["transcript_output_path"])
        boundaries = load_jsonl_records(REPO_ROOT / summary["session_boundary_output_path"])
        checks = load_jsonl_records(REPO_ROOT / summary["memory_check_output_path"])
        self.assertEqual(transcripts[0]["source_label"], "hermes_long_running_memory_public_safe")
        self.assertFalse(transcripts[0]["provenance"]["live_execution"])
        self.assertFalse(boundaries[0]["private_memory_included"])
        self.assertFalse(checks[0]["raw_memory_referenced"])

    def test_live_hermes_execution_in_quality_gate_is_rejected(self):
        plan = load_valid_plan()
        plan["quality_gate"]["live_hermes_execution_in_quality_gate"] = True

        self.assert_plan_fails(plan, "live_hermes_execution_in_quality_gate must be false")

    def test_private_memory_read_in_quality_gate_is_rejected(self):
        plan = load_valid_plan()
        plan["quality_gate"]["private_memory_read_in_quality_gate"] = True

        self.assert_plan_fails(plan, "private_memory_read_in_quality_gate must be false")

    def test_private_memory_safety_assertion_is_rejected(self):
        plan = load_valid_plan()
        plan["safety_assertions"]["private_memory"] = True

        self.assert_plan_fails(plan, "safety_assertions.private_memory must equal False")

    def test_raw_memory_path_must_be_local_only(self):
        plan = load_valid_plan()
        plan["outputs"]["raw_memory_path"] = "traces/raw/hermes_memory.jsonl"

        self.assert_plan_fails(plan, "raw_memory_path must end with .local.jsonl")

    def test_transcript_must_preserve_target_evaluator_boundary(self):
        plan = load_valid_plan()
        plan["smoke_transcripts"][0]["notes"] = "Hermes transcript fixture."

        self.assert_plan_fails(plan, "must preserve evaluator/target boundary")

    def test_session_boundary_rejects_private_memory(self):
        plan = load_valid_plan()
        plan["session_boundaries"][0]["private_memory_included"] = True

        self.assert_plan_fails(plan, "private_memory_included must equal False")

    def test_memory_check_rejects_raw_memory_reference(self):
        plan = load_valid_plan()
        plan["memory_checks"][0]["raw_memory_referenced"] = True

        self.assert_plan_fails(plan, "raw_memory_referenced must equal False")

    def test_memory_check_must_reference_generated_transcript(self):
        plan = load_valid_plan()
        plan["memory_checks"][0]["transcript_id"] = "missing-transcript"

        self.assert_plan_fails(plan, "transcript_id must reference a generated transcript")

    def assert_plan_fails(self, plan, message):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "traces" / "external") as temp_dir:
            path = Path(temp_dir) / "long_running_agent_adapter_plan.example.json"
            output_prefix = str(path.parent.relative_to(REPO_ROOT))
            plan["outputs"]["normalized_transcript_path"] = f"{output_prefix}/hermes_long_running_transcripts.example.jsonl"
            plan["outputs"]["session_boundary_path"] = f"{output_prefix}/hermes_session_boundaries.example.jsonl"
            plan["outputs"]["memory_check_path"] = f"{output_prefix}/hermes_memory_checks.example.jsonl"
            for check in plan["memory_checks"]:
                check["public_safe_evidence_path"] = plan["outputs"]["normalized_transcript_path"]
            write_json(path, plan)

            with self.assertRaisesRegex(LongRunningAgentAdapterError, message):
                generate_session_fixture(path)


if __name__ == "__main__":
    unittest.main()
