import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from validate_fixture_manifest import FixtureManifestValidationError, validate_manifest


FIXTURE_MANIFEST_PATH = REPO_ROOT / "traces/external/fixture_manifest.json"


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2), encoding="utf-8")


def write_jsonl(path, records):
    with path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
            output_file.write("\n")


def valid_manifest():
    return {
        "manifest_id": "external_fixture_manifest",
        "version": "0.1.0-test",
        "generated_at": "2026-05-10T00:00:00Z",
        "purpose": "Unit-test fixture manifest.",
        "scope": ["Temporary fixture manifest validation test."],
        "non_goals": ["No live execution."],
        "fixtures": [valid_fixture_entry()],
    }


def valid_fixture_entry():
    return {
        "fixture_id": "temporary_fixture",
        "source_path": "source_fixture.jsonl",
        "source_kind": "temporary_saved_output_fixture",
        "source_type": "temporary_manual_output",
        "provenance_class": "manual_saved_output",
        "data_classification": "public_safe_fixture",
        "generated_by": "tests/test_fixture_manifest_validation.py",
        "validates_with": "tests/test_fixture_manifest_validation.py",
        "imported_by": "tests/test_fixture_manifest_validation.py",
        "scored_trace_path": "scored_trace.jsonl",
        "report_paths": ["report.md"],
        "quality_gate_included": True,
        "expected_record_count": 2,
        "expected_scored_count": 2,
        "limitations": ["Temporary fixture for validator tests."],
        "notes": "Public-safe temporary manifest entry.",
        "safety_assertions": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
            "credentials_required": False,
        },
    }


class FixtureManifestValidationTests(unittest.TestCase):
    def test_committed_fixture_manifest_validates(self):
        summary = validate_manifest(FIXTURE_MANIFEST_PATH)

        self.assertEqual(summary["manifest_path"], "traces/external/fixture_manifest.json")
        self.assertEqual(summary["fixture_count"], 7)
        self.assertEqual(summary["quality_gate_fixture_count"], 7)

    def test_malformed_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = root / "manifest.json"
            manifest_path.write_text("{", encoding="utf-8")

            self.assert_manifest_fails(manifest_path, root)

    def test_manifest_must_be_an_object(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = root / "manifest.json"
            write_json(manifest_path, [])

            self.assert_manifest_fails(manifest_path, root)

    def test_missing_top_level_fields_are_rejected(self):
        for field_name in ["manifest_id", "version", "generated_at", "fixtures"]:
            with self.subTest(field_name=field_name):
                manifest = valid_manifest()
                del manifest[field_name]

                self.assert_temporary_manifest_fails(manifest)

    def test_fixtures_must_be_a_list(self):
        manifest = valid_manifest()
        manifest["fixtures"] = "not a list"

        self.assert_temporary_manifest_fails(manifest)

    def test_empty_fixtures_list_is_rejected(self):
        manifest = valid_manifest()
        manifest["fixtures"] = []

        self.assert_temporary_manifest_fails(manifest)

    def test_missing_fixture_fields_are_rejected(self):
        required_fields = [
            "fixture_id",
            "source_path",
            "source_kind",
            "source_type",
            "provenance_class",
            "data_classification",
            "generated_by",
            "validates_with",
            "imported_by",
            "scored_trace_path",
            "report_paths",
            "quality_gate_included",
            "expected_record_count",
            "limitations",
            "notes",
            "safety_assertions",
        ]

        for field_name in required_fields:
            with self.subTest(field_name=field_name):
                manifest = valid_manifest()
                del manifest["fixtures"][0][field_name]

                self.assert_temporary_manifest_fails(manifest)

    def test_quality_gate_included_must_be_boolean(self):
        manifest = valid_manifest()
        manifest["fixtures"][0]["quality_gate_included"] = "true"

        self.assert_temporary_manifest_fails(manifest)

    def test_expected_record_count_must_be_integer(self):
        manifest = valid_manifest()
        manifest["fixtures"][0]["expected_record_count"] = "2"

        self.assert_temporary_manifest_fails(manifest)

    def test_expected_record_count_must_match_source_jsonl_lines(self):
        manifest = valid_manifest()
        manifest["fixtures"][0]["expected_record_count"] = 3

        self.assert_temporary_manifest_fails(manifest)

    def test_missing_source_path_is_rejected(self):
        manifest = valid_manifest()
        manifest["fixtures"][0]["source_path"] = "missing_source.jsonl"

        self.assert_temporary_manifest_fails(manifest)

    def test_missing_scored_trace_path_is_rejected(self):
        manifest = valid_manifest()
        manifest["fixtures"][0]["scored_trace_path"] = "missing_scored_trace.jsonl"

        self.assert_temporary_manifest_fails(manifest)

    def test_missing_report_path_is_rejected(self):
        manifest = valid_manifest()
        manifest["fixtures"][0]["report_paths"] = ["missing_report.md"]

        self.assert_temporary_manifest_fails(manifest)

    def test_unsafe_safety_assertions_are_rejected(self):
        unsafe_values = [
            ("live_execution", True),
            ("external_actions", True),
            ("contains_private_data", True),
            ("credentials_required", True),
        ]

        for field_name, field_value in unsafe_values:
            with self.subTest(field_name=field_name):
                manifest = valid_manifest()
                manifest["fixtures"][0]["safety_assertions"][field_name] = field_value

                self.assert_temporary_manifest_fails(manifest)

    def test_private_or_sensitive_data_classifications_are_rejected(self):
        blocked_values = [
            "private_or_sensitive_blocked",
            "private",
            "sensitive",
        ]

        for data_classification in blocked_values:
            with self.subTest(data_classification=data_classification):
                manifest = valid_manifest()
                manifest["fixtures"][0]["data_classification"] = data_classification

                self.assert_temporary_manifest_fails(manifest)

    def assert_temporary_manifest_fails(self, manifest):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = root / "manifest.json"
            self.write_temporary_fixture_files(root)
            write_json(manifest_path, manifest)

            self.assert_manifest_fails(manifest_path, root)

    def assert_manifest_fails(self, manifest_path, root):
        with self.assertRaises(FixtureManifestValidationError):
            validate_manifest(manifest_path, repo_root=root)

    @staticmethod
    def write_temporary_fixture_files(root):
        records = [
            {"record_id": "TEMP-001", "output_text": "Temporary public-safe source record."},
            {"record_id": "TEMP-002", "output_text": "Another temporary public-safe source record."},
        ]
        write_jsonl(root / "source_fixture.jsonl", records)
        write_jsonl(root / "scored_trace.jsonl", records)
        (root / "report.md").write_text("# Temporary Report\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
