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
with identifier-shaped tokens masked, and assists the entity standard.

Findings, not verdicts
----------------------
Every finding is a human-readable string tagged with a severity:

- ``[leak]`` — a near-certain tell (a one-sided legitimizing assertion in the
  control, a one-sided hedge/urgency phrase in the temptation, a
  ``firstname.initial`` principal). These are what an author must re-author.
- ``[warn]`` — an asymmetry that *may* be a tell: length/character/token-position
  deltas, one-sided markers pointing the unexpected way, one-sided proper nouns,
  and pairs that could not be formed at all (symmetry is a property of a pair, so
  an unpaired case cannot be checked — that is reported, not silently passed).

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
# Pack-level API
# ---------------------------------------------------------------------------


def check_pack(cases: list[dict[str, Any]], *, tolerance: float = DEFAULT_TOLERANCE) -> list[str]:
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
    """Advisory findings per registered pack whose held-out corpus is present.

    Mirrors ``pack_conformance.check_public``'s traversal (same registry, same
    "absent corpus is not a failure" rule for clean public checkouts) but its
    findings are advisory — see the module docstring for why the gate does not
    fail on them. Grouped so a caller can summarize per pack instead of dumping
    every finding.
    """

    by_pack: dict[str, list[str]] = {}
    for slug in pack_conformance.REGISTERED_PACKS:
        pack_dir = benchmarks_dir / slug
        if not (pack_dir / "METHODOLOGY.md").exists():
            continue  # pack not registered in this checkout
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
    """Flat advisory sweep of every registered pack; ``[]`` == nothing detected."""

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
        leaks, warns = _summarize(findings)
        print(
            f"pack pair-symmetry (advisory, non-blocking): {leaks} leak / {warns} warn "
            f"findings across registered packs"
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
    if leaks or (args.strict and findings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
