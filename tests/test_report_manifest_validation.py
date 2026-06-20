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

from validate_report_manifest import ReportManifestValidationError, validate_manifest


REPORT_MANIFEST_PATH = REPO_ROOT / "reports/comparisons/report_manifest.json"
REPORT_MANIFEST_SCHEMA_PATH = REPO_ROOT / "schemas/report_manifest.schema.json"


def load_manifest_object():
    return json.loads(REPORT_MANIFEST_PATH.read_text(encoding="utf-8"))


def write_manifest(path, manifest):
    path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class ReportManifestValidationTests(unittest.TestCase):
    def validate_manifest_object(self, manifest):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "report_manifest.json"
            write_manifest(manifest_path, manifest)
            return validate_manifest(manifest_path, REPORT_MANIFEST_SCHEMA_PATH)

    def assert_manifest_error(self, manifest, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "report_manifest.json"
            write_manifest(manifest_path, manifest)
            with self.assertRaisesRegex(ReportManifestValidationError, message):
                validate_manifest(manifest_path, REPORT_MANIFEST_SCHEMA_PATH)

    def test_committed_report_manifest_validates(self):
        summary = validate_manifest(REPORT_MANIFEST_PATH, REPORT_MANIFEST_SCHEMA_PATH)

        self.assertEqual(summary["manifest_path"], "reports/comparisons/report_manifest.json")
        self.assertEqual(summary["schema_path"], "schemas/report_manifest.schema.json")
        self.assertEqual(summary["artifact_count"], 19)
        self.assertEqual(summary["markdown_report_count"], 14)
        self.assertEqual(summary["json_snapshot_count"], 5)
        self.assertEqual(summary["quality_gate_artifact_count"], 19)

    def test_rejects_missing_required_top_level_field(self):
        manifest = load_manifest_object()
        del manifest["purpose"]

        self.assert_manifest_error(manifest, "missing required fields: purpose")

    def test_rejects_unexpected_artifact_field(self):
        manifest = load_manifest_object()
        manifest["report_artifacts"][0]["unexpected"] = True

        self.assert_manifest_error(manifest, "unexpected fields: unexpected")

    def test_rejects_duplicate_artifact_id(self):
        manifest = load_manifest_object()
        manifest["report_artifacts"][1]["artifact_id"] = manifest["report_artifacts"][0]["artifact_id"]

        self.assert_manifest_error(manifest, "artifact_id duplicate value")

    def test_rejects_duplicate_artifact_path(self):
        manifest = load_manifest_object()
        manifest["report_artifacts"][1]["path"] = manifest["report_artifacts"][0]["path"]

        self.assert_manifest_error(manifest, "path duplicate value")

    def test_rejects_missing_report_path(self):
        manifest = load_manifest_object()
        manifest["report_artifacts"][0]["path"] = "reports/comparisons/missing_report.md"

        self.assert_manifest_error(manifest, "path does not exist")

    def test_rejects_missing_quality_gate_artifact(self):
        manifest = load_manifest_object()
        manifest["report_artifacts"] = manifest["report_artifacts"][1:]

        self.assert_manifest_error(manifest, "missing quality-gate artifacts: reports/baseline_report.md")

    def test_rejects_quality_gate_artifact_not_included(self):
        manifest = load_manifest_object()
        manifest["report_artifacts"][0]["quality_gate_included"] = False

        self.assert_manifest_error(manifest, "missing quality-gate artifacts: reports/baseline_report.md")

    def test_rejects_markdown_artifact_with_json_path(self):
        manifest = load_manifest_object()
        manifest["report_artifacts"][0]["path"] = "reports/comparisons/baseline_regression_snapshot.json"

        self.assert_manifest_error(manifest, "must use .md for markdown_report artifacts")

    def test_rejects_missing_generator_script(self):
        manifest = load_manifest_object()
        manifest["report_artifacts"][0]["generated_by"] = "src/missing_report_generator.py"

        self.assert_manifest_error(manifest, "generated_by does not exist")

    def test_rejects_generator_that_is_not_python_script(self):
        manifest = load_manifest_object()
        manifest["report_artifacts"][0]["generated_by"] = "README.md"

        self.assert_manifest_error(manifest, "generated_by must point to a Python script")

    def test_rejects_missing_input_path(self):
        manifest = load_manifest_object()
        manifest["report_artifacts"][0]["input_paths"] = ["traces/scored/missing_trace.jsonl"]

        self.assert_manifest_error(manifest, "input_paths\\[0\\] does not exist")

    def test_rejects_snapshot_dependency_not_in_manifest(self):
        manifest = load_manifest_object()
        manifest["report_artifacts"][0]["snapshot_dependency_paths"] = [
            "reports/comparisons/report_manifest.json"
        ]

        self.assert_manifest_error(manifest, "must reference a json_snapshot artifact")

    def test_rejects_snapshot_dependency_with_non_json_suffix(self):
        manifest = load_manifest_object()
        manifest["report_artifacts"][0]["snapshot_dependency_paths"] = [
            "reports/comparisons/profile_comparison_report.md"
        ]

        self.assert_manifest_error(manifest, "must point to a JSON snapshot")

    def test_rejects_unsafe_safety_assertion(self):
        manifest = load_manifest_object()
        manifest["report_artifacts"][0]["safety_assertions"]["live_execution"] = True

        self.assert_manifest_error(manifest, "live_execution must equal False")

    def test_original_manifest_object_is_not_mutated_by_helper_copy(self):
        manifest = load_manifest_object()
        copied_manifest = copy.deepcopy(manifest)

        self.validate_manifest_object(copied_manifest)

        self.assertEqual(manifest, load_manifest_object())


if __name__ == "__main__":
    unittest.main()
