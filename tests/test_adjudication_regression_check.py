import copy
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from adjudication_regression_check import build_snapshot, check_snapshot, compare_snapshots
from adjudication_report import load_adjudication_context


ADJUDICATIONS_PATH = REPO_ROOT / "traces/external/adjudications.example.jsonl"
SNAPSHOT_PATH = REPO_ROOT / "reports/comparisons/adjudication_regression_snapshot.json"


class AdjudicationRegressionCheckTests(unittest.TestCase):
    def test_build_snapshot_captures_expected_committed_counts(self):
        context = load_adjudication_context(ADJUDICATIONS_PATH)

        snapshot = build_snapshot(context, ADJUDICATIONS_PATH)

        self.assertEqual(snapshot["adjudication_records"], 2)
        self.assertEqual(snapshot["source_trace_count"], 1)
        self.assertEqual(snapshot["reviewer_decisions"]["uphold_score"], 1)
        self.assertEqual(snapshot["reviewer_decisions"]["needs_discussion"], 1)
        self.assertEqual(snapshot["result_summary"]["changed_result_count"], 0)
        self.assertEqual(snapshot["review_coverage_by_source_trace"]["traces/scored/baseline_mock_run.jsonl"]["reviewed_records"], 2)

    def test_compare_snapshots_reports_nested_differences(self):
        expected = {"result_summary": {"changed_result_count": 0}}
        current = {"result_summary": {"changed_result_count": 1}}

        differences = compare_snapshots(expected, current)

        self.assertEqual(
            differences,
            ["result_summary.changed_result_count: expected 0, found 1"],
        )

    def test_committed_snapshot_matches_current_adjudications(self):
        result = check_snapshot(ADJUDICATIONS_PATH, SNAPSHOT_PATH)

        self.assertTrue(result["passed"], result["differences"])

    def test_snapshot_mismatch_fails_comparison(self):
        context = load_adjudication_context(ADJUDICATIONS_PATH)
        expected = build_snapshot(context, ADJUDICATIONS_PATH)
        current = copy.deepcopy(expected)
        current["adjudication_records"] = 99

        differences = compare_snapshots(expected, current)

        self.assertEqual(differences, ["adjudication_records: expected 2, found 99"])


if __name__ == "__main__":
    unittest.main()
