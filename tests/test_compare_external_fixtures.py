import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from compare_external_fixtures import (
    ExternalFixtureComparisonError,
    generate_report,
    load_all_sources,
    load_fixture_manifest,
)
from tests.test_validate_schemas import valid_trace_record


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2), encoding="utf-8")


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
            output_file.write("\n")


def temporary_manifest():
    return {
        "manifest_id": "external_fixture_manifest",
        "version": "0.1.0-test",
        "generated_at": "2026-05-23T00:00:00Z",
        "purpose": "Temporary manifest-driven comparison test.",
        "scope": ["Temporary fixture comparison test."],
        "non_goals": ["No live execution."],
        "fixtures": [
            {
                "fixture_id": "temporary_fixture",
                "source_path": "traces/external/temporary_source.jsonl",
                "source_kind": "temporary_saved_output_fixture",
                "source_type": "temporary_manual_output",
                "provenance_class": "manual_saved_output",
                "data_classification": "public_safe_fixture",
                "generated_by": "tests/test_compare_external_fixtures.py",
                "validates_with": "tests/test_compare_external_fixtures.py",
                "imported_by": "tests/test_compare_external_fixtures.py",
                "scored_trace_path": "traces/scored/temporary_scored.jsonl",
                "expected_record_count": 1,
                "expected_scored_count": 1,
                "report_paths": ["reports/comparisons/external_fixture_comparison_report.md"],
                "quality_gate_included": False,
                "safety_assertions": {
                    "public_safe": True,
                    "live_execution": False,
                    "external_actions": False,
                    "contains_private_data": False,
                    "credentials_required": False,
                },
                "limitations": ["Temporary public-safe test fixture."],
                "notes": "Temporary manifest entry used by unit tests.",
            }
        ],
    }


class CompareExternalFixturesTests(unittest.TestCase):
    def test_report_sources_are_loaded_from_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = root / "traces/external/fixture_manifest.json"
            write_json(manifest_path, temporary_manifest())
            write_jsonl(root / "traces/external/temporary_source.jsonl", [{"record_id": "TEMP-001"}])
            write_jsonl(root / "traces/scored/temporary_scored.jsonl", [valid_trace_record()])

            manifest = load_fixture_manifest(manifest_path, repo_root=root)
            source_records = load_all_sources(manifest)
            report = generate_report(source_records, manifest)

            self.assertEqual([source.key for source in manifest.sources], ["temporary_fixture"])
            self.assertIn("temporary_fixture", report)
            self.assertIn("Manifest", report)
            self.assertIn("Quality Gate", report)

    def test_manifest_without_fixtures_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = root / "fixture_manifest.json"
            manifest = temporary_manifest()
            manifest["fixtures"] = []
            write_json(manifest_path, manifest)

            with self.assertRaises(ExternalFixtureComparisonError):
                load_fixture_manifest(manifest_path, repo_root=root)


if __name__ == "__main__":
    unittest.main()
