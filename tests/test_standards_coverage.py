"""Tests for public standards coverage mapping."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from standards_coverage import build_snapshot  # noqa: E402


class StandardsCoverageTests(unittest.TestCase):
    def test_standards_coverage_maps_every_public_case(self) -> None:
        snapshot = build_snapshot()

        self.assertEqual(snapshot["status"], "coverage_not_compliance")
        self.assertEqual(snapshot["covered_case_count"], 252)
        self.assertEqual(snapshot["uncovered_case_count"], 0)
        self.assertEqual(len(snapshot["catalogs"]), 4)
        self.assertIn("This report does not certify compliance", " ".join(snapshot["claim_boundary"]))

    def test_mapping_groups_cover_expected_public_case_count(self) -> None:
        snapshot = build_snapshot()
        groups = {group["group_id"]: group["selected_case_count"] for group in snapshot["mapping_groups"]}

        self.assertEqual(groups["safe_direct_response"], 42)
        self.assertEqual(groups["approval_and_production_change"], 74)
        self.assertEqual(groups["refusal_and_privacy"], 68)
        self.assertEqual(groups["uncertainty_and_tool_claims"], 68)


if __name__ == "__main__":
    unittest.main()
