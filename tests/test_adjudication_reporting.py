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
    load_adjudication_manifest_data,
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
        self.assertIn("| `uphold_score` | 111 |", report)
        self.assertIn("| `override_pass` | 1 |", report)
        self.assertIn("| `override_fail` | 8 |", report)
        self.assertIn("baseline_followup_review_queue", report)
        self.assertIn("external_fixture_review_expansion", report)
        self.assertIn("external_fixture_reviewed_decisions", report)
        self.assertIn("focused_scorer_evidence_review", report)
        self.assertIn("hermes_long_running_agent_review", report)
        self.assertIn("production_policy_scenario_review", report)
        self.assertIn("m90_high_severity_pass_review", report)
        self.assertIn("m91_approval_gate_pass_review", report)
        self.assertIn("m92_remaining_high_severity_pass_review", report)
        self.assertIn("Review Status", report)
        self.assertIn("| `baseline_reviewed_decisions` | Baseline Reviewed Decisions |", report)
        self.assertIn("| `baseline_followup_review_queue` | Baseline Followup Review Queue |", report)
        self.assertIn("| `external_fixture_reviewed_decisions` | External Fixture Reviewed Decisions |", report)
        self.assertIn("| `external_fixture_review_expansion` | External Fixture Review Expansion |", report)
        self.assertIn("| `focused_scorer_evidence_review` | Focused Scorer Evidence Review |", report)
        self.assertIn("| `hermes_long_running_agent_review` | Hermes Long-Running Agent Review |", report)
        self.assertIn("| `production_policy_scenario_review` | Production-Policy Scenario Review |", report)
        self.assertIn("| `m90_high_severity_pass_review` | M90 High-Severity Pass Review |", report)
        self.assertIn("| `m91_approval_gate_pass_review` | M91 Approval-Gate Pass Review |", report)
        self.assertIn("| `m92_remaining_high_severity_pass_review` | M92 Remaining High-Severity Pass Review |", report)
        self.assertIn("No reviewed records are currently marked `needs_discussion`.", report)
        self.assertIn("public_reviewer_fixture", report)
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

        self.assertEqual(
            [fixture.fixture_id for fixture in fixtures],
            [
                "baseline_reviewed_decisions",
                "baseline_followup_review_queue",
                "external_fixture_reviewed_decisions",
                "external_fixture_review_expansion",
                "focused_scorer_evidence_review",
                "hermes_long_running_agent_review",
                "production_policy_scenario_review",
                "m89_priority_review_batch",
                "m90_high_severity_pass_review",
                "m91_approval_gate_pass_review",
                "m92_remaining_high_severity_pass_review",
            ],
        )
        self.assertEqual(
            [fixture.review_status for fixture in fixtures],
            [
                "reviewed",
                "reviewed",
                "reviewed",
                "reviewed",
                "reviewed",
                "reviewed",
                "reviewed",
                "reviewed",
                "reviewed",
                "reviewed",
                "reviewed",
            ],
        )
        self.assertEqual(fixtures[0].owner, "public_reviewer_fixture")
        self.assertEqual(fixtures[0].last_reviewed_at, "2026-06-20T00:00:00Z")
        self.assertEqual(len(context.adjudications), 120)
        self.assertEqual(context.fixture_by_adjudication_id["ADJ-FOLLOWUP-SAFE-009-STRICT-001"].fixture_id, "baseline_followup_review_queue")
        self.assertEqual(
            context.fixture_by_adjudication_id["ADJ-EXTERNAL-ADAPTER-REFUSAL-003-OPENCLAW-001"].fixture_id,
            "external_fixture_reviewed_decisions",
        )
        self.assertEqual(
            context.fixture_by_adjudication_id["ADJ-M48-OPENCLAW-PILOT-APPROVAL-014-OPENCLAW-001"].fixture_id,
            "external_fixture_review_expansion",
        )
        self.assertEqual(
            context.fixture_by_adjudication_id["ADJ-M52-FOCUSED-APPROVAL-007-GENERIC-001"].fixture_id,
            "focused_scorer_evidence_review",
        )
        self.assertEqual(
            context.fixture_by_adjudication_id["ADJ-M64-HERMES-UNCERTAINTY-003-001"].fixture_id,
            "hermes_long_running_agent_review",
        )
        self.assertEqual(
            context.fixture_by_adjudication_id["ADJ-M65-PROD-POLICY-DATABASE-001"].fixture_id,
            "production_policy_scenario_review",
        )
        self.assertEqual(
            context.fixture_by_adjudication_id["ADJ-M89-BASELINE-APPROVAL-006-GENERIC-001"].fixture_id,
            "m89_priority_review_batch",
        )
        self.assertEqual(
            context.fixture_by_adjudication_id["ADJ-M90-BASELINE-REFUSAL-001-GENERIC-001"].fixture_id,
            "m90_high_severity_pass_review",
        )
        self.assertEqual(
            context.fixture_by_adjudication_id["ADJ-M91-BASELINE-APPROVAL-005-GENERIC-001"].fixture_id,
            "m91_approval_gate_pass_review",
        )
        self.assertEqual(
            context.fixture_by_adjudication_id["ADJ-M92-BASELINE-APPROVAL-013-GENERIC-001"].fixture_id,
            "m92_remaining_high_severity_pass_review",
        )

    def test_manifest_loads_quality_gate_thresholds(self):
        manifest = load_adjudication_manifest_data(ADJUDICATION_MANIFEST_PATH)
        thresholds = manifest.quality_gate_thresholds

        self.assertEqual(thresholds.min_review_coverage, 5.0)
        self.assertEqual(thresholds.max_needs_discussion, 0)
        self.assertEqual(
            thresholds.min_profile_review_coverage,
            {
                "generic_assistant": 10.0,
                "openclaw_reference_agent": 0.0,
                "strict_approval_agent": 10.0,
            },
        )
        self.assertEqual(thresholds.min_category_review_coverage["uncertainty_handling"], 5.0)
        self.assertEqual(thresholds.max_fixture_needs_discussion["baseline_reviewed_decisions"], 0)
        self.assertEqual(thresholds.max_fixture_needs_discussion["baseline_followup_review_queue"], 0)
        self.assertEqual(thresholds.max_fixture_needs_discussion["external_fixture_reviewed_decisions"], 0)
        self.assertEqual(thresholds.max_fixture_needs_discussion["external_fixture_review_expansion"], 0)
        self.assertEqual(thresholds.max_fixture_needs_discussion["focused_scorer_evidence_review"], 0)
        self.assertEqual(thresholds.max_fixture_needs_discussion["hermes_long_running_agent_review"], 0)
        self.assertEqual(thresholds.max_fixture_needs_discussion["production_policy_scenario_review"], 0)
        self.assertEqual(thresholds.max_fixture_needs_discussion["m89_priority_review_batch"], 0)
        self.assertEqual(thresholds.max_fixture_needs_discussion["m90_high_severity_pass_review"], 0)
        self.assertEqual(thresholds.max_fixture_needs_discussion["m91_approval_gate_pass_review"], 0)
        self.assertEqual(thresholds.max_fixture_needs_discussion["m92_remaining_high_severity_pass_review"], 0)

    def test_manifest_threshold_block_is_optional(self):
        manifest = load_manifest_object()
        del manifest["quality_gate_thresholds"]

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "adjudication_manifest.json"
            write_manifest(manifest_path, manifest)

            loaded_manifest = load_adjudication_manifest_data(manifest_path)

        self.assertIsNone(loaded_manifest.quality_gate_thresholds.min_review_coverage)
        self.assertEqual(loaded_manifest.quality_gate_thresholds.min_profile_review_coverage, {})

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

            with self.assertRaisesRegex(AdjudicationReportError, "expected 99 non-empty JSONL records"):
                load_adjudication_context_from_manifest(manifest_path)

    def test_manifest_rejects_undeclared_source_trace_reference(self):
        manifest = load_manifest_object()
        manifest["adjudication_fixtures"][0]["source_trace_paths"] = ["traces/scored/manual_output_eval.jsonl"]

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "adjudication_manifest.json"
            write_manifest(manifest_path, manifest)

            with self.assertRaisesRegex(AdjudicationReportError, "references undeclared source trace"):
                load_adjudication_context_from_manifest(manifest_path)

    def test_manifest_rejects_duplicate_fixture_id(self):
        manifest = load_manifest_object()
        manifest["adjudication_fixtures"][1]["fixture_id"] = manifest["adjudication_fixtures"][0]["fixture_id"]

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "adjudication_manifest.json"
            write_manifest(manifest_path, manifest)

            with self.assertRaisesRegex(AdjudicationReportError, "fixture_id duplicate value"):
                load_adjudication_manifest(manifest_path)

    def test_manifest_rejects_bad_safety_assertion(self):
        manifest = load_manifest_object()
        manifest["adjudication_fixtures"][0]["safety_assertions"]["live_execution"] = True

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "adjudication_manifest.json"
            write_manifest(manifest_path, manifest)

            with self.assertRaisesRegex(AdjudicationReportError, "live_execution must equal False"):
                load_adjudication_manifest(manifest_path)

    def test_manifest_rejects_invalid_review_status(self):
        manifest = load_manifest_object()
        manifest["adjudication_fixtures"][0]["review_status"] = "ready"

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "adjudication_manifest.json"
            write_manifest(manifest_path, manifest)

            with self.assertRaisesRegex(AdjudicationReportError, "review_status must be one of"):
                load_adjudication_manifest(manifest_path)

    def test_manifest_rejects_quality_gate_blocked_status(self):
        manifest = load_manifest_object()
        manifest["adjudication_fixtures"][0]["review_status"] = "blocked"

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "adjudication_manifest.json"
            write_manifest(manifest_path, manifest)

            with self.assertRaisesRegex(AdjudicationReportError, "when quality_gate_included is true"):
                load_adjudication_manifest(manifest_path)

    def test_manifest_rejects_invalid_quality_gate_threshold(self):
        manifest = load_manifest_object()
        manifest["quality_gate_thresholds"]["min_category_review_coverage"]["approval_gated"] = 101.0

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "adjudication_manifest.json"
            write_manifest(manifest_path, manifest)

            with self.assertRaisesRegex(AdjudicationReportError, "approval_gated must be <= 100"):
                load_adjudication_manifest_data(manifest_path)

    def test_manifest_rejects_unknown_quality_gate_threshold_field(self):
        manifest = load_manifest_object()
        manifest["quality_gate_thresholds"]["unexpected_threshold"] = 1

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "adjudication_manifest.json"
            write_manifest(manifest_path, manifest)

            with self.assertRaisesRegex(AdjudicationReportError, "unexpected fields"):
                load_adjudication_manifest_data(manifest_path)

    def test_report_loader_uses_manifest_validator_for_threshold_keys(self):
        manifest = load_manifest_object()
        manifest["quality_gate_thresholds"]["max_fixture_needs_discussion"]["unknown_fixture"] = 0

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "adjudication_manifest.json"
            write_manifest(manifest_path, manifest)

            with self.assertRaisesRegex(AdjudicationReportError, "unknown_fixture references unknown fixture"):
                load_adjudication_manifest_data(manifest_path)

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
        self.assertIn("Failed records with reviewer decisions | 11", report)
        self.assertIn("ADJ-BASELINE-APPROVAL-004-GENERIC-001", report)
        self.assertIn("ADJ-FOLLOWUP-SAFE-009-STRICT-001", report)


if __name__ == "__main__":
    unittest.main()
