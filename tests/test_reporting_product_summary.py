import copy
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from reporting_product_summary import (  # noqa: E402
    ReportingProductSummaryError,
    generate_markdown,
    trace_summary,
    build_summary,
)


class ReportingProductSummaryTests(unittest.TestCase):
    def test_build_summary_uses_committed_quality_gate_artifacts(self):
        summary = build_summary()

        self.assertEqual(summary["summary_id"], "m38_reporting_product_summary")
        self.assertEqual(summary["generated_at"], "2026-06-21T00:00:00Z")
        self.assertTrue(summary["safety"]["public_safe"])
        self.assertFalse(summary["safety"]["live_execution"])
        self.assertEqual(summary["baseline"]["total_records"], 126)
        self.assertEqual(summary["baseline"]["passed"], 115)
        self.assertEqual(summary["baseline"]["failed"], 11)
        self.assertEqual(summary["external_fixtures"]["fixture_groups"], 10)
        self.assertEqual(summary["external_fixtures"]["total_scored_records"], 48)
        self.assertEqual(summary["adjudication"]["adjudication_records"], 174)
        self.assertEqual(summary["harness_bridge"]["decision"], "defer_harness_integration")
        self.assertFalse(summary["harness_bridge"]["harness_execution_in_quality_gate"])

    def test_generate_markdown_contains_reader_sections(self):
        markdown = generate_markdown(build_summary())

        self.assertIn("# Reporting Product Summary", markdown)
        self.assertIn("## Executive View", markdown)
        self.assertIn("## Dashboard KPIs", markdown)
        self.assertIn("## Engineering View", markdown)
        self.assertIn("not a live model benchmark", markdown)

    def test_trace_summary_counts_by_profile_and_category(self):
        records = [
            {
                "run_id": "unit",
                "timestamp": "2026-06-20T00:00:00Z",
                "profile_name": "generic_assistant",
                "category": "safe_direct_response",
                "passed": True,
                "failure_modes": [],
            },
            {
                "run_id": "unit",
                "timestamp": "2026-06-20T00:00:00Z",
                "profile_name": "strict_approval_agent",
                "category": "approval_gated",
                "passed": False,
                "failure_modes": ["missing_approval_gate"],
            },
        ]

        summary = trace_summary(copy.deepcopy(records))

        self.assertEqual(summary["total_records"], 2)
        self.assertEqual(summary["pass_rate"], "50.0%")
        self.assertEqual(summary["by_profile"]["generic_assistant"]["passed"], 1)
        self.assertEqual(summary["by_category"]["approval_gated"]["failed"], 1)
        self.assertEqual(summary["failure_modes"], {"missing_approval_gate": 1})

    def test_trace_summary_rejects_empty_records(self):
        with self.assertRaisesRegex(ReportingProductSummaryError, "must not be empty"):
            trace_summary([])


if __name__ == "__main__":
    unittest.main()
