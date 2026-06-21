import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from openclaw_harness_adapter import (  # noqa: E402
    DEFAULT_PLAN_PATH,
    OpenClawHarnessAdapterError,
    generate_smoke_fixture,
)
from reporting_utils import load_jsonl_records  # noqa: E402


def load_valid_plan():
    return json.loads(DEFAULT_PLAN_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class OpenClawHarnessAdapterTests(unittest.TestCase):
    def test_committed_plan_generates_public_safe_smoke_fixture(self):
        summary = generate_smoke_fixture(DEFAULT_PLAN_PATH)

        self.assertEqual(summary["adapter_id"], "m63_openclaw_live_harness_adapter")
        self.assertEqual(summary["target_runtime"], "openclaw")
        self.assertEqual(summary["target_profile"], "openclaw_reference_agent")
        self.assertEqual(summary["transcripts"], 1)
        self.assertEqual(summary["tool_summaries"], 1)
        self.assertFalse(summary["live_openclaw_execution_in_quality_gate"])

        transcript_records = load_jsonl_records(REPO_ROOT / summary["transcript_output_path"])
        tool_summary_records = load_jsonl_records(REPO_ROOT / summary["tool_summary_output_path"])
        self.assertEqual(transcript_records[0]["source_label"], "openclaw_harness_smoke_public_safe")
        self.assertFalse(transcript_records[0]["provenance"]["live_execution"])
        self.assertFalse(tool_summary_records[0]["safety_assertions"]["tool_execution"])

    def test_live_execution_in_quality_gate_is_rejected(self):
        plan = load_valid_plan()
        plan["quality_gate"]["live_openclaw_execution_in_quality_gate"] = True

        self.assert_plan_fails(plan, "live_openclaw_execution_in_quality_gate must be false")

    def test_tool_execution_in_quality_gate_is_rejected(self):
        plan = load_valid_plan()
        plan["quality_gate"]["tool_execution_in_quality_gate"] = True

        self.assert_plan_fails(plan, "tool_execution_in_quality_gate must be false")

    def test_runtime_controls_must_be_opt_in(self):
        plan = load_valid_plan()
        plan["runtime_controls"]["opt_in_required"] = False

        self.assert_plan_fails(plan, "opt_in_required must be true")

    def test_raw_output_must_be_local_only(self):
        plan = load_valid_plan()
        plan["outputs"]["raw_output_path"] = "traces/raw/openclaw_harness_smoke.jsonl"

        self.assert_plan_fails(plan, "raw_output_path must end with .local.jsonl")

    def test_openclaw_must_remain_target_not_evaluator(self):
        plan = load_valid_plan()
        plan["smoke_transcript"]["notes"] = "OpenClaw smoke fixture."

        self.assert_plan_fails(plan, "must preserve evaluator/target boundary")

    def test_transcript_case_must_match_case_selection(self):
        plan = load_valid_plan()
        plan["smoke_transcript"]["case_id"] = "APPROVAL-001"

        self.assert_plan_fails(plan, "smoke_transcript.case_id must be selected")

    def test_tool_summary_source_must_reference_plan(self):
        plan = load_valid_plan()
        plan["tool_call_summaries"][0]["source_evidence"]["source_path"] = "traces/external/tool_sandbox_contract.example.json"

        self.assert_plan_fails(plan, "source_path must reference plan")

    def assert_plan_fails(self, plan, message):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "traces" / "external") as temp_dir:
            path = Path(temp_dir) / "openclaw_harness_adapter_plan.example.json"
            output_prefix = str(path.parent.relative_to(REPO_ROOT))
            plan["outputs"]["normalized_transcript_path"] = f"{output_prefix}/openclaw_harness_smoke_transcript.example.jsonl"
            plan["outputs"]["tool_summary_path"] = f"{output_prefix}/openclaw_harness_tool_summaries.example.jsonl"
            if (
                plan["tool_call_summaries"][0]["source_evidence"]["source_path"]
                == "traces/external/openclaw_harness_adapter_plan.example.json"
            ):
                plan["tool_call_summaries"][0]["source_evidence"]["source_path"] = str(path.relative_to(REPO_ROOT))
            write_json(path, plan)

            with self.assertRaisesRegex(OpenClawHarnessAdapterError, message):
                generate_smoke_fixture(path)


if __name__ == "__main__":
    unittest.main()
