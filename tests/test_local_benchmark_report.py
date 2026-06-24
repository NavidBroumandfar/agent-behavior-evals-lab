import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from local_benchmark_report import (  # noqa: E402
    DEFAULT_REPORT_PATH,
    DEFAULT_SNAPSHOT_PATH,
    generate_benchmark_report,
    ranking_from_entry,
)
from local_ranking_methodology import DEFAULT_METHODOLOGY_PATH  # noqa: E402
from local_run_ledger import DEFAULT_LEDGER_PATH  # noqa: E402
from validate_local_benchmark_report import (  # noqa: E402
    DEFAULT_SCHEMA_PATH,
    LocalBenchmarkReportValidationError,
    validate_local_benchmark_report,
)


def load_snapshot():
    return json.loads(DEFAULT_SNAPSHOT_PATH.read_text(encoding="utf-8"))


def load_ledger():
    return json.loads(DEFAULT_LEDGER_PATH.read_text(encoding="utf-8"))


def load_methodology():
    return json.loads(DEFAULT_METHODOLOGY_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def reviewed_local_ledger(model):
    ledger = load_ledger()
    ledger["ledger_kind"] = "published_local_benchmark"
    ledger["ledger_id"] = f"test_ledger_{model.replace(':', '_')}"
    entry = ledger["entries"][0]
    entry["evidence_class"] = "local_public_benchmark"
    entry["run_mode"] = "reviewed_live_local_run"
    entry["ranking_eligible"] = True
    entry["ranking_exclusion_reason"] = ""
    entry["runtime"] = "ollama"
    entry["model"] = model
    entry["case_set"]["benchmark_split"] = "standard"
    entry["case_set"]["case_count"] = 4
    entry["safety_assertions"]["live_execution"] = True
    ledger["safety_assertions"]["live_execution"] = True
    return ledger


class LocalBenchmarkReportTests(unittest.TestCase):
    def assert_snapshot_error(self, snapshot, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "snapshot.json"
            write_json(path, snapshot)
            with self.assertRaisesRegex(LocalBenchmarkReportValidationError, message):
                validate_local_benchmark_report(path, DEFAULT_SCHEMA_PATH, DEFAULT_REPORT_PATH)

    def test_committed_local_benchmark_report_validates(self):
        summary = validate_local_benchmark_report()

        self.assertEqual(summary["snapshot_path"], "reports/comparisons/local_open_weight_benchmark_v1.json")
        self.assertEqual(summary["schema_path"], "schemas/local_benchmark_report.schema.json")
        self.assertEqual(summary["report_path"], "reports/comparisons/local_open_weight_benchmark_v1.md")
        self.assertEqual(summary["snapshot_id"], "local_open_weight_benchmark_report_v1")
        self.assertEqual(summary["report_status"], "published_local_ranking")
        self.assertTrue(summary["ranking_claim_allowed"])
        self.assertEqual(summary["rankings"], 5)
        self.assertEqual(summary["excluded_evidence"], 1)

    def test_generator_can_write_public_safe_published_ranking_report_to_temp_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary = generate_benchmark_report(
                snapshot_path=root / "local_report.json",
                report_path=root / "local_report.md",
            )

            self.assertEqual(summary["report_status"], "published_local_ranking")
            self.assertTrue(summary["ranking_claim_allowed"])
            self.assertEqual(summary["rankings"], 5)
            self.assertEqual(summary["excluded_evidence"], 1)
            self.assertTrue((root / "local_report.json").exists())
            self.assertTrue((root / "local_report.md").exists())

    def test_committed_artifacts_exist(self):
        self.assertTrue(DEFAULT_SNAPSHOT_PATH.exists())
        self.assertTrue(DEFAULT_REPORT_PATH.exists())

    def test_snapshot_publishes_current_reviewed_ledgers_and_excludes_dry_run_evidence(self):
        snapshot = load_snapshot()

        self.assertEqual(snapshot["report_status"], "published_local_ranking")
        self.assertTrue(snapshot["ranking_claim_allowed"])
        self.assertTrue(snapshot["eligibility_summary"]["acceptance_criteria_met"])
        self.assertEqual(snapshot["eligibility_summary"]["eligible_real_local_targets"], 5)
        self.assertEqual(len(snapshot["rankings"]), 5)
        excluded = snapshot["excluded_evidence"][0]
        self.assertEqual(excluded["run_mode"], "dry_run_public_safe_example")
        self.assertIn("Evidence class is not local_public_benchmark.", excluded["exclusion_reasons"])
        self.assertIn("Run mode is not reviewed_live_local_run.", excluded["exclusion_reasons"])

    def test_ranking_aggregation_uses_scored_traces_and_review_summary(self):
        ledger = load_ledger()
        entry = ledger["entries"][0]
        methodology = load_methodology()

        row = ranking_from_entry(entry, methodology)

        self.assertEqual(row["sample_size"], 4)
        self.assertEqual(row["severity_weighted_effective_pass_rate"], 1.0)
        self.assertEqual(row["severity_weighted_heuristic_pass_rate"], 1.0)
        self.assertEqual(row["bootstrap_ci_95"], {"low": 1.0, "high": 1.0})
        self.assertEqual(row["review_counts"]["records_reviewed"], 4)
        self.assertEqual(row["review_counts"]["needs_discussion_count"], 0)

    def test_one_reviewed_live_local_ledger_remains_blocked(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "reports" / "comparisons") as temp_dir:
            root = Path(temp_dir)
            methodology = load_methodology()
            methodology["uncertainty_policy"]["minimum_sample_size_for_publication"] = 4
            methodology_path = root / "methodology.json"
            ledger_path = root / "ledger.json"
            write_json(methodology_path, methodology)
            write_json(ledger_path, reviewed_local_ledger("model-a:latest"))

            summary = generate_benchmark_report(
                snapshot_path=root / "local_report.json",
                report_path=root / "local_report.md",
                methodology_path=methodology_path,
                ledger_paths=[ledger_path],
            )
            snapshot = json.loads((root / "local_report.json").read_text(encoding="utf-8"))

            self.assertEqual(summary["report_status"], "no_rankings_published")
            self.assertFalse(summary["ranking_claim_allowed"])
            self.assertEqual(summary["rankings"], 0)
            self.assertEqual(snapshot["eligibility_summary"]["eligible_real_local_targets"], 1)
            self.assertFalse(snapshot["eligibility_summary"]["acceptance_criteria_met"])
            self.assertEqual(snapshot["rankings"], [])

    def test_two_reviewed_live_local_ledgers_unlock_fake_public_safe_report(self):
        with tempfile.TemporaryDirectory(dir=REPO_ROOT / "reports" / "comparisons") as temp_dir:
            root = Path(temp_dir)
            methodology = load_methodology()
            methodology["uncertainty_policy"]["minimum_sample_size_for_publication"] = 4
            methodology_path = root / "methodology.json"
            ledger_a_path = root / "ledger_a.json"
            ledger_b_path = root / "ledger_b.json"
            write_json(methodology_path, methodology)
            write_json(ledger_a_path, reviewed_local_ledger("model-a:latest"))
            write_json(ledger_b_path, reviewed_local_ledger("model-b:latest"))

            summary = generate_benchmark_report(
                snapshot_path=root / "local_report.json",
                report_path=root / "local_report.md",
                methodology_path=methodology_path,
                ledger_paths=[ledger_a_path, ledger_b_path],
            )
            snapshot = json.loads((root / "local_report.json").read_text(encoding="utf-8"))

            self.assertEqual(summary["report_status"], "published_local_ranking")
            self.assertTrue(summary["ranking_claim_allowed"])
            self.assertEqual(summary["rankings"], 2)
            self.assertEqual(snapshot["eligibility_summary"]["eligible_real_local_targets"], 2)
            self.assertEqual(snapshot["rankings"][0]["review_counts"]["records_reviewed"], 4)

    def test_rejects_ranking_claim_without_rankings(self):
        snapshot = load_snapshot()
        snapshot["report_status"] = "no_rankings_published"
        snapshot["ranking_claim_allowed"] = True
        snapshot["rankings"] = []
        snapshot["eligibility_summary"]["acceptance_criteria_met"] = False
        snapshot["eligibility_summary"]["ranking_publication_blocked_reason"] = "Blocked test fixture."

        self.assert_snapshot_error(snapshot, "ranking_claim_allowed")

    def test_rejects_rankings_when_no_rankings_published(self):
        snapshot = load_snapshot()
        snapshot["report_status"] = "no_rankings_published"
        snapshot["ranking_claim_allowed"] = False
        snapshot["eligibility_summary"]["acceptance_criteria_met"] = False
        snapshot["eligibility_summary"]["ranking_publication_blocked_reason"] = "Blocked test fixture."
        snapshot["rankings"] = [
            {
                "rank": 1,
                "model": "fake",
                "runtime": "fake",
                "ledger_entry_id": "fake",
                "sample_size": 70,
                "benchmark_split": "standard",
                "severity_weighted_effective_pass_rate": 1.0,
                "severity_weighted_heuristic_pass_rate": 1.0,
                "bootstrap_ci_95": {"low": 1.0, "high": 1.0},
                "unresolved_review_count": 0,
                "abstention_count": 0,
                "review_counts": {
                    "records_reviewed": 70,
                    "scorer_pass_count": 70,
                    "scorer_fail_count": 0,
                    "effective_pass_count": 70,
                    "effective_fail_count": 0,
                    "override_count": 0,
                    "needs_discussion_count": 0,
                    "unsafe_output_count": 0,
                    "malformed_output_count": 0,
                    "reviewer_count": 2,
                    "agreement_rate": 1.0,
                },
            }
        ]

        self.assert_snapshot_error(snapshot, "rankings must be empty")

    def test_rejects_private_audit_excluded_evidence(self):
        snapshot = load_snapshot()
        snapshot["excluded_evidence"][0]["evidence_class"] = "private_audit"

        self.assert_snapshot_error(snapshot, "private_audit cannot appear")


if __name__ == "__main__":
    unittest.main()
