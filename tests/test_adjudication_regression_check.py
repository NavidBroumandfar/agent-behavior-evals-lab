import copy
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from adjudication_regression_check import build_snapshot, check_snapshot, compare_snapshots, threshold_violations
from adjudication_report import load_adjudication_context_from_manifest


ADJUDICATIONS_PATH = REPO_ROOT / "traces/external/adjudications.example.jsonl"
ADJUDICATION_MANIFEST_PATH = REPO_ROOT / "traces/external/adjudication_manifest.json"
SNAPSHOT_PATH = REPO_ROOT / "reports/comparisons/adjudication_regression_snapshot.json"


class AdjudicationRegressionCheckTests(unittest.TestCase):
    def test_build_snapshot_captures_expected_committed_counts(self):
        context = load_adjudication_context_from_manifest(ADJUDICATION_MANIFEST_PATH)

        snapshot = build_snapshot(context, ADJUDICATION_MANIFEST_PATH)

        self.assertEqual(snapshot["adjudication_input"], "traces/external/adjudication_manifest.json")
        self.assertEqual(snapshot["adjudication_fixture_count"], 9)
        self.assertEqual(snapshot["adjudication_fixture_statuses"], {"reviewed": 9})
        self.assertEqual(snapshot["adjudication_fixtures"]["baseline_followup_review_queue"]["records"], 4)
        self.assertEqual(snapshot["adjudication_fixtures"]["external_fixture_reviewed_decisions"]["records"], 8)
        self.assertEqual(snapshot["adjudication_fixtures"]["external_fixture_review_expansion"]["records"], 22)
        self.assertEqual(snapshot["adjudication_fixtures"]["focused_scorer_evidence_review"]["records"], 6)
        self.assertEqual(snapshot["adjudication_fixtures"]["hermes_long_running_agent_review"]["records"], 2)
        self.assertEqual(snapshot["adjudication_fixtures"]["production_policy_scenario_review"]["records"], 6)
        self.assertEqual(snapshot["adjudication_fixtures"]["m89_priority_review_batch"]["records"], 4)
        self.assertEqual(snapshot["adjudication_fixtures"]["m90_high_severity_pass_review"]["records"], 20)
        self.assertEqual(
            snapshot["adjudication_fixtures"]["baseline_followup_review_queue"]["review_status"],
            "reviewed",
        )
        self.assertEqual(
            snapshot["adjudication_fixtures"]["baseline_followup_review_queue"]["owner"],
            "public_reviewer_fixture",
        )
        self.assertEqual(snapshot["adjudication_records"], 80)
        self.assertEqual(snapshot["source_trace_count"], 11)
        self.assertEqual(snapshot["review_coverage_by_profile"]["generic_assistant"]["review_coverage"], "53.4%")
        self.assertEqual(snapshot["review_coverage_by_profile"]["strict_approval_agent"]["review_coverage"], "45.6%")
        self.assertEqual(snapshot["review_coverage_by_profile"]["openclaw_reference_agent"]["review_coverage"], "36.8%")
        self.assertEqual(snapshot["review_coverage_by_profile"]["hermes_long_running_agent"]["review_coverage"], "100.0%")
        self.assertEqual(snapshot["review_coverage_by_category"]["approval_gated"]["review_coverage"], "45.9%")
        self.assertEqual(snapshot["review_coverage_by_category"]["safe_direct_response"]["review_coverage"], "30.4%")
        self.assertEqual(snapshot["review_coverage_by_category"]["refusal_required"]["review_coverage"], "81.2%")
        self.assertEqual(snapshot["review_coverage_by_category"]["uncertainty_handling"]["review_coverage"], "34.3%")
        self.assertEqual(snapshot["reviewer_decisions"]["uphold_score"], 77)
        self.assertEqual(snapshot["reviewer_decisions"]["needs_discussion"], 0)
        self.assertEqual(snapshot["reviewer_decisions"]["override_pass"], 1)
        self.assertEqual(snapshot["reviewer_decisions"]["override_fail"], 2)
        self.assertEqual(snapshot["result_summary"]["changed_result_count"], 3)
        self.assertEqual(snapshot["review_coverage_by_source_trace"]["traces/scored/baseline_mock_run.jsonl"]["reviewed_records"], 34)
        self.assertEqual(
            snapshot["review_coverage_by_source_trace"]["traces/scored/focused_scorer_evidence_eval.jsonl"]["review_coverage"],
            "100.0%",
        )
        self.assertEqual(
            snapshot["review_coverage_by_source_trace"]["traces/scored/adapter_output_fixture_import.jsonl"]["review_coverage"],
            "100.0%",
        )
        self.assertEqual(
            snapshot["review_coverage_by_source_trace"]["traces/scored/openclaw_manual_eval.jsonl"]["review_coverage"],
            "100.0%",
        )
        self.assertEqual(
            snapshot["review_coverage_by_source_trace"]["traces/scored/public_safe_transcript_expansion_eval.jsonl"]["review_coverage"],
            "75.0%",
        )
        self.assertEqual(
            snapshot["review_coverage_by_source_trace"]["traces/scored/hermes_long_running_agent_eval.jsonl"]["review_coverage"],
            "100.0%",
        )
        self.assertEqual(
            snapshot["review_coverage_by_source_trace"]["traces/scored/production_policy_scenario_eval.jsonl"]["review_coverage"],
            "100.0%",
        )

    def test_compare_snapshots_reports_nested_differences(self):
        expected = {"result_summary": {"changed_result_count": 0}}
        current = {"result_summary": {"changed_result_count": 1}}

        differences = compare_snapshots(expected, current)

        self.assertEqual(
            differences,
            ["result_summary.changed_result_count: expected 0, found 1"],
        )

    def test_committed_snapshot_matches_current_adjudications(self):
        result = check_snapshot(ADJUDICATIONS_PATH, SNAPSHOT_PATH, manifest_path=ADJUDICATION_MANIFEST_PATH)

        self.assertTrue(result["passed"], result["differences"])

    def test_cli_thresholds_override_manifest_thresholds(self):
        result = check_snapshot(
            ADJUDICATIONS_PATH,
            SNAPSHOT_PATH,
            min_review_coverage=28.0,
            manifest_path=ADJUDICATION_MANIFEST_PATH,
        )

        self.assertFalse(result["passed"])
        self.assertEqual(
            result["differences"],
            ["traces/scored/baseline_mock_run.jsonl.review_coverage: expected at least 28.0%, found 27.0%"],
        )

    def test_snapshot_mismatch_fails_comparison(self):
        context = load_adjudication_context_from_manifest(ADJUDICATION_MANIFEST_PATH)
        expected = build_snapshot(context, ADJUDICATION_MANIFEST_PATH)
        current = copy.deepcopy(expected)
        current["adjudication_records"] = 99

        differences = compare_snapshots(expected, current)

        self.assertEqual(differences, ["adjudication_records: expected 80, found 99"])

    def test_threshold_violations_report_coverage_failures(self):
        context = load_adjudication_context_from_manifest(ADJUDICATION_MANIFEST_PATH)
        snapshot = build_snapshot(context, ADJUDICATION_MANIFEST_PATH)

        differences = threshold_violations(snapshot, min_review_coverage=28.0, max_needs_discussion=2)

        self.assertEqual(
            differences,
            [
                "traces/scored/baseline_mock_run.jsonl.review_coverage: expected at least 28.0%, found 27.0%",
            ],
        )

    def test_threshold_violations_report_profile_category_and_fixture_failures(self):
        context = load_adjudication_context_from_manifest(ADJUDICATION_MANIFEST_PATH)
        snapshot = build_snapshot(context, ADJUDICATION_MANIFEST_PATH)

        differences = threshold_violations(
            snapshot,
            min_profile_review_coverage={"openclaw_reference_agent": 40.0},
            min_category_review_coverage={"uncertainty_handling": 35.0},
            max_fixture_needs_discussion={"missing_fixture": 0},
        )

        self.assertEqual(
            differences,
            [
                "profile.openclaw_reference_agent.review_coverage: expected at least 40.0%, found 36.8%",
                "category.uncertainty_handling.review_coverage: expected at least 35.0%, found 34.3%",
                "fixture.missing_fixture.needs_discussion: missing fixture",
            ],
        )

    def test_committed_snapshot_passes_optional_thresholds(self):
        result = check_snapshot(
            ADJUDICATIONS_PATH,
            SNAPSHOT_PATH,
            min_review_coverage=5.0,
            max_needs_discussion=0,
            manifest_path=ADJUDICATION_MANIFEST_PATH,
            min_profile_review_coverage={
                "generic_assistant": 10.0,
                "openclaw_reference_agent": 0.0,
                "strict_approval_agent": 10.0,
            },
            min_category_review_coverage={
                "approval_gated": 10.0,
                "refusal_required": 0.0,
                "safe_direct_response": 10.0,
                "uncertainty_handling": 5.0,
            },
            max_fixture_needs_discussion={
                "baseline_reviewed_decisions": 0,
                "baseline_followup_review_queue": 0,
                "external_fixture_reviewed_decisions": 0,
                "external_fixture_review_expansion": 0,
                "focused_scorer_evidence_review": 0,
                "hermes_long_running_agent_review": 0,
                "production_policy_scenario_review": 0,
                "m89_priority_review_batch": 0,
                "m90_high_severity_pass_review": 0,
            },
        )

        self.assertTrue(result["passed"], result["differences"])


if __name__ == "__main__":
    unittest.main()
