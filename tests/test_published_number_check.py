"""Tests for the published-number provenance check.

Deterministic and local-only: no providers, no live agents, no external actions.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import published_number_check as pnc


class RepoStateTests(unittest.TestCase):
    def test_repo_numbers_are_current(self) -> None:
        self.assertEqual(pnc.check_published_numbers(), [])

    def test_main_returns_zero(self) -> None:
        self.assertEqual(pnc.main([]), 0)

    def test_every_claim_names_an_existing_artifact_and_field(self) -> None:
        for claim in pnc.PUBLISHED_CLAIMS:
            artifact = json.loads((REPO_ROOT / claim["artifact"]).read_text(encoding="utf-8"))
            self.assertIn(claim["field"], artifact, f"{claim['id']} points at a missing field")


class DriftDetectionTests(unittest.TestCase):
    """The check must FAIL when a quoted number stops matching its artifact."""

    def _with_temp_repo(self, readme_text: str, catch_rate: str = "21.8%") -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reports/comparisons").mkdir(parents=True)
            (root / "reports/comparisons/blind_red_team_audit.json").write_text(
                json.dumps({"catch_rate": catch_rate, "lying_records": 55}), encoding="utf-8"
            )
            (root / "README.md").write_text(readme_text, encoding="utf-8")
            claims = (
                {
                    "id": "blind_catch_rate",
                    "artifact": "reports/comparisons/blind_red_team_audit.json",
                    "field": "catch_rate",
                    "docs": ("README.md",),
                    "quotes": (r"it catches \*\*(\d+\.\d)%\*\*",),
                    "retired": ("14.5%",),
                },
            )
            with mock.patch.object(pnc, "REPO_ROOT", root), mock.patch.object(
                pnc, "PUBLISHED_CLAIMS", claims
            ), mock.patch.object(pnc, "FROZEN_CORPORA", ()):
                return pnc.check_published_numbers()

    def test_matching_number_passes(self) -> None:
        self.assertEqual(self._with_temp_repo("it catches **21.8%** of attacks"), [])

    def test_drifted_number_is_reported(self) -> None:
        problems = self._with_temp_repo("it catches **19.4%** of attacks")
        self.assertTrue(problems)
        self.assertIn("19.4", problems[0])

    def test_retired_value_is_reported(self) -> None:
        problems = self._with_temp_repo("it catches **21.8%**, up from 14.5% before")
        self.assertTrue(any("retired" in p for p in problems))

    def test_missing_statement_is_reported(self) -> None:
        problems = self._with_temp_repo("the verifier is quite good")
        self.assertTrue(any("no recognizable statement" in p for p in problems))


class FrozenCorpusTests(unittest.TestCase):
    def test_blind_corpus_matches_its_freeze_manifest(self) -> None:
        manifest = json.loads(
            (REPO_ROOT / "evals/adversarial/blind_red_team_manifest.json").read_text(encoding="utf-8")
        )
        actual = pnc._corpus_sha256("evals/adversarial/blind_red_team_cases.jsonl")
        self.assertEqual(
            actual,
            manifest["corpus_sha256"],
            "the blind corpus changed after freeze — pre/post-fix numbers would be incomparable",
        )


if __name__ == "__main__":
    unittest.main()
