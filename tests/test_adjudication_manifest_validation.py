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

from validate_adjudication_manifest import AdjudicationManifestValidationError, validate_manifest


ADJUDICATION_MANIFEST_PATH = REPO_ROOT / "traces/external/adjudication_manifest.json"
ADJUDICATION_MANIFEST_SCHEMA_PATH = REPO_ROOT / "schemas/adjudication_manifest.schema.json"


def load_manifest_object():
    return json.loads(ADJUDICATION_MANIFEST_PATH.read_text(encoding="utf-8"))


def write_manifest(path, manifest):
    path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class AdjudicationManifestValidationTests(unittest.TestCase):
    def validate_manifest_object(self, manifest):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "adjudication_manifest.json"
            write_manifest(manifest_path, manifest)
            return validate_manifest(manifest_path, ADJUDICATION_MANIFEST_SCHEMA_PATH)

    def assert_manifest_error(self, manifest, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "adjudication_manifest.json"
            write_manifest(manifest_path, manifest)
            with self.assertRaisesRegex(AdjudicationManifestValidationError, message):
                validate_manifest(manifest_path, ADJUDICATION_MANIFEST_SCHEMA_PATH)

    def test_committed_adjudication_manifest_validates(self):
        summary = validate_manifest(ADJUDICATION_MANIFEST_PATH, ADJUDICATION_MANIFEST_SCHEMA_PATH)

        self.assertEqual(summary["manifest_path"], "traces/external/adjudication_manifest.json")
        self.assertEqual(summary["schema_path"], "schemas/adjudication_manifest.schema.json")
        self.assertEqual(summary["fixture_count"], 10)
        self.assertEqual(summary["quality_gate_fixture_count"], 10)
        self.assertEqual(summary["quality_gate_threshold_count"], 19)

    def test_threshold_block_is_optional(self):
        manifest = load_manifest_object()
        del manifest["quality_gate_thresholds"]

        summary = self.validate_manifest_object(manifest)

        self.assertEqual(summary["quality_gate_threshold_count"], 0)

    def test_rejects_missing_required_top_level_field(self):
        manifest = load_manifest_object()
        del manifest["purpose"]

        self.assert_manifest_error(manifest, "missing required fields: purpose")

    def test_rejects_unexpected_top_level_field(self):
        manifest = load_manifest_object()
        manifest["unexpected"] = True

        self.assert_manifest_error(manifest, "unexpected fields: unexpected")

    def test_rejects_invalid_threshold_type(self):
        manifest = load_manifest_object()
        manifest["quality_gate_thresholds"]["min_review_coverage"] = "5.0"

        self.assert_manifest_error(manifest, "min_review_coverage must be number")

    def test_rejects_out_of_range_threshold(self):
        manifest = load_manifest_object()
        manifest["quality_gate_thresholds"]["min_category_review_coverage"]["approval_gated"] = 101.0

        self.assert_manifest_error(manifest, "approval_gated must be <= 100")

    def test_rejects_unsafe_safety_assertion(self):
        manifest = load_manifest_object()
        manifest["adjudication_fixtures"][0]["safety_assertions"]["live_execution"] = True

        self.assert_manifest_error(manifest, "live_execution must equal False")

    def test_rejects_quality_gate_blocked_review_status(self):
        manifest = load_manifest_object()
        manifest["adjudication_fixtures"][0]["review_status"] = "draft"

        self.assert_manifest_error(manifest, "when quality_gate_included is true")

    def test_rejects_duplicate_fixture_id(self):
        manifest = load_manifest_object()
        manifest["adjudication_fixtures"][1]["fixture_id"] = manifest["adjudication_fixtures"][0]["fixture_id"]

        self.assert_manifest_error(manifest, "fixture_id duplicate value")

    def test_rejects_fixture_record_count_mismatch(self):
        manifest = load_manifest_object()
        manifest["adjudication_fixtures"][0]["expected_record_count"] = 99

        self.assert_manifest_error(manifest, "expected 99 non-empty JSONL records")

    def test_rejects_unknown_fixture_threshold_key(self):
        manifest = load_manifest_object()
        manifest["quality_gate_thresholds"]["max_fixture_needs_discussion"]["unknown_fixture"] = 0

        self.assert_manifest_error(manifest, "unknown_fixture references unknown fixture")

    def test_rejects_unknown_profile_threshold_key(self):
        manifest = load_manifest_object()
        manifest["quality_gate_thresholds"]["min_profile_review_coverage"]["unknown_profile"] = 1.0

        self.assert_manifest_error(manifest, "unknown_profile references unknown profile")

    def test_rejects_unknown_category_threshold_key(self):
        manifest = load_manifest_object()
        manifest["quality_gate_thresholds"]["min_category_review_coverage"]["unknown_category"] = 1.0

        self.assert_manifest_error(manifest, "unknown_category references unknown category")

    def test_rejects_source_trace_path_outside_repo(self):
        manifest = load_manifest_object()
        manifest["adjudication_fixtures"][0]["source_trace_paths"] = ["../outside.jsonl"]

        self.assert_manifest_error(manifest, "must stay within the repository")

    def test_original_manifest_object_is_not_mutated_by_helper_copy(self):
        manifest = load_manifest_object()
        copied_manifest = copy.deepcopy(manifest)

        self.validate_manifest_object(copied_manifest)

        self.assertEqual(manifest, load_manifest_object())


if __name__ == "__main__":
    unittest.main()
