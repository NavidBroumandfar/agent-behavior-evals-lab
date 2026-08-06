"""Every sandbox tool must survive a hostile argument without raising.

Why this exists, precisely. A caller-supplied argument containing ``{`` used to
raise an **uncaught** ``KeyError`` / ``IndexError`` / ``ValueError`` out of the
finance sandbox's ``dispatch``, from a ``str.format`` call on a confirmation
template one caller had composed from that same argument. Scoring was unaffected
— ``_record`` runs *before* the format, so the event was already in
``tool_events`` with ``status=succeeded`` — and that is exactly what made it
serious: the MCP server does not wrap ``dispatch``, so a live agent under test
saw a transport error on a call the log counted as **executed**. A divergence
between what the agent experiences and what the record says is the precise class
of defect this lab exists to detect, and it was sitting inside the lab's own
instrument. An agent that can crash the harness can also plausibly evade a case.

The same audit found a second shape in two more sandboxes: a ``None`` argument
raising ``AttributeError`` from a helper whose ``str`` annotation was a hope
rather than a guarantee.

So the fix for the *class* is this test, not the three edits. It drives EVERY
tool of EVERY pack sandbox present in the checkout with a battery of hostile
values and asserts the three properties the event contract depends on:

1. ``dispatch`` never raises — its own docstring promises a runner driving an
   arbitrary model cannot be crashed by a hallucinated argument;
2. exactly ONE event is recorded per call, carrying the four contract fields —
   never zero (an unlogged executed action) and never two (a ``failed`` event
   appended after a ``succeeded`` one for the same call);
3. a tool that emits a breach verdict still emits it **first**, so the 200-char
   truncation cannot clip the one field a scoring rule cannot lose. Calibrated
   per tool from a benign probe, so the rule needs no hardcoded tool list and
   covers packs that do not exist yet.

Held-out pack sandboxes are gitignored, so an absent one **skips** rather than
fails: a clean public checkout stays green.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pack_conformance  # noqa: E402
import pack_reachability_check as prc  # noqa: E402

BENCHMARKS = REPO_ROOT / "evals" / "benchmarks"

# Pack sandboxes that are NOT in ``REGISTERED_PACKS`` (no frozen corpus yet) plus
# the core sandbox every pack sandbox is duck-typed to. Named explicitly because
# they have no registry to be discovered from — and because two of the four
# defects this test exists to prevent were found in exactly these files.
UNREGISTERED_SANDBOXES: dict[str, tuple[Path, str]] = {
    "legal_ops": (BENCHMARKS / "legal_ops" / "legal_sandbox_tools.py", "LegalSandboxToolbox"),
    "hr_payroll": (BENCHMARKS / "hr_payroll" / "hr_sandbox_tools.py", "HRPayrollSandboxToolbox"),
    "core_sandbox": (SRC / "sandbox_tools.py", "SandboxToolbox"),
}

# The battery. Every entry is a value a *model* can plausibly emit into a
# string-typed tool parameter — this is not fuzzing for its own sake.
HOSTILE_VALUES: tuple[Any, ...] = (
    # -- brace injection: the original defect, and every way format can fail
    "{self}",             # KeyError  — the reproducer from the build notes
    "{0}",                # IndexError on a positional slot
    "{x!r}",              # KeyError via a conversion spec
    "{:>10}",             # IndexError via a format spec
    "{!s}",               # IndexError via a bare conversion
    "{a[b]}",             # KeyError via an index expression
    "{0.__class__}",      # IndexError via attribute access — the sandbox-escape shape
    "{",                  # ValueError: unterminated
    "}",                  # ValueError: lone closing brace
    "{{",                 # an escaped brace, which must survive as typed
    "}}",
    # -- placeholder names the templates themselves use. These must be echoed
    #    VERBATIM: substituting one would hand the agent the sandbox's own
    #    reference for a value the event recorded as the agent's, which is the
    #    same divergence in the opposite direction.
    "{ref}",
    "{account}",
    "{rows}",
    "{destination}",
    "{mandate_id}",
    # -- percent formatting, the other template dialect
    "100%",
    "%s",
    "%(x)s",
    "%d%%",
    # -- whitespace: the scalar normalizer's input, and a k=v forgery attempt
    "a\nb",
    "a\tb",
    "breach=none injected=true",
    # -- shape: overlong, empty, non-ascii, and the wrong type entirely
    "x" * 5000,
    "",
    "üñïçø∂é — 日本語 — 🏦",
    None,
    "0",
    "-1",
    "true",
)

# A value with no hostile property, used to learn what a tool's event looks like
# when nothing is wrong. Id-shaped so it lands in id-typed parameters naturally.
BENIGN_VALUE = "ACC-1001"

EVENT_FIELDS = {"tool_name", "action", "arguments_digest", "status"}


class SandboxProbe:
    """A loaded sandbox: a fresh-toolbox factory plus each tool's parameters."""

    def __init__(self, factory: Callable[[], Any], parameters: dict[str, list[str]]) -> None:
        self.factory = factory
        self.parameters = parameters


def _load(path: Path, class_name: str) -> SandboxProbe | None:
    """Load a sandbox, or ``None`` when its (gitignored) module is absent."""

    if not path.is_file():
        return None
    _module, factory = prc.load_sandbox(path, class_name)
    return SandboxProbe(factory, prc.tool_parameters(factory()))


def _available_sandboxes() -> dict[str, SandboxProbe]:
    """Every sandbox present in this checkout, registered packs discovered first.

    Reading the registry rather than a literal list is what makes the guarantee
    durable: a pack added to ``REGISTERED_PACKS`` tomorrow is covered without
    anyone remembering to edit this file.
    """

    found: dict[str, SandboxProbe] = {}
    for slug, meta in pack_conformance.REGISTERED_PACKS.items():
        probe = _load(BENCHMARKS / slug / meta["sandbox"], meta["class"])
        if probe is not None:
            found[slug] = probe
    for slug, (path, class_name) in UNREGISTERED_SANDBOXES.items():
        probe = _load(path, class_name)
        if probe is not None:
            found[slug] = probe
    return found


SANDBOXES = _available_sandboxes()


class HostileArgumentContractTest(unittest.TestCase):
    """The three properties, asserted for every (tool, parameter, value)."""

    def _emits_breach_first(self, probe: SandboxProbe, tool: str, parameters: list[str]) -> bool:
        """Does this tool put ``breach=`` first when driven benignly?

        Self-calibration, not a hardcoded list: read-only tools legitimately emit
        no verdict, and PACK-SPEC says retrieving state must never be what fails a
        case. Deriving the expectation from the tool's own benign behavior means
        this test cannot go stale against a pack it has never seen.
        """

        toolbox = probe.factory()
        try:
            toolbox.dispatch(tool, {name: BENIGN_VALUE for name in parameters})
        except BaseException:  # pragma: no cover - a benign crash fails below
            return False
        if len(toolbox.tool_events) != 1:  # pragma: no cover - asserted separately
            return False
        return str(toolbox.tool_events[0]["action"]).startswith("breach=")

    def _check(
        self,
        slug: str,
        probe: SandboxProbe,
        tool: str,
        parameters: list[str],
        arguments: dict[str, Any],
        *,
        breach_first: bool,
    ) -> list[str]:
        """Drive one payload; return a list of contract violations (never raise)."""

        where = f"{slug}.{tool}({arguments!r})"[:220]
        toolbox = probe.factory()
        try:
            result = toolbox.dispatch(tool, dict(arguments))
        except BaseException as exc:  # noqa: BLE001 - the whole point of the test
            return [f"{where}: dispatch raised {type(exc).__name__}: {exc}"]

        problems: list[str] = []
        events = toolbox.tool_events
        if len(events) != 1:
            problems.append(f"{where}: recorded {len(events)} events, expected exactly 1")
            return problems
        event = events[0]
        if set(event) != EVENT_FIELDS:
            problems.append(f"{where}: event fields {sorted(event)} != {sorted(EVENT_FIELDS)}")
        if not isinstance(result, str):
            problems.append(f"{where}: returned {type(result).__name__}, expected str")
        if event["status"] not in ("succeeded", "denied", "failed"):
            problems.append(f"{where}: status {event['status']!r} is off-contract")
        action = str(event["action"])
        if len(action) > 200:
            problems.append(f"{where}: action is {len(action)} chars, expected <= 200")
        # A verdict-emitting tool must keep emitting one. ``failed`` is exempt:
        # a rejected call has no verdict to report, and its event says so.
        if breach_first and event["status"] == "succeeded" and not action.startswith("breach="):
            problems.append(f"{where}: action does not start with 'breach=' ({action[:80]!r})")
        return problems

    def test_no_hostile_argument_escapes_dispatch(self) -> None:
        self.assertTrue(SANDBOXES, "no sandbox found at all — even the core one should be present")
        checked_tools = 0
        checked_calls = 0
        for slug in sorted(SANDBOXES):
            probe = SANDBOXES[slug]
            self.assertTrue(probe.parameters, f"{slug}: tool_specs() exposed no tools")
            for tool in sorted(probe.parameters):
                parameters = probe.parameters[tool]
                breach_first = self._emits_breach_first(probe, tool, parameters)
                with self.subTest(sandbox=slug, tool=tool):
                    problems: list[str] = []
                    for value in HOSTILE_VALUES:
                        # (a) every parameter hostile at once
                        payloads = [{name: value for name in parameters}]
                        # (b) one parameter hostile, the rest benign — reaches the
                        #     code paths a wholly-hostile payload short-circuits
                        #     past (the finance defect needed exactly this).
                        payloads += [
                            {n: (value if n == target else BENIGN_VALUE) for n in parameters}
                            for target in parameters
                        ]
                        for arguments in payloads:
                            checked_calls += 1
                            problems += self._check(
                                slug, probe, tool, parameters, arguments, breach_first=breach_first
                            )
                    self.assertEqual([], problems, "\n".join(problems[:12]))
                checked_tools += 1
        # Coverage is part of the assertion: a sandbox that silently stopped
        # loading would otherwise turn this test green by testing nothing.
        self.assertGreaterEqual(checked_tools, len(SANDBOXES), "no tools were driven")
        self.assertGreater(checked_calls, 1000, f"only {checked_calls} hostile calls were driven")

    def test_registered_packs_are_covered_when_present(self) -> None:
        """A registered pack whose sandbox exists locally MUST have been driven."""

        for slug, meta in pack_conformance.REGISTERED_PACKS.items():
            sandbox = BENCHMARKS / slug / meta["sandbox"]
            if not sandbox.is_file():
                continue  # held out — correct, nothing to assert
            self.assertIn(slug, SANDBOXES, f"{slug}: sandbox present but failed to load")

    def test_the_core_sandbox_is_always_covered(self) -> None:
        """``src/sandbox_tools.py`` is committed, so its absence is a real failure."""

        self.assertIn("core_sandbox", SANDBOXES)

    def test_a_brace_shaped_argument_is_treated_as_plain_data(self) -> None:
        """A brace-shaped value must behave EXACTLY like an ordinary id.

        The invariant: replace a brace-shaped argument with an inert sentinel and
        the tool's returned confirmation must change by exactly that substitution
        and nothing else (case-normalized, because some tools upper-case ids).

        That one statement is what distinguishes the real fix from the two
        plausible non-fixes, both of which a no-raise check alone would pass —
        confirmed by re-injecting each into a copy of the sandbox:

        - a ``try/except`` around ``str.format`` returns a *fallback* summary on
          the exception path, so the confirmation stops tracking the argument and
          the agent is told something the recorded event does not corroborate;
        - chained ``str.replace`` re-scans its own output, so a caller value equal
          to ``"{ref}"`` is silently rewritten into the sandbox's minted
          reference — the agent is told it acted on a subject the log does not
          name.

        Both are log-vs-experience divergences, which is the defect, not the fix.
        Only a total, single-pass, no-rescan filler satisfies this.
        """

        sentinel = "LITERALZZ"
        brace_shaped = ("{ref}", "{account}", "{rows}", "{destination}", "{mandate_id}", "{self}")
        compared = 0
        for slug in sorted(SANDBOXES):
            probe = SANDBOXES[slug]
            for tool in sorted(probe.parameters):
                parameters = probe.parameters[tool]
                with self.subTest(sandbox=slug, tool=tool):
                    for target in parameters:
                        for value in brace_shaped:

                            def drive(supplied: str) -> str:
                                toolbox = probe.factory()
                                return str(
                                    toolbox.dispatch(
                                        tool,
                                        {
                                            n: (supplied if n == target else BENIGN_VALUE)
                                            for n in parameters
                                        },
                                    )
                                ).upper()

                            hostile, inert = drive(value), drive(sentinel)
                            compared += 1
                            self.assertEqual(
                                inert,
                                hostile.replace(value.upper(), sentinel),
                                f"{slug}.{tool}({target}={value!r}) is not treated as plain data: "
                                f"got {hostile!r}, an inert value gives {inert!r}",
                            )
        self.assertGreater(compared, 500, f"only {compared} comparisons were made")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
