"""Deterministic corpus-identifier leak checker for vertical red-team packs.

The discipline this enforces is the one PACK-SPEC states in five words:

    A published eval set is a burned eval set.

Held-out scenarios, sandboxes and manifests are gitignored so that a model under
test cannot pass by recall. That protection is only as strong as its weakest
literal: an identifier that appears **verbatim** in a held-out ``user_prompt``
*and* in a git-tracked file is a public anchor into the private corpus. Whatever
the tracked file says next to that token — the scenario's shape, the deciding
state, the correct disposition — is now attached to a string the model will meet
again at test time.

Found 2026-08-06 by a blind reviewer on ``hr_payroll`` and then measured across
every pack. Twenty-eight identifiers were live in tracked files: worked examples
in two pack charters, illustrations in the finance taxonomy and run protocol, and
docstring/test fixtures in the tooling itself. The markdown half was what the
reviewer saw; the tooling half is why this check reads **every** tracked file and
not only ``*.md``.

What this check is, precisely
-----------------------------
For every pack whose held-out ``cases.jsonl`` is present locally, extract the
identifier-shaped tokens from each case's ``user_prompt``, then report any of
them that also occurs in a git-tracked file.

Three scoping decisions, each load-bearing:

- **Prompts only, not the whole case record.** The ``user_prompt`` is the text
  the model under test actually reads, so it is the only place a token can become
  a memorised anchor. ``expected_behavior`` and ``scoring_notes`` are held out
  too, but they are written *in* the shared public vocabulary — tool names,
  ``breach=none``, signal names — and scanning them would flag the vocabulary the
  spec deliberately publishes.
- **Every tracked file, not only markdown.** Nine of the twenty-eight collisions
  were in ``src/`` and ``tests/``. A docstring is as public as a charter.
- **Tracked, not "published".** ``git ls-files`` is the exact boundary the
  gitignore rules draw. If a held-out file is ever accidentally tracked, its own
  identifiers collide with themselves and this check goes loudly red — which is
  the correct alarm, not a false positive to suppress.

The false-positive rule
-----------------------
A token is reported iff it is **identifier-shaped** (see ``IDENTIFIER_RE``): a
hyphen-segmented alphanumeric token, at least ``MIN_IDENTIFIER_LEN`` characters
long, carrying at least one digit. That shape is what a fixture id looks like
(``XEMP-4471``, ``XCTRL-AML-07``, ``XHOLD-LIT-51``) and what ordinary prose does not.

There is deliberately **no semantic exemption**, and that is the whole design.
The tempting exemption is "this token is generic domain vocabulary" — ``XGL-1010``
really could be a chart-of-accounts code in a taxonomy table, and ``XCTRL-AML-07``
really could name a control in the abstract. But "it reads as generic" is exactly
the judgment that produced this breach: every one of the twenty-eight tokens
looked generic to whoever typed it, and each was in fact the literal an agent
would meet at test time. A check that can be argued out of a finding is a check
that will be. So the rule is structural, the finding is a fact ("this token is in
both"), and a human decides the remedy — re-identify the corpus, or re-illustrate
the doc.

What *is* excluded is exclusion by construction rather than by judgment:

- **The taxonomy and policy vocabulary** (``AGB-*`` failure modes, ``ABP-*``
  policy refs) and **case ids** are published on purpose; PACK-SPEC puts them in
  the public column. They are excluded via ``PUBLISHED_ID_PREFIXES`` and by
  skipping any token that is a ``case_id`` in the same corpus. In practice no
  corpus puts one in a prompt, so the exclusion is a guard, not a workaround.
- **The reserved illustration band** (``RESERVED_ILLUSTRATION_RE``): a serial
  whose LEADING SEGMENT begins with ``X`` — ``XEMP-4471``, ``XHOLD-LIT-51``.
  Public docs write their
  worked examples in this band so the example keeps its teaching value while
  being structurally incapable of naming a fixture. A corpus prompt that uses the
  band is itself a finding, because it has taken an identifier the docs are
  entitled to print.

Blocking, not advisory
----------------------
``pack_symmetry_check`` and ``pack_reachability_check`` are advisory for one
specific reason: the corpora they judge were frozen *before* those rules existed,
and a frozen corpus's only legal fix is a version bump — so failing the gate
would block everyone while forbidding the remedy.

That reason does not transfer here. The remedy for a leak is available on **both**
sides, and one of them is always legal: a public document can be re-illustrated
at any time, frozen pack or not. Nothing about this finding is unfixable, so
nothing about it justifies being ignorable. The per-pack pre-freeze run is
BLOCKING; the shared gate runs it with ``--advisory`` only while an outstanding
leak awaits a human decision, and the summary line always names which mode it
ran in rather than asserting one.

Absence is reported, never silently green
-----------------------------------------
A clean public checkout has no ``cases.jsonl`` anywhere. This check must be green
*and quiet* there — but "green because there was nothing to look at" and "green
because everything was looked at and was clean" are different results, and an
instrument that renders them identically is the defect this repo keeps finding in
other people's instruments. So the summary always names the traversal (packs
swept, prompts read, identifiers extracted, tracked files scanned), and the two
ways the instrument can be blind are reported explicitly:

- **no corpus present** → ``SKIPPED`` for that pack; the summary says so;
- **not a git checkout** (``git ls-files`` unavailable) → the whole check is
  ``SKIPPED`` with a visible notice, because the tracked-file side does not exist
  and a comparison against an empty set would pass vacuously.

Coverage is asserted *relatively*, never as an absolute floor: a pack whose
corpus is present must yield at least one scanned prompt, and the tracked-file
side must be non-empty. Asserting absolute counts ("at least N identifiers")
would fail a clean clone, which is the mistake this module is written not to
repeat.

Deterministic, offline, stdlib-only. No model calls. Never touches
``src/scorers.py``.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, NamedTuple

import pack_conformance

SEVERITY_LEAK = "leak"
SEVERITY_NOTICE = "notice"

# An identifier-shaped token: hyphen-segmented alphanumerics carrying a digit.
# ``XEMP-4471``, ``XCTRL-AML-07``, ``XACCTREF-Z1A0``, ``XHOLD-LIT-51`` all match;
# ordinary hyphenated prose ("pre-approved", "out-of-band") does not, because it
# has no digit, and "v2.7.1" does not, because it has no hyphen segmentation.
IDENTIFIER_RE = re.compile(r"^(?=.*\d)[A-Za-z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)+$")

# Below this length a token is too generic to be a useful anchor and too likely
# to collide with something structural ("A-1", "T-2"). Four characters is the
# shortest a real fixture id in these corpora gets.
MIN_IDENTIFIER_LEN = 4

# Namespaces PACK-SPEC publishes on purpose: the failure taxonomy and the policy
# vocabulary. "The vocabulary is more useful shared than hoarded" — every pack's
# HELD-OUT.md says so. A prompt that cites one is citing public vocabulary.
PUBLISHED_ID_PREFIXES: tuple[str, ...] = ("AGB-", "ABP-")

# The reserved illustration namespace: an identifier whose LEADING segment begins
# with ``X`` — ``XEMP-4471``, ``XHOLD-LIT-51``, ``XCTRL-AML-07``. Public docs,
# docstrings and test fixtures write their worked examples here, so an example can
# stay concrete and domain-shaped while being structurally incapable of naming a
# real fixture.
#
# Why the *prefix* and not the serial. Marking the serial instead (``EMP-X471``)
# reads slightly better, but it destroys the serial: ``pack_symmetry_check`` parses
# ``<PREFIX>-<numeric serial>`` and its own docstrings must demonstrate that
# parsing. A reserved prefix leaves the numeric serial intact, so every example in
# the repo can use one rule. No corpus and no sandbox uses an ``X``-initial prefix
# (verified 2026-08-06), and a prompt that starts using one is itself reported —
# it has taken an identifier the docs are entitled to print.
RESERVED_ILLUSTRATION_RE = re.compile(r"^X[A-Za-z0-9]*-")

# Tokenizer for both sides. Deliberately permissive at the edges and trimmed
# after, so "EMP-4471." and "(BCR-8801)" both yield the bare identifier.
_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.@/'-]*")
_TOKEN_TRIM = ".,;:!?'\"/-_"

# Tracked files that are not text are skipped rather than decoded; a binary blob
# cannot carry a readable anchor.
_BINARY_SUFFIXES = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".gz", ".ico", ".woff", ".woff2", ".pyc"}
)


def _finding(severity: str, subject: str, message: str) -> str:
    return f"[{severity}] {subject}: {message}"


def severity_of(finding: str) -> str:
    """The severity tag a finding carries (``""`` when it carries none)."""

    for severity in (SEVERITY_LEAK, SEVERITY_NOTICE):
        if finding.startswith(f"[{severity}]"):
            return severity
    return ""


def has_leaks(findings: Iterable[str]) -> bool:
    return any(severity_of(f) == SEVERITY_LEAK for f in findings)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def is_identifier(token: str) -> bool:
    """Is ``token`` identifier-shaped enough to be a memorisable corpus anchor?"""

    return len(token) >= MIN_IDENTIFIER_LEN and bool(IDENTIFIER_RE.match(token))


def is_published_vocabulary(token: str) -> bool:
    """Does ``token`` belong to a namespace PACK-SPEC publishes deliberately?"""

    upper = token.upper()
    return any(upper.startswith(prefix) for prefix in PUBLISHED_ID_PREFIXES)


def is_reserved_illustration(token: str) -> bool:
    """Is ``token`` in the doc-only illustration band (``XEMP-4471``)?"""

    return bool(RESERVED_ILLUSTRATION_RE.search(token))


def identifiers_in(text: str) -> set[str]:
    """Identifier-shaped tokens in ``text``, published vocabulary removed."""

    found: set[str] = set()
    for raw in _TOKEN_RE.findall(text or ""):
        token = raw.strip(_TOKEN_TRIM)
        if is_identifier(token) and not is_published_vocabulary(token):
            found.add(token)
    return found


class CorpusScan(NamedTuple):
    """What one pack's held-out corpus contributed to the sweep."""

    slug: str
    prompts: int
    #: identifier -> sorted case ids whose prompt uses it
    identifiers: dict[str, list[str]]
    #: identifiers in the reserved doc-only band (a defect on the corpus side)
    reserved_used: dict[str, list[str]]


def scan_corpus(slug: str, cases: list[dict[str, Any]]) -> CorpusScan:
    """Extract prompt identifiers for one pack, keeping the case ids that used them.

    ``case_id`` values are excluded: they are published in reports and protocols
    by design, so a prompt that happens to quote its own id is not a leak.
    """

    case_ids = {str(c.get("case_id")) for c in cases if c.get("case_id")}
    identifiers: dict[str, list[str]] = {}
    reserved: dict[str, list[str]] = {}
    prompts = 0
    for case in cases:
        prompt = str(case.get("user_prompt") or "")
        if not prompt.strip():
            continue
        prompts += 1
        cid = str(case.get("case_id") or "<no-id>")
        for token in identifiers_in(prompt):
            if token in case_ids:
                continue
            bucket = reserved if is_reserved_illustration(token) else identifiers
            bucket.setdefault(token, []).append(cid)
    for bucket in (identifiers, reserved):
        for cids in bucket.values():
            cids.sort()
    return CorpusScan(slug, prompts, identifiers, reserved)


# ---------------------------------------------------------------------------
# The tracked-file side
# ---------------------------------------------------------------------------


class TrackedCorpusUnavailable(RuntimeError):
    """``git ls-files`` could not enumerate the tracked set (not a git checkout)."""


def tracked_files(repo_root: Path) -> list[Path]:
    """Every git-tracked file that exists on disk.

    Raises ``TrackedCorpusUnavailable`` when git cannot answer. That is a *skip*,
    never a pass: with no tracked set there is nothing to compare against, and a
    comparison against nothing is vacuously clean.
    """

    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=repo_root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise TrackedCorpusUnavailable(str(exc)) from exc
    paths = [repo_root / name for name in completed.stdout.split("\0") if name]
    found = [p for p in paths if p.is_file() and p.suffix.lower() not in _BINARY_SUFFIXES]
    if not found:
        raise TrackedCorpusUnavailable("git ls-files returned no readable tracked files")
    return found


def find_tokens(paths: Iterable[Path], tokens: Iterable[str]) -> dict[str, set[Path]]:
    """Which of ``tokens`` occur in which of ``paths``.

    One compiled alternation, one pass per file. Longest-first so ``XHOLD-LIT-51``
    wins over any shorter token that prefixes it.

    **The boundary is alphanumeric, not hyphen-inclusive**, and that choice is
    load-bearing. ``XGL-1010`` must not match inside ``XGL-10105`` — a different
    account — so a trailing digit or letter blocks the match. But it *must* match
    inside ``AUD-XGL-1010``, the audit trail *for* that account, which is how the
    finance taxonomy published the ledger id while a hyphen-inclusive boundary
    read it as an unrelated token and missed it. Compositional identifiers share
    their tail on purpose in these corpora; a boundary that hides the shared part
    hides the leak.
    """

    ordered = sorted({t for t in tokens}, key=len, reverse=True)
    if not ordered:
        return {}
    pattern = re.compile(
        r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(t) for t in ordered) + r")(?![A-Za-z0-9])"
    )
    hits: dict[str, set[Path]] = {}
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in set(pattern.findall(text)):
            hits.setdefault(match, set()).add(path)
    return hits


# ---------------------------------------------------------------------------
# The sweep
# ---------------------------------------------------------------------------


class Sweep(NamedTuple):
    """The full result, findings plus the coverage numbers that license them."""

    findings: list[str]
    scans: list[CorpusScan]
    #: packs discovered whose corpus is absent (clean public checkout)
    skipped: list[str]
    tracked_scanned: int
    #: True when the tracked side could not be enumerated at all
    tracked_unavailable: bool

    @property
    def identifiers_checked(self) -> int:
        return sum(len(s.identifiers) + len(s.reserved_used) for s in self.scans)

    @property
    def prompts_scanned(self) -> int:
        return sum(s.prompts for s in self.scans)

    @property
    def leaks(self) -> int:
        return sum(1 for f in self.findings if severity_of(f) == SEVERITY_LEAK)

    @property
    def notices(self) -> int:
        return sum(1 for f in self.findings if severity_of(f) == SEVERITY_NOTICE)


def _relative(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def sweep(repo_root: Path, benchmarks_dir: Path | None = None) -> Sweep:
    """Run the full check: every discovered pack's prompts vs every tracked file."""

    benchmarks = benchmarks_dir if benchmarks_dir is not None else repo_root / "evals/benchmarks"
    findings: list[str] = []
    scans: list[CorpusScan] = []
    skipped: list[str] = []

    for entry in pack_conformance.discover_packs(benchmarks):
        corpus = benchmarks / entry.slug / "cases.jsonl"
        if not corpus.is_file():
            skipped.append(entry.slug)  # held out and absent — a clean public checkout
            continue
        try:
            cases = pack_conformance.load_cases(corpus)
        except Exception as exc:  # reported, not raised — corruption must not mask itself
            findings.append(
                _finding(SEVERITY_LEAK, entry.slug, f"cases.jsonl unreadable (corrupt/truncated?): {exc}")
            )
            continue
        scan = scan_corpus(entry.slug, cases)
        scans.append(scan)
        # Relative coverage assertion: a corpus that is present must have yielded
        # prompts. Zero means the instrument read nothing and would pass vacuously.
        if cases and scan.prompts == 0:
            findings.append(
                _finding(
                    SEVERITY_LEAK,
                    entry.slug,
                    f"corpus has {len(cases)} case(s) but not one non-empty user_prompt — nothing "
                    f"was scanned, so a green result here would mean nothing",
                )
            )

    try:
        paths = tracked_files(repo_root)
    except TrackedCorpusUnavailable as exc:
        return Sweep(
            findings
            + [
                _finding(
                    SEVERITY_NOTICE,
                    "instrument",
                    f"tracked-file set unavailable ({exc}) — this check is SKIPPED, not passed. "
                    f"It compares held-out prompt identifiers against git-tracked files; with no "
                    f"tracked set there is nothing to compare against",
                )
            ],
            scans,
            skipped,
            0,
            True,
        )

    wanted: dict[str, list[tuple[str, list[str]]]] = {}
    for scan in scans:
        for token, cids in scan.identifiers.items():
            wanted.setdefault(token, []).append((scan.slug, cids))
        for token, cids in scan.reserved_used.items():
            wanted.setdefault(token, []).append((scan.slug, cids))

    hits = find_tokens(paths, wanted)
    for token in sorted(hits):
        owners = wanted[token]
        where = ", ".join(sorted(_relative(p, repo_root) for p in hits[token]))
        origin = "; ".join(f"{slug} {', '.join(cids)}" for slug, cids in sorted(owners))
        if is_reserved_illustration(token):
            findings.append(
                _finding(
                    SEVERITY_LEAK,
                    token,
                    f"held-out prompt uses the reserved illustration band ({origin}) and the token "
                    f"is tracked in {where}. The 'X'-prefix band is reserved for public worked "
                    f"examples — re-identify the CORPUS, not the doc",
                )
            )
            continue
        findings.append(
            _finding(
                SEVERITY_LEAK,
                token,
                f"held-out prompt identifier ({origin}) appears verbatim in tracked file(s): "
                f"{where}. A published anchor into a held-out corpus — re-illustrate the tracked "
                f"file with a reserved 'X'-prefixed identifier, or re-identify the corpus if the "
                f"tracked text gives away the disposition",
            )
        )

    for scan in scans:
        for token, cids in sorted(scan.reserved_used.items()):
            if token in hits:
                continue  # already reported above, with its tracked locations
            findings.append(
                _finding(
                    SEVERITY_NOTICE,
                    scan.slug,
                    f"{token} ({', '.join(cids)}) sits in the reserved 'X'-prefix illustration "
                    f"band that public docs are entitled to print — re-identify it before some "
                    f"future worked example collides with it",
                )
            )

    return Sweep(findings, scans, skipped, len(paths), False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_summary(result: Sweep, mode: str = "BLOCKING") -> None:
    """``mode`` names the exit behaviour this run actually used, so the summary
    cannot claim to be blocking while the gate is ignoring its exit code."""

    swept = ", ".join(s.slug for s in result.scans) or "none — no held-out corpus present"
    if result.tracked_unavailable:
        print(
            f"pack identifier leak ({mode}): SKIPPED — not a git checkout, so the tracked-file "
            f"side could not be enumerated [{len(result.scans)} pack(s) with a corpus: {swept}]"
        )
        return
    print(
        f"pack identifier leak ({mode}): {result.leaks} leak / {result.notices} notice across "
        f"{len(result.scans)} pack(s) swept [{swept}]; "
        f"{result.prompts_scanned} prompt(s), {result.identifiers_checked} distinct identifier(s) "
        f"checked against {result.tracked_scanned} tracked file(s)"
    )
    if result.skipped:
        print(
            f"  corpus absent (held out — not checked): {', '.join(sorted(result.skipped))}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report-public",
        action="store_true",
        help="gate mode: sweep every discovered pack and exit non-zero on any leak",
    )
    parser.add_argument("--pack", help="restrict the sweep to one pack slug")
    parser.add_argument("--json", action="store_true", help="emit the sweep as JSON")
    parser.add_argument(
        "--advisory",
        action="store_true",
        help=(
            "report findings but always exit 0. For the shared gate while an "
            "outstanding leak awaits a human decision whose only fixes are "
            "editing published evidence or retiring a frozen case. Per-pack "
            "pre-freeze runs omit this and are blocking."
        ),
    )
    args = parser.parse_args(argv)

    from repo_config import REPO_ROOT

    benchmarks = REPO_ROOT / "evals/benchmarks"
    result = sweep(REPO_ROOT, benchmarks)

    if args.pack:
        result = Sweep(
            [f for f in result.findings if f".{args.pack}" in f or f"] {args.pack}:" in f or args.pack in f],
            [s for s in result.scans if s.slug == args.pack],
            [s for s in result.skipped if s == args.pack],
            result.tracked_scanned,
            result.tracked_unavailable,
        )

    if args.json:
        print(
            json.dumps(
                {
                    "findings": result.findings,
                    "packs_swept": [s.slug for s in result.scans],
                    "packs_corpus_absent": sorted(result.skipped),
                    "prompts_scanned": result.prompts_scanned,
                    "identifiers_checked": result.identifiers_checked,
                    "tracked_files_scanned": result.tracked_scanned,
                    "tracked_unavailable": result.tracked_unavailable,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if args.advisory else (1 if has_leaks(result.findings) else 0)

    for finding in result.findings:
        print(f"IDENTIFIER-LEAK: {finding}", file=sys.stderr)
    _print_summary(result, "ADVISORY" if args.advisory else "BLOCKING")
    return 0 if args.advisory else (1 if has_leaks(result.findings) else 0)


if __name__ == "__main__":
    raise SystemExit(main())
