import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from validate_runtime_trial_plan import (  # noqa: E402
    RuntimeTrialPlanValidationError,
    validate_plan,
)


PLAN_PATH = REPO_ROOT / "traces/external/non_gated_runtime_trial_plan.example.json"
SCHEMA_PATH = REPO_ROOT / "schemas/runtime_trial_plan.schema.json"


def load_valid_plan():
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class RuntimeTrialPlanValidationTests(unittest.TestCase):
    def test_committed_runtime_trial_plan_validates(self):
        summary = validate_plan(PLAN_PATH, SCHEMA_PATH)

        self.assertEqual(summary["plan_path"], "traces/external/non_gated_runtime_trial_plan.example.json")
        self.assertEqual(summary["schema_path"], "schemas/runtime_trial_plan.schema.json")
        self.assertEqual(summary["plan_id"], "m44_optional_non_gated_runtime_trial")
        self.assertEqual(summary["target_runtime"], "openclaw")
        self.assertEqual(summary["status"], "manual_trial_deferred")
        self.assertEqual(summary["decision"], "defer_live_runtime_trial")
        self.assertEqual(summary["case_id"], "APPROVAL-014")
        self.assertFalse(summary["runtime_native_evidence_needed"])
        self.assertFalse(summary["runtime_execution_in_quality_gate"])

    def test_missing_top_level_field_is_rejected_by_schema(self):
        plan = load_valid_plan()
        del plan["trial_controls"]

        self.assert_plan_fails(plan, "missing required fields: trial_controls")

    def test_invalid_created_at_date_is_rejected(self):
        plan = load_valid_plan()
        plan["created_at"] = "2026-99-20T00:00:00Z"

        self.assert_plan_fails(plan, "created_at must be a valid UTC timestamp")

    def test_prompt_count_must_be_one(self):
        plan = load_valid_plan()
        plan["prepared_prompt"]["prompt_count"] = 2

        self.assert_plan_fails(plan, "prompt_count must equal 1")

    def test_unknown_case_id_is_rejected(self):
        plan = load_valid_plan()
        plan["prepared_prompt"]["case_id"] = "UNKNOWN-001"

        self.assert_plan_fails(plan, "case_id is not in case_source_path")

    def test_runtime_execution_in_quality_gate_is_rejected(self):
        plan = load_valid_plan()
        plan["quality_gate"]["runtime_execution_in_quality_gate"] = True

        self.assert_plan_fails(plan, "runtime_execution_in_quality_gate must be false")

    def test_adapter_metadata_case_must_match_prepared_prompt(self):
        plan = load_valid_plan()
        plan["prepared_prompt"]["case_id"] = "APPROVAL-001"

        self.assert_plan_fails(plan, "case_ids must match prepared_prompt.case_id")

    def test_raw_output_validation_in_quality_gate_is_rejected(self):
        plan = load_valid_plan()
        plan["quality_gate"]["raw_output_validation_in_quality_gate"] = True

        self.assert_plan_fails(plan, "raw_output_validation_in_quality_gate must be false")

    def test_network_access_is_rejected(self):
        plan = load_valid_plan()
        plan["trial_controls"]["network_access"] = True

        self.assert_plan_fails(plan, "network_access must be false")

    def test_tools_must_stay_disabled(self):
        plan = load_valid_plan()
        plan["trial_controls"]["tools_disabled"] = False

        self.assert_plan_fails(plan, "tools_disabled must be true")

    def test_raw_outputs_are_not_committable(self):
        plan = load_valid_plan()
        plan["output_policy"]["raw_outputs_committable"] = True

        self.assert_plan_fails(plan, "raw_outputs_committable must be false")

    def test_raw_output_path_must_be_local_jsonl_under_traces_raw(self):
        invalid_paths = [
            "traces/raw/m44_non_gated_runtime_trial.jsonl",
            "traces/external/m44_non_gated_runtime_trial.local.jsonl",
            "../m44_non_gated_runtime_trial.local.jsonl",
        ]

        for raw_output_path in invalid_paths:
            with self.subTest(raw_output_path=raw_output_path):
                plan = load_valid_plan()
                plan["output_policy"]["raw_output_path"] = raw_output_path

                self.assert_plan_fails(plan, "raw_output_path")

    def test_closeout_decision_must_match_runtime_evidence_need(self):
        plan = load_valid_plan()
        plan["closeout_decision"]["decision"] = "manual_trial_allowed_after_human_review"

        self.assert_plan_fails(plan, "decision must be defer_live_runtime_trial")

    def test_safety_assertions_reject_live_execution(self):
        plan = load_valid_plan()
        plan["safety_assertions"]["live_execution"] = True

        self.assert_plan_fails(plan, "live_execution must be False")

    def test_missing_blocked_capability_is_rejected(self):
        plan = load_valid_plan()
        plan["blocked_capabilities"].remove("provider_execution")

        self.assert_plan_fails(plan, "missing required blocked capabilities: provider_execution")

    def assert_plan_fails(self, plan, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "runtime_trial_plan.json"
            write_json(path, plan)

            with self.assertRaisesRegex(RuntimeTrialPlanValidationError, message):
                validate_plan(path, SCHEMA_PATH)


if __name__ == "__main__":
    unittest.main()
