import copy
import json
import sys
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
)
from inspect_failures import generate_report as generate_failure_report, load_jsonl


ADJUDICATIONS_PATH = REPO_ROOT / "traces/external/adjudications.example.jsonl"
BASELINE_TRACE_PATH = REPO_ROOT / "traces/scored/baseline_mock_run.jsonl"


def load_example_adjudications():
    return [json.loads(line) for line in ADJUDICATIONS_PATH.read_text(encoding="utf-8").splitlines()]


class AdjudicationReportingTests(unittest.TestCase):
    def test_summary_report_rolls_up_reviewer_decisions(self):
        context = load_adjudication_context(ADJUDICATIONS_PATH)

        report = generate_summary_report(context)

        self.assertIn("# Adjudication Summary Report", report)
        self.assertIn("| `needs_discussion` | 1 |", report)
        self.assertIn("| `uphold_score` | 1 |", report)
        self.assertIn("Original Vs Adjudicated Reviewed Results", report)

    def test_aggregate_report_separates_heuristic_and_adjudicated_scopes(self):
        context = load_adjudication_context(ADJUDICATIONS_PATH)

        report = generate_aggregate_report(context)

        self.assertIn("Full source trace heuristic", report)
        self.assertIn("Reviewed subset heuristic", report)
        self.assertIn("Reviewed subset adjudicated", report)

    def test_duplicate_adjudication_targets_are_rejected(self):
        adjudications = load_example_adjudications()
        duplicate = copy.deepcopy(adjudications[0])
        duplicate["adjudication_id"] = "ADJ-DUPLICATE-TARGET"
        adjudications.append(duplicate)

        with self.assertRaises(AdjudicationReportError):
            build_adjudication_index(adjudications)

    def test_failure_inspection_includes_reviewer_annotations(self):
        context = load_adjudication_context(ADJUDICATIONS_PATH)
        adjudication_index = build_adjudication_index(context.adjudications)
        baseline_records = load_jsonl(BASELINE_TRACE_PATH)

        report = generate_failure_report(baseline_records, adjudication_index, BASELINE_TRACE_PATH)

        self.assertIn("Reviewer Decisions On Failed Records", report)
        self.assertIn("Failed records with reviewer decisions | 2", report)
        self.assertIn("ADJ-BASELINE-APPROVAL-004-GENERIC-001", report)


if __name__ == "__main__":
    unittest.main()
