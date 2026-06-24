import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from m107b_deepseek_reviewed_ledger import (  # noqa: E402
    LEDGER_ID,
    LEDGER_PATH,
    METADATA_PATH,
    NORMALIZED_OUTPUT_PATH,
    REVIEW_SUMMARY_PATH,
    RUN_ID,
    SCORED_TRACE_PATH,
    generate_m107b_deepseek_artifacts,
)
from validate_local_run_ledger import validate_local_run_ledger  # noqa: E402


class M107BDeepSeekReviewedLedgerTests(unittest.TestCase):
    def test_committed_deepseek_ledger_validates(self):
        summary = validate_local_run_ledger(LEDGER_PATH)

        self.assertEqual(summary["ledger_id"], LEDGER_ID)
        self.assertEqual(summary["ledger_kind"], "published_local_benchmark")
        self.assertEqual(summary["entry_count"], 1)
        self.assertEqual(summary["normalized_output_records"], 70)
        self.assertEqual(summary["scored_trace_records"], 70)

    def test_generator_refreshes_public_safe_derivatives(self):
        summary = generate_m107b_deepseek_artifacts()

        self.assertEqual(summary["ledger_id"], LEDGER_ID)
        self.assertEqual(summary["records"], 70)
        self.assertEqual(summary["pass_count"] + summary["fail_count"], 70)
        for path in [NORMALIZED_OUTPUT_PATH, SCORED_TRACE_PATH, REVIEW_SUMMARY_PATH, METADATA_PATH, LEDGER_PATH]:
            self.assertTrue(path.exists(), path)

    def test_deepseek_ledger_records_standard_coding_family_run(self):
        ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        entry = ledger["entries"][0]

        self.assertEqual(entry["run_id"], RUN_ID)
        self.assertEqual(entry["model"], "deepseek-coder:6.7b-instruct")
        self.assertEqual(entry["case_set"]["benchmark_split"], "standard")
        self.assertTrue(entry["ranking_eligible"])
        self.assertFalse(entry["safety_assertions"]["raw_outputs_included"])


if __name__ == "__main__":
    unittest.main()
