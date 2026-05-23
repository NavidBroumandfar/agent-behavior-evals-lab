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

from adjudication_report import (
    AdjudicationReportError,
    build_adjudication_index,
    generate_aggregate_report,
    generate_summary_report,
    load_adjudication_context,
    load_adjudication_context_from_manifest,
    load_adjudication_manifest,
    select_adjudication_input,
)
from inspect_failures import generate_report as generate_failure_report, load_jsonl


ADJUDICATIONS_PATH = REPO_ROOT / "traces/external/adjudications.example.jsonl"
ADJUDICATION_MANIFEST_PATH = REPO_ROOT / "traces/external/adjudication_manifest.json"
BASELINE_TRACE_PATH = REPO_ROOT / "traces/scored/baseline_mock_run.jsonl"


def load_example_adjudications():
    return [json.loads(line) for line in ADJUDICATIONS_PATH.read_text(encoding="utf-8").splitlines()]


def load_manifest_object():
    return json.loads(ADJUDICATION_MANIFEST_PATH.read_text(encoding="utf-8"))


def write_manifest(path, manifest):
    path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class AdjudicationReportingTests(unittest.TestCase):
    def test_summary_report_rolls_up_reviewer_decisions(self):
        context = load_adjudication_context_from_manifest(ADJUDICATION_MANIFEST_PATH)

        report = generate_summary_report(context)

        self.assertIn("# Adjudication Summary Report", report)
        self.assertIn("| `needs_discussion` | 3 |", report)
        self.assertIn("| `uphold_score` | 2 |", report)
        self.assertIn("| `override_pass` | 1 |", report)
        self.assertIn("| `override_fail` | 1 |", report)
        self.assertIn("baseline_followup_review_queue", report)
        self.assertIn("Needs Discussion Queue", report)
        self.assertIn("Original Vs Adjudicated Reviewed Results", report)

    def test_aggregate_report_separates_heuristic_and_adjudicated_scopes(self):
        context = load_adjudication_context(ADJUDICATIONS_PATH)

        report = generate_aggregate_report(context)

        self.assertIn("Full source trace heuristic", report)
        self.assertIn("Reviewed subset heuristic", report)
        self.assertIn("Reviewed subset adjudicated", report)

    def test_manifest_loads_multiple_adjudication_fixtures(self):
        fixtures = load_adjudication_manifest(ADJUDICATION_MANIFEST_PATH)
        context = load_adjudication_context_from_manifest(ADJUDICATION_MANIFEST_PATH)

        self.assertEqual([fixture.fixture_id for fixture in fixtures], ["baseline_reviewed_decisions", "baseline_followup_review_queue"])
        self.assertEqual(len(context.adjudications), 7)
        self.assertEqual(context.fixture_by_adjudication_id["ADJ-FOLLOWUP-SAFE-009-STRICT-001"].fixture_id, "baseline_followup_review_queue")

    def test_default_cli_selection_prefers_manifest_when_present(self):
        selected_input, selected_manifest = select_adjudication_input(
            default_adjudications_path=ADJUDICATIONS_PATH,
            default_manifest_path=ADJUDICATION_MANIFEST_PATH,
        )

        self.assertEqual(selected_input, ADJUDICATIONS_PATH)
        self.assertEqual(selected_manifest, ADJUDICATION_MANIFEST_PATH)

    def test_explicit_cli_input_uses_single_fixture_mode(self):
        selected_input, selected_manifest = select_adjudication_input(
            ADJUDICATIONS_PATH,
            default_manifest_path=ADJUDICATION_MANIFEST_PATH,
        )

        self.assertEqual(selected_input, ADJUDICATIONS_PATH)
        self.assertIsNone(selected_manifest)

    def test_manifest_rejects_record_count_mismatch(self):
        manifest = load_manifest_object()
        manifest["adjudication_fixtures"][0]["expected_record_count"] = 99

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "adjudication_manifest.json"
            write_manifest(manifest_path, manifest)

            with self.assertRaisesRegex(AdjudicationReportError, "expected 99 adjudications"):
                load_adjudication_context_from_manifest(manifest_path)

    def test_manifest_rejects_undeclared_source_trace_reference(self):
        manifest = load_manifest_object()
        manifest["adjudication_fixtures"][0]["source_trace_paths"] = ["traces/scored/manual_output_eval.jsonl"]

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "adjudication_manifest.json"
            write_manifest(manifest_path, manifest)

            with self.assertRaisesRegex(AdjudicationReportError, "references undeclared source trace"):
                load_adjudication_context_from_manifest(manifest_path)

    def test_duplicate_adjudication_targets_are_rejected(self):
        adjudications = load_example_adjudications()
        duplicate = copy.deepcopy(adjudications[0])
        duplicate["adjudication_id"] = "ADJ-DUPLICATE-TARGET"
        adjudications.append(duplicate)

        with self.assertRaises(AdjudicationReportError):
            build_adjudication_index(adjudications)

    def test_failure_inspection_includes_reviewer_annotations(self):
        context = load_adjudication_context_from_manifest(ADJUDICATION_MANIFEST_PATH)
        adjudication_index = build_adjudication_index(context.adjudications)
        baseline_records = load_jsonl(BASELINE_TRACE_PATH)

        report = generate_failure_report(baseline_records, adjudication_index, BASELINE_TRACE_PATH)

        self.assertIn("Reviewer Decisions On Failed Records", report)
        self.assertIn("Failed records with reviewer decisions | 5", report)
        self.assertIn("ADJ-BASELINE-APPROVAL-004-GENERIC-001", report)
        self.assertIn("ADJ-FOLLOWUP-SAFE-009-STRICT-001", report)


if __name__ == "__main__":
    unittest.main()
