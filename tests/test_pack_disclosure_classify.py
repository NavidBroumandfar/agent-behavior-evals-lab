"""Guards for the disclosure classification report.

Offline: every case builds a synthetic ledger, so nothing here needs a provider, a
credential or a held-out corpus.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pack_disclosure_classify as pdc
from repo_config import REPO_ROOT


def ledger(judges, meta):
    return {"judges": judges, "meta": meta}


class MajorityTests(unittest.TestCase):
    def test_majority_needs_no_unanimity_but_reports_the_split(self) -> None:
        self.assertEqual(pdc.majority(["STATED", "STATED", "RETRIEVABLE"]), ("STATED", 2, 3))
        self.assertEqual(pdc.majority(["RETRIEVABLE"] * 3), ("RETRIEVABLE", 3, 3))

    def test_unparseable_votes_are_not_counted_as_votes(self) -> None:
        self.assertEqual(pdc.majority(["ERROR:URLError", "UNPARSED"]), ("NO_VOTE", 0, 0))
        self.assertEqual(pdc.majority(["ERROR:X", "STATED"]), ("STATED", 1, 1))


class JudgeExclusionTests(unittest.TestCase):
    def test_a_judge_that_errored_on_everything_is_excluded(self) -> None:
        """A failed judge must not become a silent third vote."""

        l = ledger(
            {"good": {"A": "STATED", "B": "RETRIEVABLE"},
             "broken": {"A": "ERROR:URLError", "B": "ERROR:URLError"}},
            {"A": {"pack": "p", "b05": False}, "B": {"pack": "p", "b05": False}},
        )
        used = pdc.usable_judges(l)
        self.assertIn("good", used)
        self.assertNotIn("broken", used)
        self.assertIn("broken", pdc.analyse(l)["judges_excluded"])


class CalibrationTests(unittest.TestCase):
    def test_calibration_counts_and_names_the_misses(self) -> None:
        l = ledger(
            {"j": {"K1": "RETRIEVABLE", "K2": "STATED", "X": "STATED"}},
            {"K1": {"pack": "p", "b05": True}, "K2": {"pack": "p", "b05": True},
             "X": {"pack": "p", "b05": False}},
        )
        cal = pdc.analyse(l)["calibration"]["j"]
        self.assertEqual(cal["known_hidden"], 2)
        self.assertEqual(cal["recovered"], 1)
        self.assertEqual(cal["missed"], ["K2"])


class LedgerTests(unittest.TestCase):
    def test_the_committed_ledger_carries_no_prose(self) -> None:
        """The ledger must never grow a rationale field.

        It is committed so the aggregate re-derives without a provider. The moment it
        carries model prose it also carries scenario content, and it stops being publishable.
        """

        raw = pdc.LEDGER.read_text(encoding="utf-8")
        data = json.loads(raw)
        self.assertEqual(sorted(data), ["judges", "meta"])
        for votes in data["judges"].values():
            for value in votes.values():
                self.assertLessEqual(len(str(value)), 32, "a vote grew into prose")
        for row in data["meta"].values():
            self.assertEqual(sorted(row), ["b05", "pack"])

    def test_the_report_regenerates_from_the_committed_ledger_alone(self) -> None:
        a = pdc.analyse(pdc.load_ledger())
        self.assertGreater(len(a["rows"]), 0)
        self.assertGreaterEqual(len(a["judges_used"]), 2, "no-single-judge rule")
        text = pdc.render(a)
        self.assertIn("Calibration", text)
        self.assertIn("model judgements, not human ones", text)

    def test_a_missing_ledger_is_an_error_not_an_empty_report(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            rc = pdc.main(["--ledger", str(Path(d) / "absent.json")])
            self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
