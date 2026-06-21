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

from validate_local_adapter_registry import (  # noqa: E402
    DEFAULT_REGISTRY_PATH,
    DEFAULT_SCHEMA_PATH,
    LocalAdapterRegistryValidationError,
    validate_registry,
)


def load_registry():
    return json.loads(DEFAULT_REGISTRY_PATH.read_text(encoding="utf-8"))


def write_registry(path, registry):
    path.write_text(json.dumps(registry, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def adapter_by_id(registry, adapter_id):
    return next(adapter for adapter in registry["adapters"] if adapter["adapter_id"] == adapter_id)


class LocalAdapterRegistryTests(unittest.TestCase):
    def validate_registry_object(self, registry):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "local_adapter_registry.json"
            write_registry(path, registry)
            return validate_registry(path, DEFAULT_SCHEMA_PATH)

    def assert_registry_error(self, registry, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "local_adapter_registry.json"
            write_registry(path, registry)
            with self.assertRaisesRegex(LocalAdapterRegistryValidationError, message):
                validate_registry(path, DEFAULT_SCHEMA_PATH)

    def test_committed_local_adapter_registry_validates(self):
        summary = validate_registry(DEFAULT_REGISTRY_PATH, DEFAULT_SCHEMA_PATH)

        self.assertEqual(summary["registry_path"], "targets/adapters/local_adapter_registry.json")
        self.assertEqual(summary["schema_path"], "schemas/local_adapter_registry.schema.json")
        self.assertEqual(summary["case_set_id"], "local_public_v1")
        self.assertEqual(summary["adapter_count"], 3)
        self.assertEqual(
            summary["adapter_ids"],
            ["local_openai_compatible_text_only", "manual_saved_output", "ollama_text_only"],
        )
        self.assertEqual(
            summary["live_local_required_adapters"],
            ["local_openai_compatible_text_only", "ollama_text_only"],
        )
        self.assertEqual(summary["live_local_required_flag"], "--live-local")

    def test_rejects_missing_required_adapter(self):
        registry = load_registry()
        registry["adapters"] = [
            adapter
            for adapter in registry["adapters"]
            if adapter["adapter_id"] != "ollama_text_only"
        ]

        self.assert_registry_error(registry, "must contain exactly")

    def test_rejects_ollama_credentials_requirement(self):
        registry = load_registry()
        ollama = adapter_by_id(registry, "ollama_text_only")
        ollama["credentials_required"] = True

        self.assert_registry_error(registry, "credentials_required")

    def test_rejects_live_local_adapter_without_live_flag_requirement(self):
        registry = load_registry()
        adapter = adapter_by_id(registry, "local_openai_compatible_text_only")
        adapter["live_local_required"] = False

        self.assert_registry_error(registry, "live_local_required")

    def test_rejects_quality_gate_execution_for_local_adapter(self):
        registry = load_registry()
        adapter = adapter_by_id(registry, "ollama_text_only")
        adapter["quality_gate_execution_allowed"] = True

        self.assert_registry_error(registry, "quality_gate_execution_allowed")

    def test_rejects_wrong_live_local_policy_flag(self):
        registry = load_registry()
        registry["live_execution_policy"]["live_local_required_flag"] = "--live"

        self.assert_registry_error(registry, "live_local_required_flag")

    def test_rejects_wrong_case_set_manifest(self):
        registry = load_registry()
        registry["case_set"]["manifest_path"] = "evals/benchmarks/local_public_v1/missing.json"

        self.assert_registry_error(registry, "does not exist")

    def test_rejects_unregistered_target_profile(self):
        registry = load_registry()
        adapter = adapter_by_id(registry, "manual_saved_output")
        adapter["target_profile"] = "unknown_local_target"

        self.assert_registry_error(registry, "target_profile")

    def test_rejects_manual_adapter_marked_live(self):
        registry = load_registry()
        manual = adapter_by_id(registry, "manual_saved_output")
        manual["live_local_required"] = True

        self.assert_registry_error(registry, "live_local_required")

    def test_rejects_missing_source_path(self):
        registry = load_registry()
        registry["source_paths"] = ["docs/missing-source.md"]

        self.assert_registry_error(registry, "does not exist")

    def test_original_registry_object_is_not_mutated_by_helper_copy(self):
        registry = load_registry()
        copied = copy.deepcopy(registry)

        self.validate_registry_object(copied)

        self.assertEqual(copied, registry)
        self.assertEqual(registry, load_registry())


if __name__ == "__main__":
    unittest.main()
