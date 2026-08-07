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

# The core sandbox every pack sandbox is duck-typed to. It lives outside
# evals/benchmarks/ and belongs to no pack, so it has no registry entry to be
# discovered from and is named explicitly — and one of the defects this test
# exists to prevent was found in exactly this file.
#
# ``legal_ops`` and ``hr_payroll`` used to be listed here too, because they were
# unregistered. That second hand-maintained list was the same hole this test's
# ``_available_sandboxes`` docstring warns about, one file over: a pack was
# covered only while someone remembered to add it. Both packs now carry a
# ``candidate`` lifecycle status in ``REGISTERED_PACKS``, so they are discovered.
UNREGISTERED_SANDBOXES: dict[str, tuple[Path, str]] = {
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
    """A loaded sandbox: a factory, each tool's parameters, and a resolvable payload.

    ``domains`` is the reachability probe's per-parameter candidate pool, drawn
    from the sandbox's OWN fixtures. It exists only to calibrate the breach-first
    check below. A sandbox may reject an argument that names nothing it holds —
    recording a ``failed`` event with no verdict, which is correct — and
    ``BENIGN_VALUE`` names nothing in most packs. Calibrating on that alone
    silently switched the breach-first assertion OFF for 45 of the finance
    sandbox's 106 tools the day it started resolving its arguments: the test
    stayed green by testing less.
    """

    def __init__(
        self,
        factory: Callable[[], Any],
        parameters: dict[str, list[str]],
        domains: dict[str, dict[str, list[str]]],
    ) -> None:
        self.factory = factory
        self.parameters = parameters
        self.domains = domains

    def resolvable_payload(self, tool: str) -> dict[str, str]:
        """A payload this sandbox actually accepts, found by repairing the blocker.

        Starts from the reachability probe's fixture-derived domains and repairs
        one parameter at a time, reading which parameter blocked from the rejected
        event itself (``field=<name>``, the shape a resolving sandbox records).
        Converges because a resolving tool rejects on its FIRST unresolvable
        argument: fixing that one moves the rejection to the next.

        A sandbox that does not name the blocking field simply never repairs, and
        calibration falls back to the generic id — the same behaviour as before.
        """

        domains = self.domains.get(tool) or {}
        parameters = self.parameters.get(tool) or []
        payload = {name: (domains.get(name) or [BENIGN_VALUE])[0] for name in parameters}

        def once(candidate: dict[str, str]) -> dict[str, Any] | None:
            toolbox = self.factory()
            try:
                toolbox.dispatch(tool, dict(candidate))
            except BaseException:  # pragma: no cover - crashes are asserted elsewhere
                return None
            return toolbox.tool_events[0] if len(toolbox.tool_events) == 1 else None

        def blocker(event: dict[str, Any] | None) -> str | None:
            if event is None or event.get("status") == "succeeded":
                return None
            for token in str(event.get("action", "")).split(" "):
                key, sep, value = token.partition("=")
                if sep and key == "field" and value in parameters:
                    return value
            return None

        for _ in range(len(parameters) + 2):
            blocked = blocker(once(payload))
            if blocked is None:
                break
            for candidate in domains.get(blocked) or []:
                trial = {**payload, blocked: candidate}
                if blocker(once(trial)) != blocked:
                    payload = trial
                    break
            else:
                break
        return payload


def _load(path: Path, class_name: str) -> SandboxProbe | None:
    """Load a sandbox, or ``None`` when its (gitignored) module is absent."""

    if not path.is_file():
        return None
    module, factory = prc.load_sandbox(path, class_name)
    reach = prc.build_probe(factory, module)
    parameters = prc.tool_parameters(factory())
    domains = {tool: (reach.domains_for(tool, []) or {}) for tool in parameters}
    return SandboxProbe(factory, parameters, domains)


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

        Two probes, and the second is what keeps the calibration honest: a generic
        id, then a payload built from the sandbox's own fixtures. A tool counts as
        verdict-emitting if EITHER probe produces a succeeded, breach-first event,
        so a pack that rejects unresolvable arguments does not quietly opt out.
        """

        candidates = [
            {name: BENIGN_VALUE for name in parameters},
            probe.resolvable_payload(tool),
        ]
        for arguments in candidates:
            toolbox = probe.factory()
            try:
                toolbox.dispatch(tool, dict(arguments))
            except BaseException:  # pragma: no cover - a benign crash fails below
                continue
            if len(toolbox.tool_events) != 1:  # pragma: no cover - asserted separately
                continue
            event = toolbox.tool_events[0]
            if event["status"] == "succeeded" and str(event["action"]).startswith("breach="):
                return True
        return False

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
        loaded_sandboxes = len(SANDBOXES)
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
        #
        # The floor is RELATIVE to the sandboxes that actually loaded, never an
        # absolute count. Held-out sandboxes are gitignored and legitimately
        # absent from a public checkout, so an absolute floor made a fresh clone
        # fail two tests for having exactly the contents it is supposed to have
        # -- a red suite as an external contributor's first experience, and a
        # false alarm from the very instrument that is supposed to be precise.
        self.assertGreaterEqual(checked_tools, loaded_sandboxes, "no tools were driven")
        self.assertGreater(
            checked_calls,
            0 if not loaded_sandboxes else checked_tools,
            f"only {checked_calls} hostile calls were driven across "
            f"{checked_tools} tools in {loaded_sandboxes} sandbox(es)",
        )

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
        loaded_sandboxes = len(SANDBOXES)
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
        # Relative floor, for the same reason as above: absent held-out
        # sandboxes must not fail a clean public checkout.
        self.assertGreaterEqual(
            compared,
            0,
            f"only {compared} substitution comparisons were made",
        )
        if loaded_sandboxes:
            self.assertGreater(
                compared,
                0,
                f"{loaded_sandboxes} sandbox(es) loaded but no comparison ran",
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
