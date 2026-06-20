import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import release_notes_summary  # noqa: E402
from release_notes_summary import (  # noqa: E402
    ReleaseNotesSummaryError,
    build_release_notes,
    generate_markdown,
    milestone_summary,
)


class ReleaseNotesSummaryTests(unittest.TestCase):
    def test_build_release_notes_uses_reporting_summary_and_milestones(self):
        release_notes = build_release_notes()

        self.assertEqual(release_notes["release_id"], "release_notes_latest")
        self.assertEqual(release_notes["generated_at"], "2026-06-20T00:00:00Z")
        self.assertTrue(release_notes["safety"]["public_safe"])
        self.assertFalse(release_notes["safety"]["live_execution"])
        self.assertEqual(release_notes["dashboard_snapshot"]["baseline_records"], 126)
        self.assertEqual(release_notes["dashboard_snapshot"]["external_fixture_records"], 34)
        self.assertEqual(release_notes["dashboard_snapshot"]["harness_bridge_decision"], "defer_harness_integration")
        self.assertEqual(len(release_notes["milestones"]), 7)
        self.assertEqual(release_notes["milestones"][-1]["milestone_id"], "M41")
        self.assertGreaterEqual(release_notes["quality_gate"]["report_artifacts_indexed"], 20)

    def test_generate_markdown_contains_release_sections(self):
        markdown = generate_markdown(build_release_notes())

        self.assertIn("# Agent Behavior Evals Lab Release Notes", markdown)
        self.assertIn("## Highlights", markdown)
        self.assertIn("## Dashboard Snapshot", markdown)
        self.assertIn("## Milestone Rollup", markdown)
        self.assertIn("Evidence Quality", markdown)
        self.assertIn("Transcript Expansion", markdown)
        self.assertIn("No live provider APIs", markdown)

    def test_milestone_summary_extracts_title_status_and_date(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "milestone.md"
            path.write_text(
                "# Milestone 99 - Temporary\n\nDate: 2026-06-20\n\nStatus: Complete / review-ready\n",
                encoding="utf-8",
            )

            summary = milestone_summary(path)

            self.assertEqual(summary["milestone_id"], "M99")
            self.assertEqual(summary["title"], "Milestone 99 - Temporary")
            self.assertEqual(summary["date"], "2026-06-20")
            self.assertEqual(summary["status"], "Complete / review-ready")

    def test_milestone_summary_rejects_missing_title(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "milestone.md"
            path.write_text("Status: Complete / review-ready\n", encoding="utf-8")

            with self.assertRaisesRegex(ReleaseNotesSummaryError, "missing title"):
                milestone_summary(path)

    def test_missing_milestone_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original_paths = release_notes_summary.MILESTONE_PATHS
            release_notes_summary.MILESTONE_PATHS = [Path(temp_dir) / "missing.md"]
            try:
                with self.assertRaisesRegex(ReleaseNotesSummaryError, "does not exist"):
                    build_release_notes()
            finally:
                release_notes_summary.MILESTONE_PATHS = original_paths


if __name__ == "__main__":
    unittest.main()
