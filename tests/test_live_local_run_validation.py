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

from validate_live_local_run import (  # noqa: E402
    DEFAULT_PLAN_PATH,
    DEFAULT_SCHEMA_PATH,
    LiveLocalRunValidationError,
    validate_live_local_run_plan,
)


def load_plan():
    return json.loads(DEFAULT_PLAN_PATH.read_text(encoding="utf-8"))


def write_plan(path, plan):
    path.write_text(json.dumps(plan, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class LiveLocalRunValidationTests(unittest.TestCase):
    def assert_plan_fails(self, plan, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "live_local_run_plan.json"
            write_plan(path, plan)
            with self.assertRaisesRegex(LiveLocalRunValidationError, message):
                validate_live_local_run_plan(path, DEFAULT_SCHEMA_PATH)

    def test_committed_live_local_run_plan_validates(self):
        summary = validate_live_local_run_plan(DEFAULT_PLAN_PATH, DEFAULT_SCHEMA_PATH)

        self.assertEqual(summary["plan_path"], "traces/external/live_local_run_plan.example.json")
        self.assertEqual(summary["schema_path"], "schemas/live_local_run.schema.json")
        self.assertEqual(summary["run_id"], "m57_live_local_text_only_harness_plan")
        self.assertEqual(summary["adapter_id"], "ollama_text_only")
        self.assertEqual(summary["case_set_id"], "local_public_v1")
        self.assertEqual(summary["benchmark_split"], "smoke")
        self.assertEqual(summary["case_count"], 21)
        self.assertEqual(summary["mode"], "plan_only")

    def test_rejects_committed_plan_with_live_mode(self):
        plan = load_plan()
        plan["mode"] = "live_local"
        plan["safety_assertions"]["live_execution"] = True
        plan["execution_controls"]["dry_run_plan_in_quality_gate"] = False

        self.assert_plan_fails(plan, "mode must be plan_only")

    def test_rejects_committed_plan_with_live_flags_present(self):
        plan = load_plan()
        plan["execution_controls"]["live_local_flag_present"] = True

        self.assert_plan_fails(plan, "live_local_flag_present")

    def test_rejects_non_loopback_endpoint(self):
        plan = load_plan()
        plan["adapter"]["endpoint"] = "https://example.com/v1/chat/completions"

        self.assert_plan_fails(plan, "endpoint")

    def test_rejects_case_not_in_selected_split(self):
        plan = load_plan()
        plan["case_set"]["case_ids"] = copy.copy(plan["case_set"]["case_ids"])
        plan["case_set"]["case_ids"][0] = "LPB-SAFE-004"

        self.assert_plan_fails(plan, "not in split smoke")

    def test_rejects_raw_output_path_outside_traces_raw(self):
        plan = load_plan()
        plan["outputs"]["raw_output_path"] = "traces/external/m57_live_local_outputs.local.jsonl"

        self.assert_plan_fails(plan, "raw_output_path")


if __name__ == "__main__":
    unittest.main()
