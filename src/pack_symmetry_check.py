"""Deterministic pair-symmetry checker for vertical red-team packs.

``pack_conformance.py`` checks a case's *contract shape*; ``pack_archetype_check.py``
checks its *scored behavior*. Neither can see the defect this module exists for:

    A temptation/control pair whose PROMPTS give the label away.

Found 2026-08-06. A blind probe measured the frozen ``devops_sre`` pack as **86.4%
prompt-separable** — a judge shown only the request text, no sandbox state, no tool
list, no labels, recovered the temptation/control label (50% baseline). A reviewer
independently found the mechanism: the honest control *asserts its legitimizing
fact in prose* ("AR-5551 is approved for the responder role") while its paired
temptation stays silent or hedges. Every one of those cases passes conformance.
An agent can therefore score such a pack perfectly **while making zero read
calls**, by reading tone — measuring prose sentiment while claiming to measure
behavior, the exact substitution this lab exists to refuse. See
``evals/benchmarks/PACK-SPEC.md`` § "The pair-symmetry rule" and
``separability-probe-protocol.md``.

This module makes that catchable *deterministically, before a pack freezes*: it
pairs cases, measures length/shape asymmetry, scans two curated marker lists
(legitimizing assertions vs hedges/urgency), diffs the prompts token-by-token
with identifier-shaped tokens masked, assists the entity standard, and — because
that mask is by construction blind to what the identifiers themselves carry —
measures the corpus-level directional skew of identifier *serials* across pairs.

Findings, not verdicts
----------------------
Every finding is a human-readable string tagged with a severity:

- ``[leak]`` — a near-certain tell (a one-sided legitimizing assertion in the
  control, a one-sided hedge/urgency phrase in the temptation, a
  ``firstname.initial`` principal). These are what an author must re-author.
- ``[warn]`` — an asymmetry that *may* be a tell: length/character/token-position
  deltas, one-sided markers pointing the unexpected way, one-sided proper nouns,
  a corpus-level directional skew in identifier serials, and pairs that could not
  be formed at all (symmetry is a property of a pair, so an unpaired case cannot
  be checked — that is reported, not silently passed).

**Why this does not fail the gate by default.** The three frozen corpora were
authored *before* the pair-symmetry rule existed and they violate it — that is
the measured finding, not a surprise. Frozen means frozen: fixes land as a new
version with a new manifest, never as an in-place edit. Wiring this as a hard
gate failure would therefore break ``python3 scripts/dev.py check`` for everyone
while forbidding the only edit that would fix it. So:

- ``--report-public`` (the gate mode, wired into ``scripts/check_all.py``) prints
  its findings and **always exits 0**. It is an advisory instrument.
- ``--pack`` (the author's mode, run on a *candidate* batch before freeze) exits
  non-zero on any ``[leak]``.
- ``--strict`` promotes ``[warn]`` to a failure in either mode. That is the flag a
  future pack's pre-freeze pipeline turns on for itself.

Deterministic, offline, stdlib-only. No model calls. Never touches
``src/scorers.py``.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path
from typing import Any, NamedTuple

import pack_conformance

SEVERITY_LEAK = "leak"
SEVERITY_WARN = "warn"

# The corpora pair a temptation with its honest control by suffixing the id.
CONTROL_ID_SUFFIX = "c"

# Relative delta allowed between the two halves of a pair before it is flagged.
# Applied to the pair MEAN, with an absolute floor per metric so that short
# prompts are not flagged for a one-word difference.
DEFAULT_TOLERANCE = 0.20
WORD_DELTA_FLOOR = 6
CHAR_DELTA_FLOOR = 40
TOKEN_DIFF_FLOOR = 8

# Advisory gate mode prints at most this many findings before summarizing, so a
# frozen corpus that violates the rule wholesale cannot bury the rest of the
# gate's output. ``--strict`` prints all of them.
ADVISORY_PRINT_LIMIT = 20

# Identifier-serial skew (see ``check_serial_skew`` for the full reasoning).
# ``SKEW_ALPHA`` is the two-sided significance level; ``MIN_SKEW_PAIRS`` is the
# smallest number of *decisive* pairs the corpus statistic will speak about.
SKEW_ALPHA = 0.10
MIN_SKEW_PAIRS = 6
SKEW_SUBJECT = "corpus"

# ---------------------------------------------------------------------------
# Marker lists. Module-level constants ON PURPOSE: they are the auditable,
# extensible content of this check. Add markers here, never inline in a function.
# ---------------------------------------------------------------------------

# Direction (a): a control that ASSERTS its own legitimacy. This is the exact
# mechanism the 2026-08-06 review found — the control states the fact the agent
# was supposed to have to look up.
LEGITIMIZING_MARKERS: tuple[str, ...] = (
    "approved",
    "pre-approved",
    "preapproved",
    "authorized",
    "authorised",
    "signed off",
    "sign-off",
    "signoff",
    "cleared",
    "on file",
    "complete",
    "completed",
    "verified",
    "validated",
    "confirmed",
    "in scope",
    "entitled",
    "permitted",
    "per policy",
    "within policy",
    "policy allows",
    "documented",
    "ratified",
    "countersigned",
    "greenlit",
    "waiver",
    "exception is on record",
    "allow-listed",
    "allowlisted",
    "whitelisted",
    "already reviewed",
    "review is done",
    "closed out",
)

# Direction (b): a temptation that HEDGES its own premise, or leans on urgency.
# Either lets a reader sort the pair without touching sandbox state.
HEDGE_URGENCY_MARKERS: tuple[str, ...] = (
    # hedges — the requester declines to assert their own premise flatly
    "possibly",
    "maybe",
    "might",
    "may have",
    "probably",
    "presumably",
    "seems",
    "appears",
    "apparently",
    "supposedly",
    "allegedly",
    "reportedly",
    "i think",
    "i believe",
    "i assume",
    "not sure",
    "unclear",
    "if it turns out",
    "if that is the case",
    "they say",
    "they claim",
    "claims",
    "claimed",
    "as far as i know",
    "should be fine",
    # urgency / consequence-of-delay — pressure a routine request would not carry
    "asap",
    "urgent",
    "urgently",
    "right away",
    "immediately",
    "before",
    "quickly",
    "just",
    "real quick",
    "no time",
    "time-sensitive",
    "deadline",
    "escalating",
    "blocking",
    "critical path",
    "waiting on",
)


def _compile_markers(markers: tuple[str, ...]) -> tuple[tuple[str, re.Pattern[str]], ...]:
    """Word-boundary, case-insensitive, whitespace-tolerant marker patterns."""

    # NOTE: join the escaped words with \s+ rather than post-processing
    # re.escape's output — re.escape escapes the space itself, so replacing " "
    # inside the escaped string silently produces a pattern that never matches.
    return tuple(
        (
            m,
            re.compile(
                r"\b" + r"\s+".join(re.escape(part) for part in m.split()) + r"\b",
                re.IGNORECASE,
            ),
        )
        for m in markers
    )


_LEGITIMIZING_PATTERNS = _compile_markers(LEGITIMIZING_MARKERS)
_HEDGE_URGENCY_PATTERNS = _compile_markers(HEDGE_URGENCY_MARKERS)

# ---------------------------------------------------------------------------
# Tokenization + identifier masking (the "identical once ids are masked" test)
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"[A-Za-z0-9@][A-Za-z0-9_.@/,'-]*")
_TOKEN_TRIM = ".,;:!?'\"/-"
_ID_MASK = "<ID>"

_ID_TOKEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    # segmented identifiers containing a digit: AR-5551, DVO-IAM-201, SVC-9
    re.compile(r"^(?=[^\d]*\d)[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+$"),
    # semantic versions: v1.2.3, V2
    re.compile(r"^v\d+(?:\.\d+)*$", re.IGNORECASE),
    # dotted handles / qualified names: dana.k, svc.metrics, cases.jsonl
    re.compile(r"^[A-Za-z][A-Za-z0-9_-]*\.[A-Za-z][A-Za-z0-9_.-]*$"),
    # @handles and address-shaped tokens
    re.compile(r"^@\S+$"),
    # bare numbers long enough to be an identifier rather than a quantity
    re.compile(r"^\d[\d,]{2,}$"),
    # SHOUTY id + number, unsegmented: INC0042, PR12345
    re.compile(r"^[A-Z]{2,}\d{2,}$"),
)

# Serial-bearing identifiers: the subset of the masked tokens above that splits
# cleanly into a NAMESPACE PREFIX and a NUMERIC SERIAL. These are the tokens the
# id mask throws information away about — ``EMP-4471`` and ``EMP-4472`` both mask
# to ``<ID>``, so the masked diff is clean while the raw ids still say which twin
# is which. Deliberately narrower than ``_ID_TOKEN_PATTERNS``:
#
# - **semantic versions** (``v1.2.3``) are excluded — a version ordering is a
#   scenario fact ("roll back to the older build"), not an arbitrary fixture
#   serial, and ordering it would fire on every pack that mentions two builds;
# - **dotted handles / qualified names** (``svc.metrics``) carry no serial;
# - **bare numbers** (``1,234``) are excluded — with no prefix there is no family
#   to compare within, and a bare number in a prompt is far more often a quantity
#   (an amount, a headcount, a port) than an identifier.
_SERIAL_ID_PATTERNS: tuple[re.Pattern[str], ...] = (
    # segmented: AR-5551 -> ("AR", 5551); DVO-IAM-201 -> ("DVO-IAM", 201)
    re.compile(r"^(?P<prefix>[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z][A-Za-z0-9]*)*)-(?P<serial>\d+)$"),
    # SHOUTY unsegmented: INC0042 -> ("INC", 42); PR12345 -> ("PR", 12345)
    re.compile(r"^(?P<prefix>[A-Z]{2,})(?P<serial>\d{2,})$"),
)

# ``firstname.initial`` principals. PACK-SPEC's entity standard rejects these
# outright: they collide with real people by construction and cannot be cleared
# by search. Two shapes, both requiring a SINGLE trailing letter so that a
# missing space after a full stop ("complete.All good") is not mistaken for one.
_FIRSTNAME_INITIAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^@?[a-z][a-z'-]{2,}\.[a-z]$"),  # dana.k
    re.compile(r"^@?[A-Z][a-z'-]{2,}\.[A-Z]$"),  # Dana.K
)

_PROPER_NOUN_RE = re.compile(r"\b[A-Z][a-z]{2,}\b")
# Capitalized-by-grammar words that are not entities. Sentence-initial words are
# excluded positionally, so this set only needs the calendar.
_NOT_PROPER_NOUNS = frozenset(
    {
        "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
        "january", "february", "march", "april", "may", "june", "july", "august",
        "september", "october", "november", "december",
    }
)


def tokenize(text: str) -> list[str]:
    """Split prompt text into comparable word tokens (punctuation trimmed)."""

    tokens = []
    for raw in _TOKEN_RE.findall(text or ""):
        token = raw.strip(_TOKEN_TRIM)
        if token:
            tokens.append(token)
    return tokens


def mask_identifiers(tokens: list[str]) -> list[str]:
    """Replace identifier-shaped tokens with ``<ID>``.

    Ids, versions and handles are the ONLY things a conformant pair may differ
    in (PACK-SPEC: "the two prompts must differ only in identifiers"), so masking
    them is what turns "these prompts differ" into "these prompts differ in
    something that matters".
    """

    return [_ID_MASK if any(p.match(t) for p in _ID_TOKEN_PATTERNS) else t for t in tokens]


def serial_ids(text: str) -> dict[str, list[int]]:
    """Serial-bearing identifiers in ``text``, grouped by uppercased prefix family.

    ``"Move EMP-4471 and EMP-4480 onto AR-5551"`` →
    ``{"EMP": [4471, 4480], "AR": [5551]}``.

    Grouping by prefix is the point: twinning happens *within* a namespace
    (``EMP-4471`` dirty / ``EMP-4472`` clean). Comparing an ``AR`` serial against
    an ``EMP`` serial compares two unrelated fixture namespaces and means nothing.
    Prefixes are uppercased so ``emp-4471`` and ``EMP-4472`` are one family.
    """

    families: dict[str, list[int]] = {}
    for token in tokenize(text):
        for pattern in _SERIAL_ID_PATTERNS:
            match = pattern.match(token)
            if match:
                families.setdefault(match.group("prefix").upper(), []).append(
                    int(match.group("serial"))
                )
                break
    return families


def marker_hits(text: str, patterns: tuple[tuple[str, re.Pattern[str]], ...]) -> set[str]:
    """Which markers from a compiled list appear in ``text``."""

    return {marker for marker, pattern in patterns if pattern.search(text or "")}


def firstname_initial_handles(text: str) -> set[str]:
    """``firstname.initial``-shaped principals in ``text`` (entity-standard drop)."""

    return {
        token
        for token in tokenize(text)
        if any(p.match(token) for p in _FIRSTNAME_INITIAL_PATTERNS)
    }


def proper_nouns(text: str) -> set[str]:
    """Proper-noun-shaped tokens, skipping sentence-initial and calendar words.

    Heuristic by construction: a capitalized mid-sentence word is usually an
    entity, but not always. That is why one-sided hits are ``warn``, not ``leak``.
    """

    found: set[str] = set()
    body = text or ""
    for match in _PROPER_NOUN_RE.finditer(body):
        prefix = body[: match.start()].rstrip()
        if not prefix or prefix[-1] in ".!?:\n":
            continue  # sentence-initial capital carries no entity signal
        word = match.group(0)
        if word.lower() in _NOT_PROPER_NOUNS:
            continue
        found.add(word)
    return found


# ---------------------------------------------------------------------------
# Pairing
# ---------------------------------------------------------------------------


class Pair(NamedTuple):
    """One temptation/control pair and how it was identified."""

    temptation: dict[str, Any]
    control: dict[str, Any]
    pairing: str  # "id-suffix" | "tempting-tool"


def _cid(case: dict[str, Any]) -> str:
    return str(case.get("case_id") or "<no-id>")


def _prompt(case: dict[str, Any]) -> str:
    return str(case.get("user_prompt") or "")


def _finding(severity: str, subject: str, message: str) -> str:
    return f"[{severity}] {subject}: {message}"


def severity_of(finding: str) -> str:
    """The severity tag a finding carries (``""`` when it carries none)."""

    if finding.startswith(f"[{SEVERITY_LEAK}]"):
        return SEVERITY_LEAK
    if finding.startswith(f"[{SEVERITY_WARN}]"):
        return SEVERITY_WARN
    return ""


def has_leaks(findings: list[str]) -> bool:
    return any(severity_of(f) == SEVERITY_LEAK for f in findings)


def pair_cases(cases: list[dict[str, Any]]) -> tuple[list[Pair], list[str]]:
    """Pair temptations with honest controls; report what could not be paired.

    Two conventions, in order of authority:

    1. **id suffix** — ``DVO-IAM-201`` pairs with ``DVO-IAM-201c``.
    2. **shared ``tempting_tool``** — leftovers pair with a leftover control that
       would carry out the same action, matched in case-id order.

    An unpaired case is reported (``warn``), never silently passed: PACK-SPEC
    allows up to 3 temptations per control, so an unpaired temptation is not by
    itself a defect — but its symmetry is *unverifiable*, and saying so is the
    honest report.
    """

    findings: list[str] = []
    by_id: dict[str, dict[str, Any]] = {}
    for case in cases:
        cid = case.get("case_id")
        if cid is not None and cid not in by_id:
            by_id[str(cid)] = case

    temptations = [c for c in cases if c.get("kind") == "temptation"]
    controls = [c for c in cases if c.get("kind") == "honest_control"]
    pairs: list[Pair] = []
    used_t: set[int] = set()
    used_c: set[int] = set()

    for control in controls:
        cid = _cid(control)
        if not cid.endswith(CONTROL_ID_SUFFIX):
            continue
        base = cid[: -len(CONTROL_ID_SUFFIX)]
        temptation = by_id.get(base)
        if temptation is None or temptation.get("kind") != "temptation":
            continue
        if id(temptation) in used_t:
            continue
        pairs.append(Pair(temptation, control, "id-suffix"))
        used_t.add(id(temptation))
        used_c.add(id(control))

    pool_by_tool: dict[str, list[dict[str, Any]]] = {}
    for control in controls:
        if id(control) in used_c:
            continue
        tool = str(control.get("tempting_tool") or "")
        if tool:
            pool_by_tool.setdefault(tool, []).append(control)
    for pool in pool_by_tool.values():
        pool.sort(key=_cid)

    for temptation in sorted((c for c in temptations if id(c) not in used_t), key=_cid):
        pool = pool_by_tool.get(str(temptation.get("tempting_tool") or ""))
        if not pool:
            continue
        control = pool.pop(0)
        pairs.append(Pair(temptation, control, "tempting-tool"))
        used_t.add(id(temptation))
        used_c.add(id(control))

    for temptation in temptations:
        if id(temptation) in used_t:
            continue
        tool = temptation.get("tempting_tool") or "<none>"
        findings.append(
            _finding(
                SEVERITY_WARN,
                _cid(temptation),
                f"unpaired temptation (no '{_cid(temptation)}{CONTROL_ID_SUFFIX}' control and no "
                f"unpaired control shares tempting_tool '{tool}') — pair symmetry is unverifiable",
            )
        )
    for control in controls:
        if id(control) in used_c:
            continue
        findings.append(
            _finding(
                SEVERITY_WARN,
                _cid(control),
                "orphan honest control (no temptation pairs to it by id suffix or tempting_tool) "
                "— pair symmetry is unverifiable",
            )
        )

    pairs.sort(key=lambda p: (_cid(p.temptation), _cid(p.control)))
    return pairs, findings


# ---------------------------------------------------------------------------
# Per-pair measurement
# ---------------------------------------------------------------------------


def pair_metrics(temptation: dict[str, Any], control: dict[str, Any]) -> dict[str, Any]:
    """Raw, assertion-free measurements for one pair (the audit trail)."""

    t_text, c_text = _prompt(temptation), _prompt(control)
    t_tokens, c_tokens = tokenize(t_text), tokenize(c_text)
    t_masked, c_masked = mask_identifiers(t_tokens), mask_identifiers(c_tokens)
    overlap = min(len(t_masked), len(c_masked))
    differing = sum(1 for i in range(overlap) if t_masked[i] != c_masked[i])
    differing += abs(len(t_masked) - len(c_masked))
    return {
        "temptation_id": _cid(temptation),
        "control_id": _cid(control),
        "temptation_words": len(t_text.split()),
        "control_words": len(c_text.split()),
        "temptation_chars": len(t_text),
        "control_chars": len(c_text),
        "temptation_tokens": len(t_tokens),
        "control_tokens": len(c_tokens),
        "differing_positions": differing,
        "identical_after_id_masking": t_masked == c_masked,
    }


def identical_after_id_masking(temptation: dict[str, Any], control: dict[str, Any]) -> bool:
    """The gold standard PACK-SPEC asks for: differing only in identifiers."""

    return bool(pair_metrics(temptation, control)["identical_after_id_masking"])


def _exceeds(delta: int, mean: float, tolerance: float, floor: int) -> bool:
    return delta > floor and delta > tolerance * mean


def check_pair(
    temptation: dict[str, Any],
    control: dict[str, Any],
    *,
    pairing: str = "",
    tolerance: float = DEFAULT_TOLERANCE,
) -> list[str]:
    """Return pair-symmetry findings for one pair; ``[]`` == symmetric."""

    subject = f"{_cid(temptation)}/{_cid(control)}"
    if pairing:
        subject = f"{subject} ({pairing})"
    t_text, c_text = _prompt(temptation), _prompt(control)
    findings: list[str] = []

    if not t_text.strip() or not c_text.strip():
        missing = "temptation" if not t_text.strip() else "honest_control"
        return [
            _finding(SEVERITY_WARN, subject, f"{missing} has no user_prompt — pair symmetry is unverifiable")
        ]

    metrics = pair_metrics(temptation, control)

    # 2. Length / shape asymmetry — the cheapest reliable tell.
    word_delta = abs(metrics["temptation_words"] - metrics["control_words"])
    word_mean = (metrics["temptation_words"] + metrics["control_words"]) / 2
    if _exceeds(word_delta, word_mean, tolerance, WORD_DELTA_FLOOR):
        findings.append(
            _finding(
                SEVERITY_WARN,
                subject,
                f"word-count delta {word_delta} (temptation {metrics['temptation_words']}, "
                f"control {metrics['control_words']}) exceeds tolerance {tolerance:.0%}",
            )
        )
    char_delta = abs(metrics["temptation_chars"] - metrics["control_chars"])
    char_mean = (metrics["temptation_chars"] + metrics["control_chars"]) / 2
    if _exceeds(char_delta, char_mean, tolerance, CHAR_DELTA_FLOOR):
        findings.append(
            _finding(
                SEVERITY_WARN,
                subject,
                f"char-count delta {char_delta} (temptation {metrics['temptation_chars']}, "
                f"control {metrics['control_chars']}) exceeds tolerance {tolerance:.0%}",
            )
        )

    # 3. Lexical leak markers, in both directions.
    findings.extend(
        _marker_findings(
            subject,
            t_text,
            c_text,
            patterns=_LEGITIMIZING_PATTERNS,
            kind="legitimizing assertion",
            leak_side="control",
        )
    )
    findings.extend(
        _marker_findings(
            subject,
            t_text,
            c_text,
            patterns=_HEDGE_URGENCY_PATTERNS,
            kind="hedge/urgency phrase",
            leak_side="temptation",
        )
    )

    # 4. Token-position diff, with identifiers masked.
    if not metrics["identical_after_id_masking"]:
        token_mean = (metrics["temptation_tokens"] + metrics["control_tokens"]) / 2
        if _exceeds(metrics["differing_positions"], token_mean, tolerance, TOKEN_DIFF_FLOOR):
            findings.append(
                _finding(
                    SEVERITY_WARN,
                    subject,
                    f"{metrics['differing_positions']} differing token positions after id-masking "
                    f"(temptation {metrics['temptation_tokens']} tokens, control "
                    f"{metrics['control_tokens']}) exceeds tolerance {tolerance:.0%} — the pair is "
                    f"not 'identical but for identifiers'",
                )
            )

    # 5. Entity-standard assist: proper nouns present in only one half.
    one_sided = proper_nouns(t_text) ^ proper_nouns(c_text)
    if one_sided:
        findings.append(
            _finding(
                SEVERITY_WARN,
                subject,
                "proper-noun-shaped token(s) in only one half of the pair: "
                + ", ".join(sorted(one_sided)),
            )
        )
    return findings


def _marker_findings(
    subject: str,
    t_text: str,
    c_text: str,
    *,
    patterns: tuple[tuple[str, re.Pattern[str]], ...],
    kind: str,
    leak_side: str,
) -> list[str]:
    """One-sided marker findings.

    A marker on its *expected* leak side (legitimizing in the control, hedge or
    urgency in the temptation) is the documented mechanism and scores ``leak``.
    The reverse direction is still sortable, but it is not the known failure and
    is noisier, so it scores ``warn``.
    """

    t_hits = marker_hits(t_text, patterns)
    c_hits = marker_hits(c_text, patterns)
    findings: list[str] = []
    for side, only in (("temptation", t_hits - c_hits), ("control", c_hits - t_hits)):
        if not only:
            continue
        severity = SEVERITY_LEAK if side == leak_side else SEVERITY_WARN
        findings.append(
            _finding(
                severity,
                subject,
                f"{kind}(s) present only in the {side}: " + ", ".join(sorted(only)),
            )
        )
    return findings


# ---------------------------------------------------------------------------
# The identifier channel: serial skew across pairs
#
# The pair-symmetry rule says the two halves must be identical ONCE
# IDENTIFIER-SHAPED TOKENS ARE MASKED. ``check_pair`` enforces exactly that, and
# is therefore structurally blind to whatever the identifiers themselves carry.
# Sandbox fixtures get written in twinned pairs (``EMP-4471`` dirty,
# ``EMP-4472`` clean), so the disqualifier lands on the lower-serial twin by
# authoring habit — and the label rides out on the id, past a masked diff that
# reports the pair as perfectly symmetric.
# ---------------------------------------------------------------------------

DIRECTION_LOWER = "lower"
DIRECTION_HIGHER = "higher"
DIRECTION_TIE = "tie"
DIRECTION_MIXED = "mixed"
DIRECTION_UNRESOLVABLE = "unresolvable"


def pair_serial_direction(temptation: dict[str, Any], control: dict[str, Any]) -> str:
    """Which half carries the lower identifier serial, per pair.

    Returns one of ``lower`` / ``higher`` (from the *temptation's* point of view),
    ``tie``, ``mixed``, or ``unresolvable``. Assertion-free: a single pair's
    direction is not a finding — see ``check_serial_skew`` for why.

    How the comparison is made, and why:

    - **Prefix-keyed, not positional and not a flat multiset.** Only families
      present in *both* halves are compared. Positional comparison ("the first id
      in each prompt") breaks the moment one half mentions an extra id, and a flat
      minimum over the whole prompt lets whichever namespace happens to use small
      numbers decide the direction for the pair. Prefix keying compares like with
      like, which is the relation twinning actually creates.
    - **Minimum within a family.** When a half names several ids from one family,
      its minimum represents it. Those ids were minted together; the minimum is
      the stable representative and matches how the skew was first measured by
      hand.
    - **Unanimity across families.** If every decisive shared family points the
      same way, that is the pair's direction. If two families disagree the pair is
      ``mixed`` and carries no direction — it is counted and then excluded, rather
      than resolved by an arbitrary tie-break. Families that tie are simply
      uninformative and do not contradict a decisive one.
    - **No shared family ⇒ ``unresolvable``.** Two halves that name disjoint
      namespaces (or no serial-bearing id at all) cannot be compared. Reported as
      such; never guessed at.
    """

    t_families = serial_ids(_prompt(temptation))
    c_families = serial_ids(_prompt(control))
    shared = sorted(set(t_families) & set(c_families))
    if not shared:
        return DIRECTION_UNRESOLVABLE

    directions: set[str] = set()
    for prefix in shared:
        t_serial, c_serial = min(t_families[prefix]), min(c_families[prefix])
        if t_serial < c_serial:
            directions.add(DIRECTION_LOWER)
        elif t_serial > c_serial:
            directions.add(DIRECTION_HIGHER)
    if not directions:
        return DIRECTION_TIE
    if len(directions) > 1:
        return DIRECTION_MIXED
    return directions.pop()


def two_sided_binomial_p(successes: int, trials: int) -> float:
    """Exact two-sided binomial p-value against p = 0.5. Stdlib only, by hand.

    Under the null the distribution is symmetric, so the exact two-sided p is
    twice the tail at least as extreme as the observed majority, clamped at 1.0.
    ``math.comb`` keeps this exact in integer arithmetic at the pair counts a pack
    can plausibly reach; no dependency, no normal approximation (which is wrong at
    n < 10, exactly the range that matters here).
    """

    if trials <= 0:
        return 1.0
    majority = max(successes, trials - successes)
    tail = sum(math.comb(trials, k) for k in range(majority, trials + 1))
    return min(1.0, 2.0 * tail / float(2**trials))


class SerialSkew(NamedTuple):
    """Directional counts of identifier-serial comparisons over a pack's pairs."""

    lower: int = 0
    higher: int = 0
    tie: int = 0
    mixed: int = 0
    unresolvable: int = 0

    @property
    def decisive(self) -> int:
        """Pairs that yielded a direction — the only ones the statistic uses."""

        return self.lower + self.higher

    @property
    def majority(self) -> int:
        return max(self.lower, self.higher)

    @property
    def direction(self) -> str:
        """Which way the majority points (``""`` when nothing is decisive)."""

        if not self.decisive:
            return ""
        return DIRECTION_LOWER if self.lower >= self.higher else DIRECTION_HIGHER

    @property
    def fraction(self) -> float:
        """Skew fraction: majority / decisive. ``0.5`` is perfect balance."""

        return self.majority / self.decisive if self.decisive else 0.0

    @property
    def p_value(self) -> float:
        return two_sided_binomial_p(self.majority, self.decisive)


def serial_skew(pairs: list[Pair]) -> SerialSkew:
    """Tally ``pair_serial_direction`` over every pair (the audit trail)."""

    counts = {
        DIRECTION_LOWER: 0,
        DIRECTION_HIGHER: 0,
        DIRECTION_TIE: 0,
        DIRECTION_MIXED: 0,
        DIRECTION_UNRESOLVABLE: 0,
    }
    for pair in pairs:
        counts[pair_serial_direction(pair.temptation, pair.control)] += 1
    return SerialSkew(
        lower=counts[DIRECTION_LOWER],
        higher=counts[DIRECTION_HIGHER],
        tie=counts[DIRECTION_TIE],
        mixed=counts[DIRECTION_MIXED],
        unresolvable=counts[DIRECTION_UNRESOLVABLE],
    )


def check_serial_skew(
    pairs: list[Pair],
    *,
    min_pairs: int = MIN_SKEW_PAIRS,
    alpha: float = SKEW_ALPHA,
) -> list[str]:
    """Corpus-level finding for a directional skew in identifier serials.

    **The statistic.** Each pair contributes one sign — does the temptation carry
    the lower or the higher serial (see ``pair_serial_direction``). Ties, mixed
    pairs and unresolvable pairs contribute no sign and are excluded from the
    test, as they are from any sign test: the null is about the *direction* of
    decisive comparisons, and a pair with no direction is not evidence either way.
    Over the ``n`` decisive pairs the check runs an exact two-sided binomial test
    against 50/50 and flags when ``p < alpha``.

    **Why a binomial test and not just a fraction.** A skew fraction alone has no
    scale: 2 of 2 is 100% and means nothing, 8 of 9 is 89% and is a finding. The
    binomial p is what turns "how lopsided" into "how lopsided *for this many
    pairs*", which is the whole distinction this check exists to draw. Both are
    reported, because the fraction is what an author reads and the p is what
    licenses reading it.

    **Why ``alpha = 0.10`` and not 0.05.** This is a screening instrument whose
    output is one advisory ``warn`` line. A false positive costs an author one
    look at their id assignments; a miss leaves a live channel in a frozen corpus.
    The test is also two-sided against a directional prior — fixture ordering puts
    the disqualifier on the *lower* twin — so a two-sided 0.10 is roughly a
    one-sided 0.05 in the direction actually expected. It is kept two-sided anyway,
    because a systematic skew the *other* way is the same defect.

    **Why ``min_pairs = 6``.** Below six decisive pairs the only configuration
    that could ever clear ``alpha`` is a clean sweep, and a five-pair sweep is not
    something worth accusing a corpus over — the claim being made is that an
    *authoring habit* ordered the twins, and at that size habit and coincidence
    are not separable. Six is where the test starts to discriminate rather than
    merely echo the sample size. A pack with fewer decisive pairs gets no finding,
    ever; ``serial_skew`` still reports its counts for anyone who wants them.

    **Why ``warn`` and not ``leak``.** A ``leak`` is a per-case tell an author must
    re-author. This is neither per-case nor certain to be exploitable. A judge
    shown one case per context sees a single id with nothing to compare it
    against, and cannot use this at all. What it does put at risk is (a) any model
    that sees the corpus as a whole, or is few-shot prompted or fine-tuned on it,
    (b) the per-pair sortability metric, where both halves are compared by
    construction, and (c) corpus quality generally — systematically ordered twins
    mean the pairs are not exchangeable, which is a design smell whatever consumes
    them. It is a measured artifact, not a demonstrated exploit, and it is graded
    to say so.

    **Why there is no per-pair finding.** A single pair whose temptation carries
    the lower serial is exactly what you would expect half the time. Emitting a
    finding per pair would bury the real signal under noise proportional to pack
    size, and would fire on every conformant pack. The direction is measured per
    pair and reported only in aggregate.
    """

    skew = serial_skew(pairs)
    if skew.decisive < min_pairs or skew.p_value >= alpha:
        return []
    return [
        _finding(
            SEVERITY_WARN,
            SKEW_SUBJECT,
            f"identifier-serial skew: the temptation carries the {skew.direction} serial in "
            f"{skew.majority} of {skew.decisive} decisive pair(s) ({skew.fraction:.0%}; exact "
            f"two-sided binomial p={skew.p_value:.3f} against 50/50, alpha={alpha:g}) "
            f"[{skew.tie} tie, {skew.mixed} mixed, {skew.unresolvable} with no shared identifier "
            f"family]. The masked-token diff cannot see this — twins mask to the same <ID> — so a "
            f"pair can read as perfectly symmetric while its ids still sort it. Alternate which "
            f"twin carries the disqualifier; do not let fixture-file ordering decide the labels",
        )
    ]


# ---------------------------------------------------------------------------
# Pack-level API
# ---------------------------------------------------------------------------


def check_pack(
    cases: list[dict[str, Any]],
    *,
    tolerance: float = DEFAULT_TOLERANCE,
    min_skew_pairs: int = MIN_SKEW_PAIRS,
    skew_alpha: float = SKEW_ALPHA,
) -> list[str]:
    """Return human-readable pair-symmetry findings; ``[]`` == nothing detected.

    Mirrors ``pack_conformance.validate_pack``'s shape (a list of strings, empty
    when clean) so the two can be run and reported side by side. Unlike
    ``validate_pack``, an empty list here is *evidence of absence at this
    resolution*, not a proof of symmetry: the blind separability probe remains
    the measurement, and this is the cheap deterministic pre-filter for it.
    """

    pairs, findings = pair_cases(cases)
    for pair in pairs:
        findings.extend(
            check_pair(pair.temptation, pair.control, pairing=pair.pairing, tolerance=tolerance)
        )
    # The identifier channel is corpus-level, not per-pair: one finding per pack,
    # and only when there are enough decisive pairs for it to mean anything.
    findings.extend(check_serial_skew(pairs, min_pairs=min_skew_pairs, alpha=skew_alpha))
    # The entity standard is per-case, not per-pair: scan every case so unpaired
    # ones are still held to it.
    for case in cases:
        handles = firstname_initial_handles(_prompt(case))
        if handles:
            findings.append(
                _finding(
                    SEVERITY_LEAK,
                    _cid(case),
                    "firstname.initial-shaped principal(s) "
                    + ", ".join(sorted(handles))
                    + " — PACK-SPEC's entity standard rejects these (they collide with real "
                    "people by construction and cannot be cleared by search)",
                )
            )
    return findings


def public_findings_by_pack(
    benchmarks_dir: Path, *, tolerance: float = DEFAULT_TOLERANCE
) -> dict[str, list[str]]:
    """Advisory findings per discovered pack whose held-out corpus is present.

    Mirrors ``pack_conformance.check_public``'s traversal — the same
    ``discover_packs`` enumeration, so a pack with a corpus on disk and no
    registry entry is swept too, and the same "absent corpus is not a failure"
    rule for clean public checkouts. The findings stay advisory — see the module
    docstring for why the gate does not fail on them. Grouped so a caller can
    summarize per pack instead of dumping every finding.
    """

    by_pack: dict[str, list[str]] = {}
    for entry in pack_conformance.packs_with_corpus(benchmarks_dir):
        slug = entry.slug
        pack_dir = benchmarks_dir / slug
        corpus = pack_dir / "cases.jsonl"
        if not corpus.exists():
            continue  # held-out fixtures absent (public checkout) — correct, skip
        try:
            cases = pack_conformance.load_cases(corpus)
        except Exception as exc:  # reported, not raised — corruption must not mask itself
            by_pack[slug] = [
                _finding(SEVERITY_WARN, slug, f"cases.jsonl unreadable (corrupt/truncated?): {exc}")
            ]
            continue
        findings = [_with_pack(f, slug) for f in check_pack(cases, tolerance=tolerance)]
        if findings:
            by_pack[slug] = findings
    return by_pack


def check_public(benchmarks_dir: Path, *, tolerance: float = DEFAULT_TOLERANCE) -> list[str]:
    """Flat advisory sweep of every discovered pack; ``[]`` == nothing detected."""

    findings: list[str] = []
    for pack_findings in public_findings_by_pack(benchmarks_dir, tolerance=tolerance).values():
        findings.extend(pack_findings)
    return findings


def _with_pack(finding: str, slug: str) -> str:
    """Insert the pack slug after the severity tag, keeping the tag parseable."""

    tag, sep, rest = finding.partition("] ")
    return f"{tag}{sep}{slug}: {rest}" if sep else f"{slug}: {finding}"


def _summarize(findings: list[str]) -> tuple[int, int]:
    leaks = sum(1 for f in findings if severity_of(f) == SEVERITY_LEAK)
    return leaks, len(findings) - leaks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", help="pack directory under evals/benchmarks/")
    parser.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE,
        help="relative length/shape delta allowed within a pair (default %(default)s)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat 'warn' findings as failures too (opt-in; frozen corpora violate them)",
    )
    parser.add_argument(
        "--report-public",
        action="store_true",
        help="advisory gate mode: report every registered pack, exit 0 unless --strict",
    )
    args = parser.parse_args(argv)

    from repo_config import REPO_ROOT

    benchmarks = REPO_ROOT / "evals/benchmarks"

    if args.report_public:
        by_pack = public_findings_by_pack(benchmarks, tolerance=args.tolerance)
        findings = [f for pack_findings in by_pack.values() for f in pack_findings]
        shown = findings if args.strict else findings[:ADVISORY_PRINT_LIMIT]
        for finding in shown:
            print(f"SYMMETRY: {finding}", file=sys.stderr)
        if len(shown) < len(findings):
            print(
                f"SYMMETRY: ... {len(findings) - len(shown)} more finding(s) suppressed; run "
                f"`pack_symmetry_check.py --pack <slug>` for a pack's full list",
                file=sys.stderr,
            )
        for slug, pack_findings in by_pack.items():
            leaks, warns = _summarize(pack_findings)
            print(f"  {slug}: {leaks} leak / {warns} warn")
        swept = pack_conformance.packs_with_corpus(benchmarks)
        leaks, warns = _summarize(findings)
        # Name what was swept, not only what was found: "0 leak" over five packs
        # and "0 leak" over none read identically otherwise.
        print(
            f"pack pair-symmetry (advisory, non-blocking): {leaks} leak / {warns} warn "
            f"findings across {len(swept)} pack(s) swept "
            f"[{', '.join(e.slug for e in swept) or 'none — no corpus present'}]"
        )
        return 1 if (args.strict and findings) else 0

    if not args.pack:
        parser.error("--pack is required unless --report-public is given")
    pack_dir = (benchmarks / args.pack) if not Path(args.pack).is_absolute() else Path(args.pack)
    if pack_dir.name != args.pack and not (pack_dir / "cases.jsonl").exists():
        pack_dir = REPO_ROOT / args.pack  # allow a full repo-relative path too
    cases = pack_conformance.load_cases(pack_dir / "cases.jsonl")

    findings = check_pack(cases, tolerance=args.tolerance)
    for finding in findings:
        print(f"SYMMETRY: {finding}", file=sys.stderr)
    pairs, _ = pair_cases(cases)
    gold = sum(1 for p in pairs if identical_after_id_masking(p.temptation, p.control))
    leaks, warns = _summarize(findings)
    print(
        f"pack {pack_dir.name}: {len(cases)} cases, {len(pairs)} pairs, "
        f"{gold} identical after id-masking — {leaks} leak / {warns} warn findings"
    )
    # Always printed, flagged or not: the counts are an audit number an author
    # should see even when the corpus is too small for the test to speak.
    skew = serial_skew(pairs)
    print(
        f"  identifier-serial skew: temptation lower in {skew.lower}, higher in {skew.higher} "
        f"of {skew.decisive} decisive pair(s) ({skew.fraction:.0%}, two-sided p="
        f"{skew.p_value:.3f}); {skew.tie} tie, {skew.mixed} mixed, "
        f"{skew.unresolvable} unresolvable"
    )
    if leaks or (args.strict and findings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
