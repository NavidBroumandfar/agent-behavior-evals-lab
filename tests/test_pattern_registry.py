"""Tests for the AGB failure-pattern registry. Offline and deterministic."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pattern_registry import (
    HTML_OUTPUT_PATH,
    JSON_OUTPUT_PATH,
    V2_CASE_PATH,
    build_registry,
    generate,
)


class PatternRegistryTest(unittest.TestCase):
    def test_forty_unique_permanent_ids(self) -> None:
        registry = build_registry()
        ids = [pattern["pattern_id"] for pattern in registry["patterns"]]
        self.assertEqual(len(ids), 40)
        self.assertEqual(len(set(ids)), 40)
        self.assertEqual(ids[0], "AGB-001")
        self.assertEqual(ids[-1], "AGB-040")

    def test_every_pattern_maps_to_a_real_v2_case(self) -> None:
        case_ids = {
            json.loads(line)["case_id"]
            for line in V2_CASE_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        for pattern in build_registry()["patterns"]:
            self.assertIn(pattern["example_case_id"], case_ids)

    def test_committed_artifacts_match_regeneration(self) -> None:
        self.assertTrue(JSON_OUTPUT_PATH.exists(), "run src/pattern_registry.py first")
        temp_dir = Path(tempfile.mkdtemp())
        json_path = temp_dir / "registry.json"
        html_path = temp_dir / "index.html"
        generate(json_path, html_path)
        self.assertEqual(
            json_path.read_text(encoding="utf-8"),
            JSON_OUTPUT_PATH.read_text(encoding="utf-8"),
        )
        self.assertEqual(
            html_path.read_text(encoding="utf-8"),
            HTML_OUTPUT_PATH.read_text(encoding="utf-8"),
        )

    def test_html_page_cites_patterns(self) -> None:
        page = HTML_OUTPUT_PATH.read_text(encoding="utf-8")
        self.assertIn("AGB-030", page)
        self.assertIn("approval by silence", page)


if __name__ == "__main__":
    unittest.main()
