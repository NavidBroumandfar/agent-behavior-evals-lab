import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from validate_harness_bridge_plan import (  # noqa: E402
    HarnessBridgePlanValidationError,
    validate_plan,
)


PLAN_PATH = REPO_ROOT / "traces/external/harness_bridge_plan.example.json"
SCHEMA_PATH = REPO_ROOT / "schemas/harness_bridge_plan.schema.json"


def load_valid_plan():
    return json.loads(PLAN_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2), encoding="utf-8")


class HarnessBridgePlanValidationTests(unittest.TestCase):
    def test_committed_harness_bridge_plan_validates(self):
        summary = validate_plan(PLAN_PATH, SCHEMA_PATH)

        self.assertEqual(summary["plan_path"], "traces/external/harness_bridge_plan.example.json")
        self.assertEqual(summary["schema_path"], "schemas/harness_bridge_plan.schema.json")
        self.assertEqual(summary["plan_id"], "m37_optional_harness_integration_decision")
        self.assertEqual(summary["target_runtime"], "openclaw")
        self.assertEqual(summary["decision"], "defer_harness_integration")
        self.assertFalse(summary["runtime_native_state_required"])
        self.assertEqual(summary["evidence_count"], 3)
        self.assertFalse(summary["harness_execution_in_quality_gate"])

    def test_missing_top_level_field_is_rejected_by_schema(self):
        plan = load_valid_plan()
        del plan["decision"]

        self.assert_plan_fails(plan, "missing required fields: decision")

    def test_invalid_created_at_date_is_rejected(self):
        plan = load_valid_plan()
        plan["created_at"] = "2026-99-20T00:00:00Z"

        self.assert_plan_fails(plan, "created_at must be a valid UTC timestamp")

    def test_missing_evidence_path_is_rejected(self):
        plan = load_valid_plan()
        plan["evidence"][0]["path"] = "docs/milestones/missing-closeout.md"

        self.assert_plan_fails(plan, "path does not exist")

    def test_absolute_evidence_path_is_rejected(self):
        plan = load_valid_plan()
        plan["evidence"][0]["path"] = "/tmp/not-allowed.md"

        self.assert_plan_fails(plan, "must be a repository-relative path")

    def test_local_only_evidence_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_supporting_files(root)
            plan = load_valid_plan()
            plan["evidence"][0]["path"] = "traces/raw/sandbox.local.jsonl"
            write_json(root / "plan.json", plan)

            with self.assertRaisesRegex(HarnessBridgePlanValidationError, "must not reference local-only output"):
                validate_plan(root / "plan.json", SCHEMA_PATH, repo_root=root)

    def test_duplicate_evidence_id_is_rejected(self):
        plan = load_valid_plan()
        plan["evidence"][1]["evidence_id"] = plan["evidence"][0]["evidence_id"]

        self.assert_plan_fails(plan, "evidence_id duplicate value")

    def test_non_deferred_decision_requires_runtime_native_state(self):
        plan = load_valid_plan()
        plan["decision"] = "prepare_non_gated_bridge_only"
        plan["preferred_paths"].append("harness_bridge")

        self.assert_plan_fails(plan, "must be defer_harness_integration")

    def test_bridge_preparation_decision_requires_harness_preferred_path(self):
        plan = load_valid_plan()
        plan["runtime_native_state_required"] = True
        plan["decision"] = "prepare_non_gated_bridge_only"

        self.assert_plan_fails(plan, "must include harness_bridge")

    def test_deferred_decision_requires_non_harness_preferred_path(self):
        plan = load_valid_plan()
        plan["preferred_paths"] = ["harness_bridge"]

        self.assert_plan_fails(plan, "must include at least one non-harness path")

    def test_quality_gate_harness_execution_is_rejected(self):
        plan = load_valid_plan()
        plan["quality_gate"]["harness_execution_in_quality_gate"] = True

        self.assert_plan_fails(plan, "harness_execution_in_quality_gate must be false")

    def test_bridge_contract_must_keep_private_logs_blocked(self):
        plan = load_valid_plan()
        plan["bridge_contract"]["private_logs_allowed"] = True

        self.assert_plan_fails(plan, "private_logs_allowed must be false")

    def test_bridge_contract_requires_local_raw_pattern(self):
        plan = load_valid_plan()
        plan["bridge_contract"]["raw_output_path_pattern"] = "traces/raw/*.jsonl"

        self.assert_plan_fails(plan, "raw_output_path_pattern")

    def test_safety_assertions_reject_live_execution(self):
        plan = load_valid_plan()
        plan["safety_assertions"]["live_execution"] = True

        self.assert_plan_fails(plan, "live_execution must equal False")

    def test_missing_blocked_capability_is_rejected(self):
        plan = load_valid_plan()
        plan["blocked_capabilities"].remove("shell_execution")

        self.assert_plan_fails(plan, "missing required blocked capabilities: shell_execution")

    def assert_plan_fails(self, plan, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "harness_bridge_plan.json"
            write_json(path, plan)

            with self.assertRaisesRegex(HarnessBridgePlanValidationError, message):
                validate_plan(path, SCHEMA_PATH)

    @staticmethod
    def write_supporting_files(root):
        for relative_path in [
            "docs/milestones/m35-openclaw-saved-transcript-pilot-closeout.md",
            "docs/milestones/m36-controlled-live-agent-sandbox-closeout.md",
            "reports/comparisons/openclaw_saved_transcript_pilot_report.md",
            "traces/raw/sandbox.local.jsonl",
        ]:
            path = root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("public-safe test support file\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
