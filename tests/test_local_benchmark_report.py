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
)
from validate_local_benchmark_report import (  # noqa: E402
    DEFAULT_SCHEMA_PATH,
    LocalBenchmarkReportValidationError,
    validate_local_benchmark_report,
)


def load_snapshot():
    return json.loads(DEFAULT_SNAPSHOT_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


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
        self.assertEqual(summary["report_status"], "no_rankings_published")
        self.assertFalse(summary["ranking_claim_allowed"])
        self.assertEqual(summary["rankings"], 0)
        self.assertEqual(summary["excluded_evidence"], 1)

    def test_generator_can_write_public_safe_no_ranking_report_to_temp_paths(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary = generate_benchmark_report(
                snapshot_path=root / "local_report.json",
                report_path=root / "local_report.md",
            )

            self.assertEqual(summary["report_status"], "no_rankings_published")
            self.assertFalse(summary["ranking_claim_allowed"])
            self.assertEqual(summary["rankings"], 0)
            self.assertEqual(summary["excluded_evidence"], 1)
            self.assertTrue((root / "local_report.json").exists())
            self.assertTrue((root / "local_report.md").exists())

    def test_committed_artifacts_exist(self):
        self.assertTrue(DEFAULT_SNAPSHOT_PATH.exists())
        self.assertTrue(DEFAULT_REPORT_PATH.exists())

    def test_snapshot_excludes_dry_run_ledger_evidence(self):
        snapshot = load_snapshot()

        self.assertEqual(snapshot["report_status"], "no_rankings_published")
        self.assertFalse(snapshot["eligibility_summary"]["acceptance_criteria_met"])
        self.assertEqual(snapshot["eligibility_summary"]["eligible_real_local_targets"], 0)
        self.assertEqual(snapshot["rankings"], [])
        excluded = snapshot["excluded_evidence"][0]
        self.assertEqual(excluded["run_mode"], "dry_run_public_safe_example")
        self.assertIn("Evidence class is not local_public_benchmark.", excluded["exclusion_reasons"])
        self.assertIn("Run mode is not reviewed_live_local_run.", excluded["exclusion_reasons"])

    def test_rejects_ranking_claim_without_rankings(self):
        snapshot = load_snapshot()
        snapshot["ranking_claim_allowed"] = True

        self.assert_snapshot_error(snapshot, "ranking_claim_allowed")

    def test_rejects_rankings_when_no_rankings_published(self):
        snapshot = load_snapshot()
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
            }
        ]

        self.assert_snapshot_error(snapshot, "rankings must be empty")

    def test_rejects_private_audit_excluded_evidence(self):
        snapshot = load_snapshot()
        snapshot["excluded_evidence"][0]["evidence_class"] = "private_audit"

        self.assert_snapshot_error(snapshot, "private_audit cannot appear")


if __name__ == "__main__":
    unittest.main()
