import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from live_local_harness import (  # noqa: E402
    LIVE_LOCAL_REQUIRED_ENV,
    LiveLocalHarnessError,
    build_run_plan,
    prompt_messages,
    run_live_local_plan,
)


class FakeLocalClient:
    def __init__(self, output_text="Fake local answer.", fail=False):
        self.output_text = output_text
        self.fail = fail
        self.availability_checks = 0
        self.generate_calls = 0

    def check_model_available(self):
        self.availability_checks += 1

    def generate(self, case, *, timeout_seconds):
        self.generate_calls += 1
        if self.fail:
            raise RuntimeError("fake generation failure")
        return f"{self.output_text} {case['case_id']}"


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class LiveLocalHarnessTests(unittest.TestCase):
    def build_plan(self, root, **overrides):
        args = {
            "adapter_id": "ollama_text_only",
            "model": "fake-local-model",
            "split": "smoke",
            "output_path": root / "fake_live_local.local.jsonl",
            "run_id": "m57_fake_live_local",
            "created_at": "2026-06-21T00:00:00Z",
            "max_cases": 2,
            "mode": "live_local",
            "live_local_flag_present": True,
            "live_local_env_present": True,
        }
        args.update(overrides)
        return build_run_plan(**args)

    def test_plan_only_selects_smoke_cases_without_live_flags(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = build_run_plan(
                adapter_id="ollama_text_only",
                model="fake-local-model",
                split="smoke",
                output_path=root / "plan.local.jsonl",
                run_id="m57_plan_only_unit",
                created_at="2026-06-21T00:00:00Z",
                mode="plan_only",
            )

            self.assertEqual(plan["mode"], "plan_only")
            self.assertEqual(plan["case_set"]["case_count"], 21)
            self.assertFalse(plan["execution_controls"]["live_local_flag_present"])
            self.assertFalse(plan["execution_controls"]["live_local_env_present"])
            self.assertFalse(plan["safety_assertions"]["live_execution"])

    def test_live_execution_requires_flag_and_environment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = self.build_plan(
                root,
                live_local_env_present=False,
            )

            with self.assertRaisesRegex(LiveLocalHarnessError, LIVE_LOCAL_REQUIRED_ENV):
                run_live_local_plan(plan, env={}, client=FakeLocalClient())

    def test_fake_client_writes_pending_live_local_raw_records_and_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = self.build_plan(root)
            client = FakeLocalClient("Precision and recall are evaluation metrics.")

            summary = run_live_local_plan(plan, env={LIVE_LOCAL_REQUIRED_ENV: "1"}, client=client)

            self.assertEqual(summary["run_status"], "succeeded")
            self.assertEqual(summary["records_written"], 2)
            self.assertEqual(client.availability_checks, 1)
            self.assertEqual(client.generate_calls, 2)

            raw_records = read_jsonl(root / "fake_live_local.local.jsonl")
            self.assertEqual(len(raw_records), 2)
            self.assertTrue(all(record["review_status"] == "pending_review" for record in raw_records))
            self.assertTrue(all(record["provenance"]["live_execution"] for record in raw_records))
            self.assertTrue(all(not record["provenance"]["external_actions"] for record in raw_records))
            self.assertEqual(
                {record["metadata"]["harness_id"] for record in raw_records},
                {"live_local_text_only_harness"},
            )
            self.assertEqual({record["metadata"]["run_status"] for record in raw_records}, {"succeeded"})

            metadata = json.loads((root / "fake_live_local.metadata.local.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["results"]["succeeded"], 2)
            self.assertEqual(metadata["results"]["failed"], 0)
            self.assertFalse(metadata["ranking_excluded"])

    def test_generation_failures_retry_and_abort_with_partial_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plan = self.build_plan(root, max_cases=3, max_attempts=2, max_failures=1)
            client = FakeLocalClient(fail=True)

            summary = run_live_local_plan(plan, env={LIVE_LOCAL_REQUIRED_ENV: "true"}, client=client)

            self.assertEqual(summary["run_status"], "partial")
            self.assertEqual(summary["records_written"], 1)
            self.assertEqual(summary["failed"], 3)
            self.assertEqual(summary["skipped"], 2)
            self.assertEqual(client.generate_calls, 2)

            raw_records = read_jsonl(root / "fake_live_local.local.jsonl")
            self.assertEqual(raw_records[0]["metadata"]["run_status"], "failed")
            self.assertEqual(raw_records[0]["metadata"]["attempt_count"], 2)
            self.assertTrue(raw_records[0]["metadata"]["ranking_excluded"])

    def test_prompt_template_disables_tools_in_system_message(self):
        messages = prompt_messages({"user_prompt": "Explain JSONL.", "case_id": "LPB-SAFE-001"})

        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("Tools are disabled", messages[0]["content"])
        self.assertEqual(messages[1]["content"], "Explain JSONL.")


if __name__ == "__main__":
    unittest.main()
