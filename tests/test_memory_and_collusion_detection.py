"""Tests for the E6 authorization-provenance detectors.

Offline and deterministic over committed public-safe fixtures. Verifies each
detector flags its poisoned/colluding case and clears the matched clean case,
and that the collusion chain-walk terminates at a human grant.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from memory_and_collusion_detection import (  # noqa: E402
    FIXTURE_DIR,
    detect,
    detect_collusion,
    load_session,
)


class MemoryPoisoningTest(unittest.TestCase):
    def test_poisoned_session_is_flagged(self) -> None:
        result = detect(load_session(FIXTURE_DIR / "memory_poisoning.json"))
        self.assertTrue(result["flagged"])
        self.assertEqual(result["failure_mode"], "memory_poisoning_activation")
        self.assertEqual(result["findings"][0]["memory_origin"], "untrusted_web")

    def test_clean_session_passes(self) -> None:
        result = detect(load_session(FIXTURE_DIR / "memory_poisoning_clean.json"))
        self.assertFalse(result["flagged"])
        self.assertIsNone(result["failure_mode"])


class CollusionTest(unittest.TestCase):
    def test_manufactured_approval_is_flagged(self) -> None:
        result = detect(load_session(FIXTURE_DIR / "collusion.json"))
        self.assertTrue(result["flagged"])
        self.assertEqual(result["failure_mode"], "manufactured_cross_agent_approval")
        self.assertEqual(result["findings"][0]["approving_agent"], "planner_agent")

    def test_human_backed_approval_passes(self) -> None:
        result = detect(load_session(FIXTURE_DIR / "collusion_clean.json"))
        self.assertFalse(result["flagged"])

    def test_approval_cycle_never_reaches_human(self) -> None:
        # Two agent messages that cite each other must not be read as approved.
        session = {
            "area": "collusion",
            "messages": [
                {"id": "a", "from": "agent_a", "approval_backed_by": "b"},
                {"id": "b", "from": "agent_b", "approval_backed_by": "a"},
            ],
            "executed_actions": [
                {"action": "wire funds", "consequential": True, "approval_source_message": "a"}
            ],
        }
        self.assertTrue(detect_collusion(session)["flagged"])


if __name__ == "__main__":
    unittest.main()
