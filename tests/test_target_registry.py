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

from target_registry import (
    TargetRegistryError,
    allowed_adapter_output_profiles,
    allowed_manual_output_profiles,
    quality_gate_profile_names,
    target_profile_names,
    validate_target_registry,
)


TARGET_REGISTRY_PATH = REPO_ROOT / "targets/target_registry.json"


def load_registry():
    return json.loads(TARGET_REGISTRY_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2), encoding="utf-8")


class TargetRegistryTests(unittest.TestCase):
    def test_committed_target_registry_validates(self):
        summary = validate_target_registry(path=TARGET_REGISTRY_PATH)

        self.assertEqual(summary["registry_path"], "targets/target_registry.json")
        self.assertEqual(summary["target_count"], 4)
        self.assertEqual(summary["quality_gate_profile_count"], 3)

    def test_quality_gate_profiles_stay_deterministic_mock_profiles(self):
        self.assertEqual(
            quality_gate_profile_names(),
            [
                "generic_assistant",
                "openclaw_reference_agent",
                "strict_approval_agent",
            ],
        )

    def test_text_only_candidate_is_registered_for_saved_outputs_not_quality_gate(self):
        self.assertIn("text_only_adapter_candidate", target_profile_names())
        self.assertIn("text_only_adapter_candidate", allowed_manual_output_profiles())
        self.assertIn("text_only_adapter_candidate", allowed_adapter_output_profiles())
        self.assertNotIn("text_only_adapter_candidate", quality_gate_profile_names())

    def test_duplicate_target_profile_is_rejected(self):
        registry = load_registry()
        duplicate = copy.deepcopy(registry["targets"][0])
        registry["targets"].append(duplicate)

        self.assert_registry_fails(registry, "duplicate value")

    def test_schema_rejects_unknown_target_kind(self):
        registry = load_registry()
        registry["targets"][0]["target_kind"] = "unknown_target_kind"

        self.assert_registry_fails(registry, "target_kind must be one of")

    def test_schema_rejects_unexpected_target_field(self):
        registry = load_registry()
        registry["targets"][0]["unexpected"] = True

        self.assert_registry_fails(registry, "unexpected fields: unexpected")

    def test_missing_profile_path_is_rejected(self):
        registry = load_registry()
        registry["targets"][0]["profile_path"] = "targets/profiles/missing.md"

        self.assert_registry_fails(registry, "profile_path does not exist")

    def test_quality_gate_profile_must_be_mock_profile(self):
        registry = load_registry()
        registry["targets"][3]["quality_gate_profile"] = True

        self.assert_registry_fails(registry, "quality_gate_profile requires target_kind=mock_profile")

    def assert_registry_fails(self, registry, message=None):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "target_registry.json"
            write_json(path, registry)

            context = (
                self.assertRaisesRegex(TargetRegistryError, message)
                if message
                else self.assertRaises(TargetRegistryError)
            )
            with context:
                validate_target_registry(path=path)


if __name__ == "__main__":
    unittest.main()
