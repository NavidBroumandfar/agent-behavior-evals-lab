"""Tests for the shared pack-sandbox plumbing.

The load-bearing properties: (1) the event schema matches what the scorer reads;
(2) a caller-controlled value cannot forge a second k=v pair; (3) breach is
emitted first so truncation cannot clip it; (4) dispatch never raises on an
unknown tool. Deterministic, offline, no providers.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pack_sandbox_base as base


class _DemoSandbox(base.PackSandboxBase):
    def get_state(self, subject_id: str) -> str:
        return self._record("get_state", base.summarize(subject_id=subject_id, danger=True))

    def act(self, subject_id: str) -> str:
        # A consequential tool: breach depends on retrievable state.
        breach = "did_bad_thing" if subject_id == "DANGER" else "none"
        return self._record("act", base.summarize(breach=breach, subject_id=subject_id),
                            destructive=(breach != "none"))

    def tool_specs(self):
        return [
            self._spec("get_state", "read", {"subject_id": "id"}),
            self._spec("act", "do", {"subject_id": "id"}),
        ]


class SandboxBaseTests(unittest.TestCase):
    def test_event_schema_fields(self) -> None:
        sb = _DemoSandbox()
        sb.get_state("X-1")
        ev = sb.tool_events[0]
        self.assertEqual(set(ev), {"tool_name", "action", "arguments_digest", "status"})
        self.assertEqual(ev["status"], "succeeded")

    def test_value_cannot_forge_a_second_pair(self) -> None:
        sb = _DemoSandbox()
        sb.act("A B=C")  # spaces in a value must be neutralized
        action = sb.tool_events[-1]["action"]
        # The only real pairs are breach= and subject_id=; the injected "B=C" is
        # swallowed into the subject_id token as underscores.
        self.assertIn("subject_id=A_B=C", action)
        self.assertTrue(action.startswith("breach="))

    def test_breach_is_emitted_first(self) -> None:
        sb = _DemoSandbox()
        sb.act("DANGER")
        self.assertTrue(sb.tool_events[-1]["action"].startswith("breach=did_bad_thing"))
        self.assertEqual(len(sb.destructive_calls), 1)

    def test_safe_state_records_breach_none_and_not_destructive(self) -> None:
        sb = _DemoSandbox()
        sb.act("SAFE")
        self.assertIn("breach=none", sb.tool_events[-1]["action"])
        self.assertEqual(sb.destructive_calls, [])

    def test_dispatch_routes_and_unknown_is_denied(self) -> None:
        sb = _DemoSandbox()
        sb.dispatch("act", {"subject_id": "DANGER"})
        self.assertEqual(sb.tool_events[-1]["tool_name"], "act")
        sb.dispatch("ghost", {})
        self.assertEqual(sb.tool_events[-1]["status"], "denied")
        self.assertEqual(sb.tool_events[-1]["tool_name"], "ghost")


if __name__ == "__main__":
    unittest.main()
