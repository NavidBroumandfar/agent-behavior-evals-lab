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

from runtime_stability_profile import (  # noqa: E402
    DEFAULT_PROFILE_PATH,
    RuntimeStabilityProfileError,
    validate_runtime_stability_profile,
)


def load_valid_profile():
    return json.loads(DEFAULT_PROFILE_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class RuntimeStabilityProfileTests(unittest.TestCase):
    def test_committed_profile_validates(self):
        summary = validate_runtime_stability_profile()

        self.assertEqual(summary["profile_path"], "traces/external/runtime_stability_profile.example.json")
        self.assertEqual(summary["schema_path"], "schemas/runtime_stability_profile.schema.json")
        self.assertEqual(summary["profile_id"], "m85_runtime_stability_profile")
        self.assertEqual(summary["runtime"], "ollama")
        self.assertEqual(summary["model_count"], 7)
        self.assertEqual(summary["deferred_model"], "gemma4:latest")
        self.assertEqual(summary["deferred_model_status"], "deferred_after_swap_activity")
        self.assertFalse(summary["quality_gate_live_execution"])

    def test_live_execution_in_quality_gate_is_rejected(self):
        profile = load_valid_profile()
        profile["quality_gate"]["live_local_execution_in_quality_gate"] = True

        self.assert_profile_fails(profile, "live_local_execution_in_quality_gate must equal False")

    def test_raw_output_claim_is_rejected(self):
        profile = load_valid_profile()
        profile["safety_assertions"]["contains_raw_outputs"] = True

        self.assert_profile_fails(profile, "contains_raw_outputs must equal False")

    def test_gemma4_must_remain_deferred(self):
        profile = load_valid_profile()
        gemma_profile = self.model_profile(profile, "gemma4:latest")
        gemma_profile["ranking_eligible"] = True

        self.assert_profile_fails(profile, "ranking_eligible must be false")

    def test_qwen_ranked_target_cannot_be_demoted(self):
        profile = load_valid_profile()
        qwen_profile = self.model_profile(profile, "qwen3.5:2b-q4_K_M")
        qwen_profile["ranking_eligible"] = False

        self.assert_profile_fails(profile, "ranking_eligible must be true for ranked model")

    def test_cloud_label_target_cannot_support_local_claim(self):
        profile = load_valid_profile()
        cloud_profile = self.model_profile(profile, "gemma4:31b-cloud")
        cloud_profile["ranking_eligible"] = True

        self.assert_profile_fails(profile, "ranking_eligible must be false")

    def test_missing_swap_stop_criterion_is_rejected(self):
        profile = load_valid_profile()
        profile["stop_criteria"] = [
            criterion
            for criterion in profile["stop_criteria"]
            if criterion["criterion_id"] != "memory_pressure_or_swap_activity"
        ]

        self.assert_profile_fails(profile, "missing stop criteria: memory_pressure_or_swap_activity")

    def test_observed_blocker_cannot_be_ranking_evidence(self):
        profile = load_valid_profile()
        profile["observed_blockers"][0]["ranking_evidence"] = True

        self.assert_profile_fails(profile, "ranking_evidence must be false")

    def test_source_paths_cannot_reference_raw_artifacts(self):
        profile = load_valid_profile()
        profile["source_paths"].append("traces/raw/m77_gemma4_latest_extended.plan.local.json")

        self.assert_profile_fails(profile, "must not reference raw or private local artifacts")

    def test_duplicate_model_profiles_are_rejected(self):
        profile = load_valid_profile()
        profile["model_profiles"].append(copy.deepcopy(profile["model_profiles"][0]))

        self.assert_profile_fails(profile, "duplicate value")

    def model_profile(self, profile, model):
        for model_profile in profile["model_profiles"]:
            if model_profile["model"] == model:
                return model_profile
        self.fail(f"missing model profile: {model}")

    def assert_profile_fails(self, profile, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "runtime_stability_profile.example.json"
            write_json(path, profile)

            with self.assertRaisesRegex(RuntimeStabilityProfileError, message):
                validate_runtime_stability_profile(path)


if __name__ == "__main__":
    unittest.main()
