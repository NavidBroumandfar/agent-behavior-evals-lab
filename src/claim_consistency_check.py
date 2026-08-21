"""Deterministic checker for the repo contradicting itself in its own prose.

``published_number_check.py`` verifies a **hand-registered** list of numbers against
their generator artifacts. That list is only as good as the last person who
remembered to extend it, and the failures this module exists for were all outside
it. In one 24-hour audit the repository was found publicly asserting, about itself:

- "no result from these packs exists yet", while two committed result reports sat
  in the pack's own ``reports/`` directory;
- "no probe has been run against v0.6", inside the very paragraph that links the
  report publishing that probe;
- that ``devops_sre`` was the leakiest pack, while the repo's own checker said
  ``finance_redteam`` was, by 12 findings to 0;
- that ``cases.jsonl`` "does not exist yet" for a pack whose corpus is on disk.

Every one of those was **true when written** and went stale. A human re-reading
303 tracked markdown files will not catch the next one. This module applies the
lab's own governing rule — *claims are checked against recorded reality, never
against how confidently they are worded* — to the repository's own prose.

Four claim classes, each detected as a PATTERN, never as a list of known bugs
-----------------------------------------------------------------------------

a. **Existence claims.** A sentence asserting that something has *not* happened
   or does *not* exist ("no X exists yet", "has never been run", "no scenario has
   been authored"), where a matching artefact is present on disk.
b. **Pack-fact drift.** Every pack version string and case count quoted in tracked
   markdown, checked against the manifests and corpora actually on disk.
c. **Cross-file numeric contradiction.** The same named quantity given two
   different values in two tracked files.
d. **Superlative drift.** "Pack X is the worst/most/only ..." on a measure some
   checker in this repo can currently compute, checked against that checker.

Verdicts, and why there are only two
------------------------------------

- ``CONFIRMED`` — the claim and the fact cannot both be true, and the fact is
  derivable from this checkout without judgement.
- ``NEEDS_HUMAN`` — a real mismatch whose resolution is editorial: the claim is
  quoted inside its own published correction, or it sits in a dated snapshot
  (a report or a pre-registration) that is *expected* to describe its own moment.

Nothing is ever silently "fine". A claim this module cannot adjudicate is counted
and named, never dropped.

Honest degradation, which is the load-bearing part
--------------------------------------------------

Held-out pack fixtures are gitignored, so in a clean public checkout the manifests
and corpora that would adjudicate classes (b), (c) and (d) are **absent**. This
module then reports those claims as ``cannot verify`` with their file:line — it
does **not** report a pass. That distinction has already been paid for here: an
existing sandbox-contract guarantee advertised as covering "213 tools" silently
narrowed to 5 in a public checkout and kept printing a green line.

The same rule applies upward: the claim side is enumerated with ``git ls-files``,
which also guarantees this module never reads a held-out file. If git cannot
answer, the whole scan reports as unavailable rather than as clean.

Deterministic, offline, stdlib-only. No model calls. Never touches
``src/scorers.py``, no pack, and no report.

Exit codes:
    0 - no confirmed contradiction (advisory findings and cannot-verify notes printed)
    1 - at least one CONFIRMED contradiction (suppressed by ``--report-public``)
    2 - usage or input error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, NamedTuple

import pack_conformance
import pack_identifier_leak_check

REPO_ROOT = Path(__file__).resolve().parents[1]

VERDICT_CONFIRMED = "CONFIRMED"
VERDICT_NEEDS_HUMAN = "NEEDS_HUMAN"

CLASS_EXISTENCE = "existence"
CLASS_PACK_FACT = "pack-fact"
CLASS_CROSS_FILE = "cross-file"
CLASS_SUPERLATIVE = "superlative"
CLASS_INTEGRITY = "pack-integrity"


class ClaimSourceUnavailable(RuntimeError):
    """The tracked-file set could not be enumerated, so no claim could be read.

    A skip, never a pass: a scan over nothing finds nothing, and reporting that as
    "no contradictions" is the exact instrument failure this module exists to stop.
    """


# ---------------------------------------------------------------------------
# Findings and coverage
# ---------------------------------------------------------------------------


class Finding(NamedTuple):
    """One claim that contradicts a fact this checkout can derive."""

    cls: str
    verdict: str
    path: str  # repo-relative
    line: int  # 1-indexed
    claim: str  # the claim as written, truncated
    fact: str  # what the repo actually shows
    note: str = ""

    def render(self) -> str:
        tail = f" [{self.note}]" if self.note else ""
        return f"{self.path}:{self.line}: [{self.cls}] claim: {self.claim}\n    fact: {self.fact}{tail}"


class Unverifiable(NamedTuple):
    """A claim that WOULD be checkable, whose fact source is absent here."""

    cls: str
    path: str
    line: int
    claim: str
    reason: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: [{self.cls}] cannot verify: {self.claim}\n    reason: {self.reason}"


class Unadjudicated(NamedTuple):
    """A claim of a checked shape whose subject this module could not resolve."""

    cls: str
    path: str
    line: int
    claim: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: [{self.cls}] not adjudicated: {self.claim}"


class Report(NamedTuple):
    findings: tuple[Finding, ...]
    unverifiable: tuple[Unverifiable, ...]
    unadjudicated: tuple[Unadjudicated, ...]
    files_scanned: int
    units_scanned: int
    claims_seen: dict[str, int]
    facts: "Facts"

    @property
    def confirmed(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.verdict == VERDICT_CONFIRMED)

    @property
    def needs_human(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.verdict == VERDICT_NEEDS_HUMAN)

    @property
    def fully_verified(self) -> bool:
        """True only when every claim found had a fact source to check it against."""

        return not self.unverifiable


# ---------------------------------------------------------------------------
# The fact side
# ---------------------------------------------------------------------------


class PackFacts(NamedTuple):
    """What this checkout can actually say about one pack."""

    slug: str
    corpus_present: bool
    manifest_present: bool
    manifest_version: str | None
    total: int | None
    temptations: int | None
    controls: int | None
    record_versions: tuple[tuple[str, int], ...]  # sorted (version, count)
    freeze_intact: bool | None  # None == no manifest here, so nothing to verify


class Facts(NamedTuple):
    packs: dict[str, PackFacts]
    artefacts: tuple["Artefact", ...]
    symmetry: dict[str, tuple[int, int]] | None  # slug -> (leak, warn); None == unavailable
    symmetry_reason: str
    repo_root: Path
    benchmarks_dir: Path
    aliases: dict[str, str]
    alias_re: "re.Pattern[str] | None"

    def pack(self, slug: str) -> PackFacts | None:
        return self.packs.get(slug)


class Artefact(NamedTuple):
    """A committed file that is evidence something happened."""

    path: str
    slugs: frozenset[str]
    versions: frozenset[str]
    kinds: frozenset[str]


# Artefact kinds, and the words that put a file (or a claim) in one. Deliberately
# small: a kind exists only where the repo can produce evidence for it.
KIND_WORDS: dict[str, tuple[str, ...]] = {
    "run": ("run", "runs", "ran", "trajector", "driven", "drove", "executed", "rows scored"),
    "result": ("result", "report", "verdict", "score", "scored", "measurement", "measured", "number"),
    "probe": ("probe", "probed", "separab"),
    "scenario": ("scenario", "case", "cases", "corpus", "authored", "batch"),
    "freeze": ("freeze", "frozen", "manifest", "pinned"),
}

# Where committed evidence lives. Anything tracked under these roots is indexed.
ARTEFACT_ROOTS = ("reports/", "evals/benchmarks/")
ARTEFACT_SUFFIXES = (".md", ".json")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def collect_pack_facts(benchmarks_dir: Path) -> dict[str, PackFacts]:
    """Version and count facts for every pack ``discover_packs`` can see.

    Absent held-out files are recorded as absent, never as zero — a pack whose
    corpus is gitignored has an *unknown* case count, and a checker that reports
    it as 0 would clear every count claim in a public checkout.
    """

    facts: dict[str, PackFacts] = {}
    for slug in _pack_slugs(benchmarks_dir):
        pack_dir = benchmarks_dir / slug
        corpus = pack_dir / "cases.jsonl"
        manifest = pack_dir / "manifest.json"
        version = total = temptations = controls = None
        record_versions: tuple[tuple[str, int], ...] = ()
        freeze_intact: bool | None = None
        expected_hash = ""
        if manifest.is_file():
            try:
                payload = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = {}
            expected_hash = str(payload.get("corpus_sha256") or "")
            raw_version = payload.get("case_set_version")
            version = str(raw_version) if isinstance(raw_version, str) else None
            counts = payload.get("counts")
            if isinstance(counts, dict):
                total = counts.get("total") if isinstance(counts.get("total"), int) else None
                temptations = counts.get("temptation") if isinstance(counts.get("temptation"), int) else None
                controls = counts.get("honest_control") if isinstance(counts.get("honest_control"), int) else None
        if corpus.is_file():
            if expected_hash:
                freeze_intact = _sha256(corpus) == expected_hash
            cases = _load_case_headers(corpus)
            if total is None:
                total = len(cases)
            if temptations is None:
                temptations = sum(1 for c in cases if c.get("kind") == "temptation")
            if controls is None:
                controls = sum(1 for c in cases if c.get("kind") == "honest_control")
            seen: dict[str, int] = {}
            for case in cases:
                value = case.get("case_set_version")
                if isinstance(value, str):
                    seen[value] = seen.get(value, 0) + 1
            record_versions = tuple(sorted(seen.items()))
        facts[slug] = PackFacts(
            slug=slug,
            corpus_present=corpus.is_file(),
            manifest_present=manifest.is_file(),
            manifest_version=version,
            total=total,
            temptations=temptations,
            controls=controls,
            record_versions=record_versions,
            freeze_intact=freeze_intact,
        )
    return facts


def _pack_slugs(benchmarks_dir: Path) -> list[str]:
    """Every pack directory in this checkout, whether or not it has fixtures.

    ``pack_conformance.discover_packs`` deliberately stays silent about a pack
    directory that holds only public docs — for a *conformance* check that is
    right, because there is nothing to conform. Here it would be a false pass:
    the docs are exactly what this module reads claims from, and a claim about a
    pack whose manifest is absent must be reported as unverifiable, not skipped.
    So the registry and ``discover_packs`` are unioned with a plain scan for pack
    directories.
    """

    slugs: set[str] = set()
    try:
        slugs.update(e.slug for e in pack_conformance.discover_packs(benchmarks_dir))
    except Exception:  # pragma: no cover - discovery is defensive by design
        pass
    if benchmarks_dir.is_dir():
        for pack_dir in sorted(p for p in benchmarks_dir.iterdir() if p.is_dir()):
            try:
                if pack_conformance.is_pack_dir(pack_dir):
                    slugs.add(pack_dir.name)
            except Exception:  # pragma: no cover - defensive
                continue
    return sorted(slugs)


def _sha256(path: Path) -> str:
    import hashlib

    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def _load_case_headers(corpus: Path) -> list[dict[str, Any]]:
    """Read only the fields this module is allowed to know: kind and version.

    Deliberately narrow. Prompts, identifiers and scoring contracts are held-out
    content; this module never needs them and therefore never holds them.
    """

    headers: list[dict[str, Any]] = []
    try:
        lines = corpus.read_text(encoding="utf-8").splitlines()
    except OSError:
        return headers
    for line in lines:
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            headers.append({"kind": record.get("kind"), "case_set_version": record.get("case_set_version")})
    return headers


_VERSION_TOKEN = re.compile(r"\bv(\d+\.\d+)\b")


def collect_artefacts(repo_root: Path, tracked: Iterable[Path], slugs: Iterable[str]) -> tuple[Artefact, ...]:
    """Index the tracked files that are evidence something happened."""

    known = tuple(sorted(slugs, key=len, reverse=True))
    out: list[Artefact] = []
    for path in sorted(tracked):
        try:
            rel = path.relative_to(repo_root).as_posix()
        except ValueError:
            continue
        if path.suffix.lower() not in ARTEFACT_SUFFIXES:
            continue
        if not any(rel.startswith(root) for root in ARTEFACT_ROOTS):
            continue
        if "/reports/" not in f"/{rel}" and not rel.startswith("reports/"):
            continue
        text = _read_text(path)
        haystack = f"{rel}\n{text}".lower()
        found_slugs = frozenset(s for s in known if s in haystack)
        versions = frozenset(f"v{m}" for m in _VERSION_TOKEN.findall(text))
        kinds = frozenset(k for k, words in KIND_WORDS.items() if any(w in haystack for w in words))
        out.append(Artefact(path=rel, slugs=found_slugs, versions=versions, kinds=kinds))
    return tuple(out)


def collect_symmetry(
    benchmarks_dir: Path, pack_facts: dict[str, PackFacts]
) -> tuple[dict[str, tuple[int, int]] | None, str]:
    """Current ``pack_symmetry_check`` leak/warn counts per pack, or why not.

    Imported lazily: it is the only fact source here that needs the held-out
    corpora, and an import failure must degrade to "cannot verify" rather than
    take the whole check down.
    """

    try:
        import pack_symmetry_check
    except Exception as exc:  # pragma: no cover - defensive
        return None, f"pack_symmetry_check unimportable ({exc})"
    try:
        by_pack = pack_symmetry_check.public_findings_by_pack(benchmarks_dir)
        swept = [e.slug for e in pack_conformance.packs_with_corpus(benchmarks_dir)]
    except Exception as exc:  # pragma: no cover - defensive
        return None, f"pack_symmetry_check raised ({exc})"
    if not swept:
        return None, "no pack corpus is present in this checkout (held-out fixtures are gitignored)"
    # "Freeze before you score" applies to this instrument too. A ranking computed
    # over a corpus that no longer matches its own manifest hash is not a fact
    # about the frozen pack, so it must not adjudicate a claim about one.
    broken = sorted(s for s, f in pack_facts.items() if f.freeze_intact is False)
    if broken:
        return None, (
            "refusing to rank: " + ", ".join(broken) + " no longer match(es) the corpus_sha256 in "
            "its own manifest.json, so any ranking here would be measured against an unfrozen corpus"
        )
    counts: dict[str, tuple[int, int]] = {}
    for slug in swept:
        findings = by_pack.get(slug, [])
        leaks = sum(1 for f in findings if pack_symmetry_check.severity_of(f) == pack_symmetry_check.SEVERITY_LEAK)
        counts[slug] = (leaks, len(findings) - leaks)
    return counts, f"swept {len(counts)} pack(s) with a corpus on disk"


def collect_facts(repo_root: Path, tracked: Iterable[Path] | None = None) -> Facts:
    benchmarks_dir = repo_root / "evals/benchmarks"
    packs = collect_pack_facts(benchmarks_dir)
    slugs = set(packs) | set(pack_conformance.REGISTERED_PACKS)
    if tracked is None:
        tracked = tracked_markdown(repo_root)
    artefacts = collect_artefacts(repo_root, tracked, slugs)
    symmetry, reason = collect_symmetry(benchmarks_dir, packs)
    aliases = pack_aliases(packs)
    return Facts(
        packs=packs,
        artefacts=artefacts,
        symmetry=symmetry,
        symmetry_reason=reason,
        repo_root=repo_root,
        benchmarks_dir=benchmarks_dir,
        aliases=aliases,
        alias_re=alias_pattern(aliases),
    )


# ---------------------------------------------------------------------------
# The claim side: tracked markdown, split into addressable units
# ---------------------------------------------------------------------------


def tracked_markdown(repo_root: Path) -> list[Path]:
    """Every git-tracked ``.md`` file on disk.

    Tracked-ness is the right filter twice over: it is exactly the set a reader
    of the public repository sees, and it is the set that provably excludes the
    held-out fixtures (``cases.jsonl``, ``BUILD-NOTES.md``, ``manifest.json``),
    which are gitignored. This module therefore cannot read held-out prose even
    by accident.
    """

    try:
        files = pack_identifier_leak_check.tracked_files(repo_root)
    except pack_identifier_leak_check.TrackedCorpusUnavailable as exc:
        raise ClaimSourceUnavailable(str(exc)) from exc
    return sorted(p for p in files if p.suffix.lower() == ".md")


class Unit(NamedTuple):
    """One addressable piece of prose: a sentence, a table row, or a heading."""

    path: str
    line: int
    text: str
    kind: str  # "prose" | "row" | "heading"


_LIST_START = re.compile(r"^(?:[-*+]\s|\d+[.)]\s|>\s)")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")
_FENCE = re.compile(r"^\s*(?:```|~~~)")


def split_units(rel_path: str, text: str) -> list[Unit]:
    """Split a markdown document into units that each carry a real line number.

    Prose is re-joined per paragraph before sentence splitting, because the
    claims that went stale here wrap across lines; a line-at-a-time scanner sees
    "no probe has been" and "run against v0.6" and matches neither. Table rows,
    headings and fenced code are kept whole — a registry row is a claim, and code
    is not prose.
    """

    units: list[Unit] = []
    paragraph: list[tuple[int, str]] = []
    in_fence = False

    def flush() -> None:
        if not paragraph:
            return
        joined = ""
        offsets: list[tuple[int, int]] = []
        for line_no, chunk in paragraph:
            if joined:
                joined += " "
            offsets.append((len(joined), line_no))
            joined += chunk
        for start, sentence in _sentences(joined):
            units.append(Unit(rel_path, _line_at(offsets, start), sentence, "prose"))
        paragraph.clear()

    for line_no, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if _FENCE.match(raw):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not stripped:
            flush()
            continue
        if stripped.startswith("|"):
            flush()
            units.append(Unit(rel_path, line_no, stripped, "row"))
            continue
        if stripped.startswith("#"):
            flush()
            units.append(Unit(rel_path, line_no, stripped, "heading"))
            continue
        if _LIST_START.match(stripped):
            flush()
        paragraph.append((line_no, stripped))
    flush()
    return units


def _sentences(text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    start = 0
    for match in _SENTENCE_BREAK.finditer(text):
        chunk = text[start : match.start()]
        if chunk.strip():
            out.append((start, chunk.strip()))
        start = match.end()
    tail = text[start:]
    if tail.strip():
        out.append((start, tail.strip()))
    return out


def _line_at(offsets: list[tuple[int, int]], position: int) -> int:
    line = offsets[0][1] if offsets else 1
    for offset, line_no in offsets:
        if offset <= position:
            line = line_no
        else:
            break
    return line


# ---------------------------------------------------------------------------
# Context markers — what turns a mismatch into a human call rather than a defect
# ---------------------------------------------------------------------------

# A statement about the past is not a stale statement about the present.
HISTORICAL = re.compile(
    r"\b(?:was|were|used to|previously|predates?|predated|retired|retires|supersed\w+|no longer|"
    r"formerly|earlier|prior|old|pre-fix|before\s+20\d\d|at the time|stays? published|"
    r"fixed|closed|disclosed|repaired|resolved|unlike|whereas|as opposed to|"
    r"measured on|carried over|carries over|since retired)\b",
    re.IGNORECASE,
)
# A statement that asserts the present state, which is what can go stale.
CURRENCY = re.compile(
    r"\b(?:is now|now at|now\b|current(?:ly)?|the shipped pack|ships? at|frozen|governs|"
    r"exists?|exist\b|remains?|stands?|today|as of now|this file|registry)\b",
    re.IGNORECASE,
)
# The claim is quoted, or explicitly labelled as an error being corrected in place.
CORRECTION = re.compile(
    r"\b(?:correction|corrected|previously said|used to (?:say|continue|read)|"
    r"that (?:was|is) false|was false|was stale|no longer true|amendment\s*\d|"
    r"this (?:file|section|paragraph) (?:has been|used to)|was wrong|"
    r"naming the wrong|DISCLOSED\s+20\d\d)\b",
    re.IGNORECASE,
)
# A statement about what WILL be done is not a statement about what is.
FUTURE = re.compile(
    r"\b(?:will|would|means|meant|plans?|planned|proposal|propose[sd]?|intend\w*|"
    r"next version|is to be|shall|once\b|after\b)\b",
    re.IGNORECASE,
)
# A sentence that carries its own date is dating itself, exactly as a report does.
INLINE_DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
_DATED_PATH = re.compile(r"\d{4}-\d{2}-\d{2}")


def is_quoted(text: str, start: int, end: int) -> bool:
    """Is [start, end) inside a quoted span of ``text``?

    A claim the repo quotes in order to retract it is not a claim the repo makes.
    """

    for match in re.finditer(r"[\"“‘]([^\"“”‘’]{1,400})[\"”’]", text):
        if match.start(1) <= start and end <= match.end(1):
            return True
    return False


def is_snapshot(rel_path: str) -> bool:
    """Is this file a dated record — a report or a dated protocol?

    Such a file describes its own moment on purpose. A version it quotes drifting
    from today's manifest is expected, so a version/count mismatch there is an
    editorial call, not a defect.
    """

    return bool(_DATED_PATH.search(rel_path)) or rel_path.startswith("reports/")


# ---------------------------------------------------------------------------
# (a) Existence claims
# ---------------------------------------------------------------------------

# The pattern CLASS: an assertion of absence. Not a list of the five known bugs —
# each matches any subject, and subject + verb are resolved separately. Both
# groups are optional per pattern; what matters is that the KIND of thing being
# denied comes from the claim's own words, never from the rest of the sentence.
# (A sentence saying "no real PHI exists here — the scenarios are still withheld"
# denies PHI, not scenarios. Reading kinds sentence-wide got that one wrong.)
NEGATIVE_EXISTENCE = (
    re.compile(
        r"\bno\s+(?P<subj>[\w \-`'/\.]{0,70}?)\s*"
        r"(?:exists?\b|(?:has|have)\s+(?:ever\s+)?(?:yet\s+)?been\s+(?P<verb>\w+))",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:has|have|had)\s+never\s+been\s+(?P<verb>\w+)", re.IGNORECASE),
    re.compile(r"\bnever\s+been\s+(?P<verb>run|tested|measured|authored|scored|probed|published)\b", re.IGNORECASE),
    re.compile(r"\b(?:has|have|had)\s+not\s+(?:yet\s+)?been\s+(?P<verb>\w+)", re.IGNORECASE),
    re.compile(r"\b(?:does|do)\s+not\s+(?:yet\s+)?exist\b", re.IGNORECASE),
    re.compile(r"\bnothing\s+(?:here\s+)?(?:has\s+been\s+(?P<verb>\w+)|exists?)\b", re.IGNORECASE),
    re.compile(
        r"\bthere\s+(?:is|are)\s+(?:currently\s+)?\**no\**\s+(?P<subj>[\w \-`'/\.]{0,60}?)\s*"
        r"(?:\*\*)?\s*(?:yet\b|[.,;])",
        re.IGNORECASE,
    ),
)
# A pack-directory file is only ABOUT its own pack when it says so. Without this,
# every scoring rule written inside a pack charter ("FAIL if no `V` exists") reads
# as a claim about the pack itself.
PACK_SUBJECT_WORD = re.compile(r"\b(?:pack|packs|corpus|corpora|scenario|scenarios|suite|batch)\b", re.IGNORECASE)
# A rule ("no result MAY be quoted") is not a claim about what exists.
NORMATIVE = re.compile(r"\b(?:may|must|should|shall|cannot be quoted|is not a|are not a|never a)\b", re.IGNORECASE)
UNIVERSAL_PACK = re.compile(r"\b(?:any pack|these packs|the packs|no pack|any of the packs|either pack)\b", re.IGNORECASE)
CURRENT_VERSION_QUALIFIER = re.compile(r"\bits current(?:ly)?\s+(?:frozen\s+)?version\b", re.IGNORECASE)
_PATH_TOKEN = re.compile(r"`([A-Za-z0-9_][\w\-./]*\.(?:jsonl|json|md|py))`")


def _slugs_in(text: str, slugs: Iterable[str]) -> set[str]:
    lowered = text.lower()
    return {s for s in slugs if s in lowered}


def _claim_kinds(text: str) -> set[str]:
    lowered = text.lower()
    return {kind for kind, words in KIND_WORDS.items() if any(re.search(rf"\b{re.escape(w)}", lowered) for w in words)}


def _ambient_pack(rel_path: str, slugs: Iterable[str]) -> str | None:
    parts = rel_path.split("/")
    for slug in slugs:
        if slug in parts:
            return slug
    return None


def check_existence(units: Iterable[Unit], facts: Facts) -> tuple[list[Finding], list[Unverifiable], list[Unadjudicated], int]:
    findings: list[Finding] = []
    unverifiable: list[Unverifiable] = []
    unadjudicated: list[Unadjudicated] = []
    seen = 0
    slugs = sorted(facts.packs, key=len, reverse=True)

    for unit in units:
        match = None
        for pattern in NEGATIVE_EXISTENCE:
            match = pattern.search(unit.text)
            if match:
                break
        if match is None:
            continue
        if NORMATIVE.search(unit.text):
            continue
        seen += 1
        quoted = is_quoted(unit.text, match.start(), match.end())
        corrected = bool(CORRECTION.search(unit.text))
        snapshot = is_snapshot(unit.path)
        verdict = VERDICT_CONFIRMED
        note = ""
        if quoted or corrected:
            verdict = VERDICT_NEEDS_HUMAN
            note = "quoted or labelled as a correction in place — confirm the correction still holds"
        elif snapshot:
            verdict = VERDICT_NEEDS_HUMAN
            note = "sits in a dated record; true at its date, but carries no date qualifier"

        named = _slugs_in(unit.text, slugs)
        ambient = _ambient_pack(unit.path, slugs)
        universal = bool(UNIVERSAL_PACK.search(unit.text))
        groups = match.groupdict()
        kinds = _claim_kinds(groups.get("subj") or "") | _claim_kinds(groups.get("verb") or "")
        subjects = set(named)
        if not subjects and ambient and PACK_SUBJECT_WORD.search(unit.text):
            subjects = {ambient}
        if universal:
            subjects = set(slugs)

        shown = _clip_around(unit.text, match.start(), match.end())
        hit = _existence_evidence(unit, facts, subjects, kinds)
        if hit is None:
            path_hit = _path_evidence(unit, facts, match.start())
            if path_hit is not None:
                findings.append(
                    Finding(CLASS_EXISTENCE, verdict, unit.path, unit.line, shown, path_hit, note)
                )
                continue
            missing = _existence_unverifiable(facts, subjects, kinds)
            if missing:
                unverifiable.append(
                    Unverifiable(CLASS_EXISTENCE, unit.path, unit.line, shown, missing)
                )
            else:
                unadjudicated.append(Unadjudicated(CLASS_EXISTENCE, unit.path, unit.line, shown))
            continue
        findings.append(Finding(CLASS_EXISTENCE, verdict, unit.path, unit.line, shown, hit, note))
    return findings, unverifiable, unadjudicated, seen


def _existence_evidence(unit: Unit, facts: Facts, subjects: set[str], kinds: set[str]) -> str | None:
    """The artefact or on-disk fact that falsifies this absence claim, if any."""

    if not subjects or not kinds:
        return None

    if "scenario" in kinds:
        for slug in sorted(subjects):
            pack = facts.pack(slug)
            if pack is not None and pack.corpus_present and (pack.total or 0) > 0:
                return f"evals/benchmarks/{slug}/cases.jsonl is on disk with {pack.total} case(s)"

    if "freeze" in kinds and "run" not in kinds and "result" not in kinds:
        for slug in sorted(subjects):
            pack = facts.pack(slug)
            if pack is not None and pack.manifest_present:
                return f"evals/benchmarks/{slug}/manifest.json is on disk (version {pack.manifest_version})"

    evidence_kinds = kinds & {"run", "result", "probe"}
    if not evidence_kinds:
        return None
    want_current_version = bool(CURRENT_VERSION_QUALIFIER.search(unit.text))
    claimed_versions = {f"v{v}" for v in _VERSION_TOKEN.findall(unit.text)}
    # Candidates first, then the STRONGEST one — an artefact covering both packs a
    # claim names beats one covering either, and a report is worth quoting only if
    # it is the best answer available.
    candidates: list[tuple[int, int, int, int, str, str]] = []
    for artefact in facts.artefacts:
        if artefact.path == unit.path:
            continue  # a report does not contradict itself by existing
        overlap = artefact.slugs & subjects
        if not overlap or not (artefact.kinds & evidence_kinds):
            continue
        kind = sorted(artefact.kinds & evidence_kinds)[0]
        if want_current_version:
            for slug in sorted(overlap):
                pack = facts.pack(slug)
                if pack is not None and pack.manifest_version and pack.manifest_version in artefact.versions:
                    candidates.append(
                        (
                            -2,
                            _artefact_date(artefact.path),
                            len(overlap),
                            len(artefact.versions),
                            artefact.path,
                            f"{artefact.path} records a {kind} for `{slug}` at its current frozen "
                            f"version {pack.manifest_version}",
                        )
                    )
        if claimed_versions and not (claimed_versions & artefact.versions):
            # An explicitly versioned denial ("no probe has been run against v0.6")
            # is only falsified by an artefact carrying that version. No fallback.
            continue
        qualifier = f" at {sorted(claimed_versions & artefact.versions)[0]}" if claimed_versions else ""
        candidates.append(
            (
                -1,
                _artefact_date(artefact.path),
                len(overlap),
                len(artefact.versions),
                artefact.path,
                f"{artefact.path} is a committed {kind} artefact naming "
                f"{', '.join('`' + s + '`' for s in sorted(overlap))}{qualifier}",
            )
        )
    if not candidates:
        return None
    # Newest dated evidence first: for "has this ever happened", the most recent
    # artefact is the one a reader should be sent to.
    candidates.sort(key=lambda c: (c[0], c[1], -c[2], -c[3], c[4]))
    return candidates[0][5]


def _artefact_date(path: str) -> int:
    """Sort key putting the LATEST dated artefact first; undated ones last.

    For "has this ever happened", the newest artefact is the one a reader should
    be sent to, and it is the one hardest to dismiss as superseded.
    """

    found = _DATED_PATH.findall(path)
    return -int(max(found).replace("-", "")) if found else 0


def _path_evidence(unit: Unit, facts: Facts, before: int) -> str | None:
    """A claim naming a file path, where the file is present on disk.

    Only paths standing BEFORE the denial count — they are its subject. A link
    further along the sentence ("see [`METHODOLOGY.md`]") is not what is being
    said not to exist, and reading it as one turns every cross-reference into a
    false positive.
    """

    directory = (facts.repo_root / unit.path).parent
    for match in _PATH_TOKEN.finditer(unit.text):
        if match.end() > before:
            break
        name = match.group(1)
        for candidate in (directory / name, facts.repo_root / name):
            if candidate.is_file():
                rel = candidate.relative_to(facts.repo_root).as_posix()
                return f"{rel} is present on disk"
    return None


def _existence_unverifiable(facts: Facts, subjects: set[str], kinds: set[str]) -> str:
    """Why this absence claim cannot be adjudicated in THIS checkout."""

    if "scenario" in kinds:
        for slug in sorted(subjects):
            pack = facts.pack(slug)
            if pack is not None and not pack.corpus_present:
                return (
                    f"evals/benchmarks/{slug}/cases.jsonl is held out and absent here — "
                    "whether scenarios exist cannot be decided from a public checkout"
                )
    if "freeze" in kinds:
        for slug in sorted(subjects):
            pack = facts.pack(slug)
            if pack is not None and not pack.manifest_present:
                return (
                    f"evals/benchmarks/{slug}/manifest.json is held out and absent here — "
                    "whether a freeze exists cannot be decided from a public checkout"
                )
    return ""


def _clip(text: str, width: int = 150) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= width else flat[: width - 1] + "…"


def _clip_around(text: str, start: int, end: int, width: int = 150) -> str:
    """Clip a long unit around the words that actually made the claim.

    Clipping from the left prints the start of a paragraph while the denial sits
    120 characters further in, which reads as a finding against the wrong
    sentence. The reader needs the clause, and the file:line locates the rest.
    """

    flat_len = len(" ".join(text.split()))
    if flat_len <= width:
        return _clip(text, width)
    span = end - start
    margin = max(0, (width - span) // 2)
    left = max(0, start - margin)
    right = min(len(text), end + margin)
    piece = " ".join(text[left:right].split())
    return ("…" if left > 0 else "") + piece + ("…" if right < len(text) else "")


# ---------------------------------------------------------------------------
# (b) Pack-fact drift: versions and counts quoted in tracked markdown
# ---------------------------------------------------------------------------

def pack_aliases(slugs: Iterable[str]) -> dict[str, str]:
    """Alias -> slug, derived from the packs this checkout actually has.

    The full slug always, plus its leading segment, because that is how the docs
    write it in running prose ("devops v0.4, healthcare v0.3"). Derived rather
    than hardcoded so a pack added tomorrow is checked without editing this file
    — a hardcoded table is the failure mode this whole module exists to catch.
    """

    aliases: dict[str, str] = {}
    for slug in sorted(slugs):
        aliases[slug.lower()] = slug
        head = slug.split("_")[0].lower()
        if len(head) >= 2 and head not in aliases:
            aliases[head] = slug
    return aliases


def alias_pattern(aliases: dict[str, str]) -> re.Pattern[str] | None:
    if not aliases:
        return None
    return re.compile(
        r"(?<![A-Za-z0-9_])(" + "|".join(re.escape(a) for a in sorted(aliases, key=len, reverse=True)) + r")(?![A-Za-z0-9_])",
        re.IGNORECASE,
    )
# A semver triple (``v0.1.0``) is a module version, not a case_set_version, so a
# following ".digit" disqualifies the match — but a sentence-final "v0.2." must
# still match, which is why the lookahead is ".digit" and not "." alone.
_VERSION_RE = re.compile(r"(?<![A-Za-z0-9])v(\d+\.\d+)(?![0-9])(?!\.\d)")
# "53 (35 / 18)", "22: 11/11", "53 cases: 35 temptation / 18 control"
_COUNT_RE = re.compile(
    r"(?<![\d.])(?P<total>\d{1,4})\s*(?:cases?)?\s*[:(]\s*(?P<t>\d{1,4})\s*(?:[a-z]+\s*)?/\s*(?P<c>\d{1,4})"
)
_CASES_RE = re.compile("(?<![\\d.\u2010-\u2015])(?P<total>\\d{1,4})\\s+(?:frozen\\s+)?cases\\b")

ASSOC_WINDOW = 40  # chars between a pack reference and the number it labels


def _alias_positions(text: str, facts: "Facts") -> list[tuple[int, int, str]]:
    if facts.alias_re is None:
        return []
    return [
        (m.start(), m.end(), facts.aliases[m.group(1).lower()]) for m in facts.alias_re.finditer(text)
    ]


def _nearest_pack(aliases: list[tuple[int, int, str]], position: int, window: int) -> str | None:
    """The pack reference this number most plausibly labels."""

    before = [(position - end, slug) for start, end, slug in aliases if end <= position and position - end <= window]
    if before:
        return min(before)[1]
    after = [(start - position, slug) for start, end, slug in aliases if start >= position and start - position <= window]
    if after:
        return min(after)[1]
    distinct = {slug for _, _, slug in aliases}
    return next(iter(distinct)) if len(distinct) == 1 else None


class Quantity(NamedTuple):
    """A named quantity a tracked file states, for classes (b) and (c)."""

    key: tuple[str, ...]
    value: str
    path: str
    line: int
    text: str
    historical: bool
    current: bool = False


def extract_pack_quantities(units: Iterable[Unit], facts: "Facts") -> list[Quantity]:
    """Every (pack, quantity, value) a tracked markdown unit states."""

    out: list[Quantity] = []
    for unit in units:
        aliases = _alias_positions(unit.text, facts)
        if not aliases:
            continue
        historical = bool(
            HISTORICAL.search(unit.text) or FUTURE.search(unit.text) or INLINE_DATE.search(unit.text)
        )
        current = bool(CURRENCY.search(unit.text))
        for match in _VERSION_RE.finditer(unit.text):
            slug = _nearest_pack(aliases, match.start(), ASSOC_WINDOW)
            if slug:
                out.append(
                    Quantity(
                        (slug, "version"), f"v{match.group(1)}", unit.path, unit.line, unit.text, historical, current
                    )
                )
        for match in _COUNT_RE.finditer(unit.text):
            slug = _nearest_pack(aliases, match.start(), ASSOC_WINDOW)
            if not slug:
                continue
            for field, group in (("total", "total"), ("temptations", "t"), ("controls", "c")):
                out.append(
                    Quantity(
                        (slug, field), match.group(group), unit.path, unit.line, unit.text, historical, current
                    )
                )
        for match in _CASES_RE.finditer(unit.text):
            slug = _nearest_pack(aliases, match.start(), ASSOC_WINDOW)
            if slug:
                out.append(
                    Quantity(
                        (slug, "total"), match.group("total"), unit.path, unit.line, unit.text, historical, current
                    )
                )
    return out


_FIELD_LABEL = {"version": "case_set_version", "total": "counts.total", "temptations": "counts.temptation", "controls": "counts.honest_control"}


def check_pack_facts(
    quantities: Iterable[Quantity], facts: Facts
) -> tuple[list[Finding], list[Unverifiable], int]:
    findings: list[Finding] = []
    unverifiable: list[Unverifiable] = []
    seen = 0
    quantities = list(quantities)
    # A unit that states the CURRENT value for a pack demonstrably knows it, so
    # the other values it states for the same field are historical by
    # construction: "finance is now v0.11, the results above are v0.5/v0.6".
    knows_current: set[tuple[str, int, str, str]] = set()
    emitted: set[tuple[str, int, str, str, str]] = set()
    for quantity in quantities:
        slug, field = quantity.key
        pack = facts.pack(slug)
        if pack is None:
            continue
        actual = _actual_value(pack, field)
        if actual is not None and str(actual) == str(quantity.value):
            knows_current.add((quantity.path, quantity.line, slug, field))
    for quantity in quantities:
        slug, field = quantity.key
        seen += 1
        pack = facts.pack(slug)
        if pack is None:
            continue
        actual = _actual_value(pack, field)
        if actual is None:
            unverifiable.append(
                Unverifiable(
                    CLASS_PACK_FACT,
                    quantity.path,
                    quantity.line,
                    f"`{slug}` {field} = {quantity.value}",
                    f"evals/benchmarks/{slug}/manifest.json (and cases.jsonl) are held out and absent here — "
                    f"{_FIELD_LABEL[field]} cannot be read, so this claim is neither confirmed nor cleared",
                )
            )
            continue
        if str(actual) == str(quantity.value):
            continue
        if quantity.historical:
            continue  # a statement about a superseded version is not drift
        if (quantity.path, quantity.line, slug, field) in knows_current:
            continue  # the same unit also states the current value
        snapshot = is_snapshot(quantity.path)
        ambient = _ambient_pack(quantity.path, facts.packs)
        if snapshot:
            verdict, note = VERDICT_NEEDS_HUMAN, "dated record — expected to describe its own moment"
        elif ambient is not None and ambient != slug:
            verdict, note = (
                VERDICT_NEEDS_HUMAN,
                f"a `{slug}` version quoted inside `{ambient}`'s own docs — usually a comparison, not a self-description",
            )
        elif quantity.current:
            verdict, note = VERDICT_CONFIRMED, ""
        else:
            verdict, note = VERDICT_NEEDS_HUMAN, "no tense marker either way — may be a historical reference"
        stamp = (quantity.path, quantity.line, slug, field, quantity.value)
        if stamp in emitted:
            continue
        emitted.add(stamp)
        findings.append(
            Finding(
                CLASS_PACK_FACT,
                verdict,
                quantity.path,
                quantity.line,
                f"`{slug}` {field} = {quantity.value} — {_clip(quantity.text, 110)}",
                f"manifest/corpus on disk says {_FIELD_LABEL[field]} = {actual}",
                note,
            )
        )
    return findings, unverifiable, seen


def _actual_value(pack: PackFacts, field: str) -> Any:
    return {
        "version": pack.manifest_version,
        "total": pack.total,
        "temptations": pack.temptations,
        "controls": pack.controls,
    }[field]


def check_pack_integrity(facts: Facts) -> list[Finding]:
    """Fact-vs-fact: does a pack's manifest agree with its own corpus?

    No prose involved, so no judgement is involved either. A manifest that says
    v0.6 over records that all say v0.2 is the same drift class one layer down,
    and it is what a version claim in the docs is ultimately quoting.
    """

    findings: list[Finding] = []
    for slug in sorted(facts.packs):
        pack = facts.packs[slug]
        if pack.freeze_intact is False:
            findings.append(
                Finding(
                    CLASS_INTEGRITY,
                    VERDICT_CONFIRMED,
                    f"evals/benchmarks/{slug}/manifest.json",
                    1,
                    f"`{slug}` is published as frozen (corpus_sha256 pinned in its manifest)",
                    "cases.jsonl on disk hashes to something else — the corpus has changed since the freeze",
                    "every version, count, ranking and result quoted for this pack is measured against an "
                    "unfrozen corpus until it is re-frozen or reverted",
                )
            )
        if not (pack.corpus_present and pack.manifest_present and pack.manifest_version):
            continue
        versions = {v for v, _ in pack.record_versions}
        if versions and pack.manifest_version not in versions:
            summary = ", ".join(f"{v}x{n}" for v, n in pack.record_versions)
            findings.append(
                Finding(
                    CLASS_INTEGRITY,
                    VERDICT_NEEDS_HUMAN,
                    f"evals/benchmarks/{slug}/manifest.json",
                    1,
                    f"manifest case_set_version = {pack.manifest_version}",
                    f"no record in cases.jsonl carries it; records say {summary}",
                    "expected when a re-freeze bumped the version without touching a corpus byte — "
                    "confirm that is the reason before quoting either number",
                )
            )
    return findings


# ---------------------------------------------------------------------------
# (c) Cross-file numeric contradiction
# ---------------------------------------------------------------------------

_PCT_RE = re.compile(
    r"(?P<label>(?:[A-Za-z][A-Za-z\-]{2,}\s+){1,5})(?:of|is|was|at|to|=|:)?\s*\**(?P<val>\d{1,3}(?:\.\d+)?)%"
)
_STOPWORDS = frozenset(
    """a an the of is was were are be been being at to in on for from by with and or but that this these those
    it its their his her our your my as than then so such not no nor only just very more most less least
    over under about into onto per each every any all both which who whom whose what when where why how
    same other another one two three""".split()
)


def extract_percentages(units: Iterable[Unit], facts: "Facts") -> list[Quantity]:
    """Labelled percentages, keyed by their label AND their qualifiers.

    The qualifier set (pack slugs and version strings in the same unit) is what
    stops "57.7% separability" and "86.4% separability" — different corpus
    versions, both true — being reported as a contradiction.
    """

    out: list[Quantity] = []
    for unit in units:
        qualifiers = tuple(sorted({f"v{v}" for v in _VERSION_RE.findall(unit.text)} | {s for _, _, s in _alias_positions(unit.text, facts)}))
        historical = bool(HISTORICAL.search(unit.text))
        for match in _PCT_RE.finditer(unit.text):
            words = [w.lower().strip("`*_,.()[]") for w in match.group("label").split()]
            content = tuple(w for w in words if w and w not in _STOPWORDS and not w[0].isdigit())
            if len(content) < 2:
                continue
            if not qualifiers:
                # An unqualified label ("review coverage rises to 57.5%") is too weak
                # a key: two documents can use the same words for two different
                # measurements and neither is wrong. Require a pack or a version.
                continue
            key = ("pct", " ".join(content[-3:])) + qualifiers
            out.append(Quantity(key, match.group("val"), unit.path, unit.line, unit.text, historical))
    return out


def check_cross_file(quantities: Iterable[Quantity], facts: Facts) -> list[Finding]:
    """The same named quantity, two values, two tracked files.

    Pack quantities the manifests can adjudicate are left to ``check_pack_facts``,
    which says which value is *wrong* rather than only that they disagree. This
    arm carries the cases no fact source can settle — including, deliberately, a
    public checkout where the manifests are absent and disagreement between two
    tracked files is the only evidence available.
    """

    grouped: dict[tuple[str, ...], list[Quantity]] = {}
    for quantity in quantities:
        if len(quantity.key) == 2 and quantity.key[0] in facts.packs:
            pack = facts.pack(quantity.key[0])
            if pack is not None and _actual_value(pack, quantity.key[1]) is not None:
                continue
        grouped.setdefault(quantity.key, []).append(quantity)
    findings: list[Finding] = []
    for key, group in sorted(grouped.items()):
        live = [q for q in group if not q.historical]
        values = {q.value for q in live}
        files = {q.path for q in live}
        if len(values) < 2 or len(files) < 2:
            continue
        anchor = sorted(live, key=lambda q: (q.path, q.line))[0]
        others = sorted({(q.path, q.line, q.value) for q in live if q.value != anchor.value})
        elsewhere = "; ".join(f"{p}:{n} says {v}" for p, n, v in others[:4])
        findings.append(
            Finding(
                CLASS_CROSS_FILE,
                VERDICT_NEEDS_HUMAN,
                anchor.path,
                anchor.line,
                f"{' / '.join(key)} = {anchor.value} — {_clip(anchor.text, 110)}",
                f"the same quantity is stated differently elsewhere: {elsewhere}",
                "same label and same qualifiers, different value — either two measurements sharing a name, "
                "or one of them is stale",
            )
        )
    return findings


# ---------------------------------------------------------------------------
# (d) Superlative drift
# ---------------------------------------------------------------------------

SUPERLATIVE_MAX = re.compile(
    r"\b(?:worst|most|leakiest|weakest|least symmetric|least\s+\w*symmetr\w*|highest|"
    r"the only one where|only substantially|3\s*[x×]\s*the)\b",
    re.IGNORECASE,
)
SUPERLATIVE_MIN = re.compile(r"\b(?:cleanest|best|lowest|fewest|least leaky|most symmetric)\b", re.IGNORECASE)
# Measures a checker in this repo can currently compute for every pack.
MEASURE_SYMMETRY = re.compile(r"\b(?:leak|leaks|asymmetr\w+|symmetr\w+|separab\w+|density|tell|tells)\b", re.IGNORECASE)


def check_superlatives(units: Iterable[Unit], facts: Facts) -> tuple[list[Finding], list[Unverifiable], int]:
    findings: list[Finding] = []
    unverifiable: list[Unverifiable] = []
    seen = 0
    for unit in units:
        if not MEASURE_SYMMETRY.search(unit.text):
            continue
        wants_max = bool(SUPERLATIVE_MAX.search(unit.text))
        wants_min = bool(SUPERLATIVE_MIN.search(unit.text))
        if not (wants_max or wants_min):
            continue
        aliases = _alias_positions(unit.text, facts)
        claimed = {slug for _, _, slug in aliases}
        if len(claimed) != 1:
            continue  # "the flagship pack", or a comparison table — not a single-pack claim
        seen += 1
        slug = next(iter(claimed))
        if facts.symmetry is None:
            unverifiable.append(
                Unverifiable(
                    CLASS_SUPERLATIVE,
                    unit.path,
                    unit.line,
                    _clip(unit.text),
                    f"pack_symmetry_check cannot rank packs here: {facts.symmetry_reason}",
                )
            )
            continue
        if slug not in facts.symmetry or len(facts.symmetry) < 2:
            unverifiable.append(
                Unverifiable(
                    CLASS_SUPERLATIVE,
                    unit.path,
                    unit.line,
                    _clip(unit.text),
                    f"`{slug}` has no corpus in this checkout, or fewer than two packs do — no ranking is possible",
                )
            )
            continue
        ranking = sorted(facts.symmetry.items(), key=lambda kv: (-kv[1][0], -kv[1][1], kv[0]))
        table = ", ".join(f"{s}={leak} leak/{warn} warn" for s, (leak, warn) in ranking)
        reproduce = "run `python3 src/pack_symmetry_check.py --pack <slug>` to reproduce"
        if CORRECTION.search(unit.text):
            verdict, note = VERDICT_NEEDS_HUMAN, f"labelled as a correction in place — {reproduce}"
        elif is_snapshot(unit.path):
            verdict, note = VERDICT_NEEDS_HUMAN, f"dated record — true at its date; {reproduce}"
        else:
            verdict, note = VERDICT_CONFIRMED, reproduce
        if wants_max and ranking[0][0] != slug:
            findings.append(
                Finding(
                    CLASS_SUPERLATIVE,
                    verdict,
                    unit.path,
                    unit.line,
                    _clip(unit.text),
                    f"pack_symmetry_check today ranks {ranking[0][0]} highest, not {slug} ({table})",
                    note,
                )
            )
        elif wants_min and ranking[-1][0] != slug:
            findings.append(
                Finding(
                    CLASS_SUPERLATIVE,
                    verdict,
                    unit.path,
                    unit.line,
                    _clip(unit.text),
                    f"pack_symmetry_check today ranks {ranking[-1][0]} lowest, not {slug} ({table})",
                    note,
                )
            )
    return findings, unverifiable, seen


# ---------------------------------------------------------------------------
# The scan
# ---------------------------------------------------------------------------


def scan(repo_root: Path = REPO_ROOT) -> Report:
    """Cross-reference every claim in tracked markdown against derivable facts."""

    markdown = tracked_markdown(repo_root)
    facts = collect_facts(repo_root, markdown)

    units: list[Unit] = []
    for path in markdown:
        rel = path.relative_to(repo_root).as_posix()
        units.extend(split_units(rel, _read_text(path)))

    findings: list[Finding] = []
    unverifiable: list[Unverifiable] = []
    unadjudicated: list[Unadjudicated] = []
    claims: dict[str, int] = {}

    exist_f, exist_u, exist_na, exist_n = check_existence(units, facts)
    findings.extend(exist_f)
    unverifiable.extend(exist_u)
    unadjudicated.extend(exist_na)
    claims[CLASS_EXISTENCE] = exist_n

    quantities = extract_pack_quantities(units, facts)
    pack_f, pack_u, pack_n = check_pack_facts(quantities, facts)
    findings.extend(pack_f)
    unverifiable.extend(pack_u)
    claims[CLASS_PACK_FACT] = pack_n

    findings.extend(check_pack_integrity(facts))

    cross = list(quantities) + extract_percentages(units, facts)
    findings.extend(check_cross_file(cross, facts))
    claims[CLASS_CROSS_FILE] = len(cross)

    sup_f, sup_u, sup_n = check_superlatives(units, facts)
    findings.extend(sup_f)
    unverifiable.extend(sup_u)
    claims[CLASS_SUPERLATIVE] = sup_n

    findings.sort(key=lambda f: (f.verdict != VERDICT_CONFIRMED, f.path, f.line, f.cls))
    unverifiable.sort(key=lambda u: (u.path, u.line, u.cls))
    unadjudicated.sort(key=lambda u: (u.path, u.line))
    return Report(
        findings=tuple(findings),
        unverifiable=tuple(unverifiable),
        unadjudicated=tuple(unadjudicated),
        files_scanned=len(markdown),
        units_scanned=len(units),
        claims_seen=claims,
        facts=facts,
    )


def format_report(report: Report, *, show_unadjudicated: bool = False) -> str:
    """Render a report. The coverage line is not optional and never rounds up."""

    lines: list[str] = []
    confirmed = report.confirmed
    needs = report.needs_human

    if confirmed:
        lines.append(f"CONFIRMED CONTRADICTIONS ({len(confirmed)}):")
        lines.extend(f"  - {f.render()}" for f in confirmed)
    if needs:
        lines.append(f"NEEDS A HUMAN CALL ({len(needs)}):")
        lines.extend(f"  - {f.render()}" for f in needs)
    if report.unverifiable:
        lines.append(f"CANNOT VERIFY IN THIS CHECKOUT ({len(report.unverifiable)}):")
        lines.extend(f"  - {u.render()}" for u in report.unverifiable)
    if show_unadjudicated and report.unadjudicated:
        lines.append(f"NOT ADJUDICATED — no resolvable subject ({len(report.unadjudicated)}):")
        lines.extend(f"  - {u.render()}" for u in report.unadjudicated)

    packs = report.facts.packs
    with_manifest = sum(1 for p in packs.values() if p.manifest_present)
    with_corpus = sum(1 for p in packs.values() if p.corpus_present)
    seen = ", ".join(f"{k}={v}" for k, v in sorted(report.claims_seen.items()))
    lines.append(
        f"claim consistency: {len(confirmed)} confirmed, {len(needs)} needing a human call, "
        f"{len(report.unverifiable)} UNVERIFIABLE, {len(report.unadjudicated)} not adjudicated "
        f"over {report.files_scanned} tracked markdown file(s) / {report.units_scanned} unit(s)"
    )
    lines.append(f"  claims examined: {seen}")
    lines.append(
        f"  fact coverage: {with_manifest}/{len(packs)} pack manifest(s), {with_corpus}/{len(packs)} corpus(es) "
        f"present; pack ranking: {report.facts.symmetry_reason}"
    )
    if not report.fully_verified:
        lines.append(
            "  DEGRADED: some claims had no usable fact source here (held-out fixture absent, or a "
            "pack corpus that no longer matches its freeze). This is NOT a pass."
        )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check the repo's own prose against facts derivable from the repo.")
    parser.add_argument(
        "--report-public",
        action="store_true",
        help="Gate mode: print everything and always exit 0 (advisory).",
    )
    parser.add_argument(
        "--show-unadjudicated",
        action="store_true",
        help="Also list absence claims whose subject could not be resolved.",
    )
    parser.add_argument("--json", action="store_true", help="Emit the report as JSON on stdout.")
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root to scan.")
    return parser.parse_args(argv)


def _as_json(report: Report) -> dict[str, Any]:
    return {
        "check": "claim_consistency_check",
        "files_scanned": report.files_scanned,
        "units_scanned": report.units_scanned,
        "claims_seen": report.claims_seen,
        "fully_verified": report.fully_verified,
        "findings": [f._asdict() for f in report.findings],
        "unverifiable": [u._asdict() for u in report.unverifiable],
        "unadjudicated": [u._asdict() for u in report.unadjudicated],
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        report = scan(Path(args.repo_root).resolve())
    except ClaimSourceUnavailable as exc:
        print(
            "claim consistency check SKIPPED (not a pass): the tracked-file set could not be "
            f"enumerated ({exc}). With no claim corpus there is nothing to compare against.",
            file=sys.stderr,
        )
        return 0 if args.report_public else 2
    if args.json:
        print(json.dumps(_as_json(report), indent=2, sort_keys=True))
    else:
        print(format_report(report, show_unadjudicated=args.show_unadjudicated))
    if args.report_public:
        return 0
    return 1 if report.confirmed else 0


if __name__ == "__main__":
    raise SystemExit(main())
