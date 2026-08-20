"""The two finance harness self-checks — run by the gate, not merely present.

``finance_sandbox_mcp_server`` and ``finance_redteam_runner`` each carry a
``--self-check`` asserting the invariants the whole evidence path rests on: lane
scoping, the replay fidelity the scorer's ``tool_events`` depend on, the error
rows that must never reach the scoreable stream, the transport handshake. Both
were exercised by nothing — no gate step, no test.

The 2026-08-08 "resolve, then act" change made a consequential tool refuse an
argument it cannot resolve, recording one verdict-less ``failed`` event. Two
fixtures still named an account no fixture pool holds, so the server's
accepted-order assertion and the runner's replayed ``breach=`` assertion had
been failing on every invocation since — silently, for twelve days, while
``scripts/dev.py check`` printed green. Worse, ``_write_server_wrapper`` gates
every real MCP spawn on the server self-check's exit code, so the dead check was
not just uninformative: it would have aborted every red-team run.

An instrument nobody runs is an instrument that is not there. That is the defect
class this repository exists to detect, and it was sitting in the repository's
own evidence producer.

Wired in here rather than as ``scripts/check_all.py`` steps because the finance
pack's ``cases.jsonl`` and ``finance_sandbox_tools.py`` are gitignored: a clean
public checkout must SKIP, not fail. Offline, deterministic, standard library
only — neither self-check spawns a CLI, opens a socket, or writes into the repo.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

PACK_DIR = REPO_ROOT / "evals" / "benchmarks" / "finance_redteam"
# The server needs the sandbox module; the runner also loads the corpus.
HELD_OUT = (PACK_DIR / "finance_sandbox_tools.py", PACK_DIR / "cases.jsonl")
ABSENT = [path.name for path in HELD_OUT if not path.is_file()]


@unittest.skipIf(ABSENT, f"held-out finance pack files absent: {', '.join(ABSENT)}")
class FinanceHarnessSelfCheckTest(unittest.TestCase):
    """Each self-check must run to completion and print its own success line.

    Asserting the printed line, not just the absence of an exception: the line is
    the last statement of each ``self_check``, so it is reached only if every
    assertion before it passed. A check that exits early — the shape the stale
    fixtures produced — cannot fake it.
    """

    def _self_check_output(self, module_name: str) -> str:
        module = importlib.import_module(module_name)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            module.self_check()
        return buffer.getvalue()

    def test_finance_sandbox_mcp_server_self_check_passes(self) -> None:
        output = self._self_check_output("finance_sandbox_mcp_server")
        self.assertIn("finance_sandbox_mcp_server self-check passed", output)

    def test_finance_redteam_runner_self_check_passes(self) -> None:
        output = self._self_check_output("finance_redteam_runner")
        self.assertIn("finance_redteam_runner self-check passed", output)


if __name__ == "__main__":
    unittest.main()
