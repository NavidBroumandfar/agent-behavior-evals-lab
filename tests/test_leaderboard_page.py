"""Tests for the static leaderboard page generator. Offline and deterministic."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from leaderboard_page import (
    DEFAULT_OUTPUT_PATH,
    DEFAULT_REPORT_PATH,
    LeaderboardPageError,
    generate,
    load_report,
    render_page,
)


class LeaderboardPageTest(unittest.TestCase):
    def test_renders_all_ranked_models(self) -> None:
        report = load_report(DEFAULT_REPORT_PATH)
        page = render_page(report)
        for entry in report["rankings"]:
            self.assertIn(str(entry["model"]), page)
        self.assertIn("Severity-weighted pass rate", page)
        self.assertIn("Limitations", page)

    def test_committed_page_matches_regeneration(self) -> None:
        self.assertTrue(DEFAULT_OUTPUT_PATH.exists(), "run src/leaderboard_page.py first")
        temp_output = Path(tempfile.mkdtemp()) / "index.html"
        generate(DEFAULT_REPORT_PATH, temp_output)
        self.assertEqual(
            temp_output.read_text(encoding="utf-8"),
            DEFAULT_OUTPUT_PATH.read_text(encoding="utf-8"),
        )

    def test_missing_report_raises(self) -> None:
        with self.assertRaises(LeaderboardPageError):
            load_report(Path(tempfile.mkdtemp()) / "missing.json")


if __name__ == "__main__":
    unittest.main()
