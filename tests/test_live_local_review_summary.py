import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from live_local_review_summary import (  # noqa: E402
    DEFAULT_SUMMARY_PATH,
    LiveLocalReviewSummaryError,
    generate_live_local_review_summary_report,
    validate_live_local_review_summary,
)


def load_valid_summary():
    return json.loads(DEFAULT_SUMMARY_PATH.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


class LiveLocalReviewSummaryTests(unittest.TestCase):
    def test_committed_review_summary_generates_public_safe_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report_json = Path(temp_dir) / "live_local_review_summary.json"
            report_md = Path(temp_dir) / "live_local_review_summary.md"

            report = generate_live_local_review_summary_report(
                report_json_path=report_json,
                report_markdown_path=report_md,
            )

            self.assertEqual(report["report_id"], "m70_live_local_review_summary_report")
            self.assertEqual(report["review_counts"]["records_reviewed"], 4)
            self.assertEqual(report["review_counts"]["needs_discussion_count"], 0)
            self.assertTrue(report["publication_gate"]["publishable_review_state"])
            self.assertEqual(report["inter_rater"]["agreement_rate"], 1.0)
            self.assertTrue(report_json.exists())
            self.assertIn("Live-Local Review Summary", report_md.read_text(encoding="utf-8"))

    def test_duplicate_record_id_is_rejected(self):
        summary = load_valid_summary()
        summary["reviewed_records"][1]["record_id"] = summary["reviewed_records"][0]["record_id"]

        self.assert_summary_fails(summary, "record_id duplicate value")

    def test_unresolved_review_count_must_match_records(self):
        summary = load_valid_summary()
        summary["reviewed_records"][0]["reviewer_decision"] = "needs_discussion"
        summary["reviewed_records"][0]["effective_passed"] = False

        self.assert_summary_fails(summary, "effective_pass_count must equal 3")

    def test_reviewer_alias_must_be_public_safe(self):
        summary = load_valid_summary()
        summary["reviewed_records"][0]["primary_reviewer_alias"] = "person@example.com"

        self.assert_summary_fails(summary, "must be a public-safe reviewer alias")

    def test_inter_rater_counts_must_match_records(self):
        summary = load_valid_summary()
        summary["inter_rater"]["agreement_count"] = 1

        self.assert_summary_fails(summary, "agreement_count must equal 2")

    def test_quality_gate_cannot_run_live_local(self):
        summary = load_valid_summary()
        summary["quality_gate"]["live_local_execution_in_quality_gate"] = True

        self.assert_summary_fails(summary, "live_local_execution_in_quality_gate must equal False")

    def assert_summary_fails(self, summary, message):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "review_summary.json"
            write_json(path, summary)

            with self.assertRaisesRegex(LiveLocalReviewSummaryError, message):
                validate_live_local_review_summary(path)


if __name__ == "__main__":
    unittest.main()
