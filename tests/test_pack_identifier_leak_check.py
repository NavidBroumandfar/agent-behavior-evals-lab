"""Tests for the deterministic corpus-identifier leak checker.

The load-bearing properties, each named in ``src/pack_identifier_leak_check.py``'s
own docstring and pinned here because an unverified check that reports nothing is
indistinguishable from a clean result:

1. a held-out prompt identifier that also sits in a git-tracked file is a ``leak``
   — in *any* tracked file, not only markdown;
2. the reserved ``X``-prefix illustration band is what makes a public worked
   example safe, and a corpus prompt that takes an identifier from that band is
   itself a finding;
3. published vocabulary (``AGB-*`` failure modes, ``ABP-*`` policy refs) and the
   corpus's own ``case_id`` values are excluded by construction, not by judgment;
4. the substring boundary is alphanumeric, not hyphen-inclusive — ``XGL-1010``
   must not match inside ``XGL-10105`` but must match inside ``AUD-XGL-1010``;
5. the shape rule: prose hyphenation and dotted versions are not identifiers, and
   a token needs a digit and ``MIN_IDENTIFIER_LEN`` characters;
6. absence is reported, never silently green — an absent corpus is ``SKIPPED`` by
   name, an unavailable tracked set skips the whole check with a visible notice,
   and a corpus that is present but yields nothing to scan is a finding;
7. ``--advisory`` exits 0 where the default exits 1 on the same finding, and the
   summary names the mode it actually ran in.

Coverage is asserted RELATIVELY throughout: no test asserts an absolute count of
identifiers, packs or findings against the real repository, because a clean public
checkout has no held-out corpus at all and such a test would fail there. Synthetic
packs and synthetic git repositories in temp dirs only; no held-out fixture is ever
referenced. Deterministic, offline, no providers.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pack_identifier_leak_check as pilc

CHECK_ALL_PATH = REPO_ROOT / "scripts/check_all.py"

_HAS_GIT = shutil.which("git") is not None

# Identifiers used by these tests. NOT drawn from any pack: 'ZLED' is a synthetic
# prefix that appears in no corpus, so nothing here can double as a real anchor.
_LEAKY_ID = "ZLED-4102"
_LEAKY_PROMPT = f"Post the correcting entry against {_LEAKY_ID} before the cycle closes."


# ---------------------------------------------------------------------------
# Synthetic git repositories
# ---------------------------------------------------------------------------
#
# The tracked-file side of this check is literally `git ls-files`, so it cannot be
# faked with a directory listing. Each scenario builds a throwaway repository with
# global/system git config disabled, so a developer's own gitconfig or global
# excludes cannot change what these tests measure.

_GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        env=_GIT_ENV,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _init_repo(root: Path) -> None:
    _git(root, "init", "-q")


def _track(root: Path, relpath: str, text: str) -> Path:
    """Write a file and put it in the index — i.e. make it *tracked*, and public."""

    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    _git(root, "add", "-f", "--", relpath)
    return path


def _case(cid: str = "ZLD-201", prompt: str = _LEAKY_PROMPT) -> dict:
    return {"case_id": cid, "kind": "temptation", "user_prompt": prompt}


def _write_pack(bench: Path, slug: str, cases: list[dict] | None) -> Path:
    """A pack directory: public charter always, held-out corpus only when given.

    ``cases=None`` is the clean-public-checkout shape — the charter is committed,
    the corpus is gitignored and absent.
    """

    pack = bench / slug
    pack.mkdir(parents=True, exist_ok=True)
    (pack / "METHODOLOGY.md").write_text("public method\n", encoding="utf-8")
    if cases is not None:
        (pack / "cases.jsonl").write_text(
            "".join(json.dumps(c) + "\n" for c in cases), encoding="utf-8"
        )
    return pack


def _run_cli(argv: list[str]) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = pilc.main(argv)
    return code, out.getvalue(), err.getvalue()


def _leaks(findings: list[str]) -> list[str]:
    return [f for f in findings if pilc.severity_of(f) == pilc.SEVERITY_LEAK]


def _notices(findings: list[str]) -> list[str]:
    return [f for f in findings if pilc.severity_of(f) == pilc.SEVERITY_NOTICE]


def _summary(result: pilc.Sweep, mode: str = "BLOCKING") -> str:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        pilc._print_summary(result, mode)
    return out.getvalue()


# ---------------------------------------------------------------------------
# Shape rule
# ---------------------------------------------------------------------------


class IdentifierShapeTests(unittest.TestCase):
    """What counts as a memorisable anchor, and what is just prose."""

    def test_fixture_shaped_tokens_are_identifiers(self) -> None:
        for token in ("ZLED-4102", "XEMP-4471", "XCTRL-AML-07", "XHOLD-LIT-51", "XACCTREF-Z1A0"):
            self.assertTrue(pilc.is_identifier(token), token)

    def test_prose_hyphenation_is_not_an_identifier(self) -> None:
        # The digit requirement is what separates a fixture id from English. If
        # this ever relaxes, every hyphenated adjective in every charter becomes a
        # candidate leak and the check drowns in its own noise.
        for token in ("pre-approved", "out-of-band", "read-only", "sign-off", "end-of-day"):
            self.assertFalse(pilc.is_identifier(token), token)

    def test_dotted_versions_are_not_identifiers(self) -> None:
        # No hyphen segmentation: 'v2.7.1' is a version, a scenario fact rather
        # than a name for a fixture.
        for token in ("v2.7.1", "v1.2.3", "svc.metrics"):
            self.assertFalse(pilc.is_identifier(token), token)

    def test_a_token_needs_a_digit_and_a_hyphen_and_a_leading_letter(self) -> None:
        self.assertFalse(pilc.is_identifier("ZLED4102"))  # no hyphen segmentation
        self.assertFalse(pilc.is_identifier("LEDGER-CODE"))  # no digit
        self.assertFalse(pilc.is_identifier("1234-5678"))  # no leading letter

    def test_min_identifier_len_is_the_floor_and_it_is_what_rejects_short_tokens(self) -> None:
        # PIN of the floor itself, and of the fact that the floor (not the shape)
        # is what rejects 'R-4': the same token one character longer is accepted.
        self.assertEqual(pilc.MIN_IDENTIFIER_LEN, 4)
        self.assertTrue(pilc.IDENTIFIER_RE.match("R-4"))  # shape is fine...
        self.assertFalse(pilc.is_identifier("R-4"))  # ...length is not
        self.assertTrue(pilc.is_identifier("R-42"))
        self.assertFalse(pilc.is_identifier("A-1"))

    def test_identifiers_in_trims_surrounding_punctuation(self) -> None:
        found = pilc.identifiers_in("(ZLED-4102) and ZBCR-8801. Then ZREQ-77;")
        self.assertEqual(found, {"ZLED-4102", "ZBCR-8801", "ZREQ-77"})

    def test_identifiers_in_ignores_prose_and_versions_in_the_same_sentence(self) -> None:
        found = pilc.identifiers_in("The pre-approved out-of-band rollout of v2.7.1 is read-only.")
        self.assertEqual(found, set())

    def test_published_vocabulary_is_excluded_at_extraction(self) -> None:
        # AGB-* failure modes and ABP-* policy refs are in PACK-SPEC's public
        # column. A prompt citing one is citing shared vocabulary, not an anchor.
        self.assertEqual(pilc.PUBLISHED_ID_PREFIXES, ("AGB-", "ABP-"))
        self.assertTrue(pilc.is_published_vocabulary("AGB-FIN-004"))
        self.assertTrue(pilc.is_published_vocabulary("ABP-07-A"))
        self.assertFalse(pilc.is_published_vocabulary("ZLED-4102"))
        self.assertEqual(
            pilc.identifiers_in("Cite AGB-FIN-004 under ABP-07-A while posting ZLED-4102"),
            {"ZLED-4102"},
        )

    def test_published_vocabulary_match_is_case_folded(self) -> None:
        self.assertTrue(pilc.is_published_vocabulary("agb-fin-004"))
        self.assertTrue(pilc.is_published_vocabulary("abp-07"))

    def test_reserved_band_is_the_leading_segment_only(self) -> None:
        # 'X' has to lead the whole token. A composed identifier whose LATER
        # segment starts with X ('AUD-XGL-1010') is an ordinary identifier — which
        # is exactly the audit-trail token the finance taxonomy published.
        for token in ("XEMP-4471", "XHOLD-LIT-51", "XCTRL-AML-07", "X-4471"):
            self.assertTrue(pilc.is_reserved_illustration(token), token)
        for token in ("AUD-XGL-1010", "EMP-4471", "ZLED-4102"):
            self.assertFalse(pilc.is_reserved_illustration(token), token)

    def test_reserved_band_is_uppercase_as_the_spec_writes_it(self) -> None:
        # PIN of a deliberate asymmetry: published vocabulary is case-folded, the
        # reserved band is not. It fails SAFE — a lowercase 'x'-initial corpus
        # token is treated as an ordinary identifier, so a collision with it is
        # reported as a leak rather than downgraded to a notice.
        self.assertFalse(pilc.is_reserved_illustration("xemp-4471"))
        self.assertTrue(pilc.is_identifier("xemp-4471"))

    def test_severity_tags_are_machine_readable(self) -> None:
        self.assertEqual(pilc.severity_of("[leak] X: y"), pilc.SEVERITY_LEAK)
        self.assertEqual(pilc.severity_of("[notice] X: y"), pilc.SEVERITY_NOTICE)
        self.assertEqual(pilc.severity_of("untagged line"), "")
        self.assertTrue(pilc.has_leaks(["[notice] a: b", "[leak] c: d"]))
        self.assertFalse(pilc.has_leaks(["[notice] a: b"]))
        self.assertFalse(pilc.has_leaks([]))


# ---------------------------------------------------------------------------
# Prompt-side extraction
# ---------------------------------------------------------------------------


class CorpusScanTests(unittest.TestCase):
    """``scan_corpus``: prompts only, case ids out, reserved band bucketed apart."""

    def test_prompt_identifiers_are_keyed_to_the_cases_that_used_them(self) -> None:
        scan = pilc.scan_corpus(
            "zpack",
            [_case("ZLD-201"), _case("ZLD-202"), _case("ZLD-203", "Reconcile ZBCR-8801 today.")],
        )
        self.assertEqual(scan.slug, "zpack")
        self.assertEqual(scan.prompts, 3)
        self.assertEqual(scan.identifiers, {_LEAKY_ID: ["ZLD-201", "ZLD-202"], "ZBCR-8801": ["ZLD-203"]})
        self.assertEqual(scan.reserved_used, {})

    def test_only_the_user_prompt_is_read(self) -> None:
        # expected_behavior / scoring_notes are held out too, but they are written
        # in the shared public vocabulary; scanning them would flag the spec's own
        # deliberately-published words.
        scan = pilc.scan_corpus(
            "zpack",
            [
                {
                    "case_id": "ZLD-204",
                    "user_prompt": "Nothing identifier-shaped here.",
                    "expected_behavior": "Refuse; ZBCR-8801 is on hold.",
                    "scoring_notes": "breach=none for ZLED-4102",
                }
            ],
        )
        self.assertEqual(scan.identifiers, {})
        self.assertEqual(scan.prompts, 1)

    def test_blank_and_missing_prompts_are_not_counted_as_scanned(self) -> None:
        scan = pilc.scan_corpus(
            "zpack",
            [_case("ZLD-201", "   "), {"case_id": "ZLD-202"}, _case("ZLD-203")],
        )
        self.assertEqual(scan.prompts, 1)

    def test_a_case_id_quoted_in_its_own_prompt_is_not_a_leak(self) -> None:
        scan = pilc.scan_corpus(
            "zpack", [_case("ZLD-4102", f"Per ticket ZLD-4102, post against {_LEAKY_ID}.")]
        )
        self.assertEqual(scan.identifiers, {_LEAKY_ID: ["ZLD-4102"]})

    def test_a_case_id_belonging_to_a_sibling_case_is_also_excluded(self) -> None:
        # The exclusion is corpus-wide: case ids are published in reports and
        # protocols by design, whichever case quotes them.
        scan = pilc.scan_corpus("zpack", [_case("ZLD-4102", "See ZLD-9001."), _case("ZLD-9001")])
        self.assertNotIn("ZLD-9001", scan.identifiers)

    def test_reserved_band_use_by_a_prompt_lands_in_its_own_bucket(self) -> None:
        scan = pilc.scan_corpus("zpack", [_case("ZLD-201", "Adjust XEMP-4471 and ZBCR-8801.")])
        self.assertEqual(scan.reserved_used, {"XEMP-4471": ["ZLD-201"]})
        self.assertEqual(scan.identifiers, {"ZBCR-8801": ["ZLD-201"]})

    def test_case_ids_are_sorted_so_findings_are_stable(self) -> None:
        scan = pilc.scan_corpus("zpack", [_case("ZLD-9"), _case("ZLD-1"), _case("ZLD-5")])
        self.assertEqual(scan.identifiers[_LEAKY_ID], ["ZLD-1", "ZLD-5", "ZLD-9"])

    def test_empty_corpus_yields_an_empty_scan_rather_than_raising(self) -> None:
        scan = pilc.scan_corpus("zpack", [])
        self.assertEqual((scan.prompts, scan.identifiers, scan.reserved_used), (0, {}, {}))


# ---------------------------------------------------------------------------
# The substring boundary — the distinction that let a real leak through
# ---------------------------------------------------------------------------


class SubstringBoundaryTests(unittest.TestCase):
    """``find_tokens``: alphanumeric boundary, not hyphen-inclusive.

    Both directions are pinned because this exact distinction is why a real leak
    was previously missed: a hyphen-inclusive boundary read ``AUD-XGL-1010`` as an
    unrelated token and never reported the published ledger id.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _file(self, name: str, text: str) -> Path:
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_a_longer_identifier_with_a_trailing_digit_does_not_match(self) -> None:
        path = self._file("accounts.md", "The control account is XGL-10105 this quarter.")
        self.assertEqual(pilc.find_tokens([path], ["XGL-1010"]), {})

    def test_a_trailing_letter_also_blocks_the_match(self) -> None:
        path = self._file("accounts.md", "Sub-ledger XGL-1010A rolls up separately.")
        self.assertEqual(pilc.find_tokens([path], ["XGL-1010"]), {})

    def test_a_leading_alphanumeric_also_blocks_the_match(self) -> None:
        # This is what makes the reserved band work: a doc printing 'XEMP-4471'
        # does not collide with a corpus using 'EMP-4471'.
        path = self._file("accounts.md", "Worked example XEMP-4471 in the charter.")
        self.assertEqual(pilc.find_tokens([path], ["EMP-4471"]), {})

    def test_a_hyphen_composed_identifier_DOES_match(self) -> None:
        path = self._file("taxonomy.md", "The audit trail AUD-XGL-1010 records the posting.")
        self.assertEqual(pilc.find_tokens([path], ["XGL-1010"]), {"XGL-1010": {path}})

    def test_a_trailing_hyphen_segment_also_matches(self) -> None:
        path = self._file("taxonomy.md", "See XGL-1010-B for the reversal leg.")
        self.assertEqual(pilc.find_tokens([path], ["XGL-1010"]), {"XGL-1010": {path}})

    def test_longest_first_alternation_reports_the_composed_token(self) -> None:
        path = self._file("taxonomy.md", "The audit trail AUD-XGL-1010 records the posting.")
        hits = pilc.find_tokens([path], ["XGL-1010", "AUD-XGL-1010"])
        self.assertEqual(hits, {"AUD-XGL-1010": {path}})

    def test_ordinary_punctuation_is_a_boundary(self) -> None:
        path = self._file("notes.md", "Rows: (ZLED-4102), ZLED-4102. ZLED-4102;")
        self.assertEqual(pilc.find_tokens([path], ["ZLED-4102"]), {"ZLED-4102": {path}})

    def test_an_empty_token_set_matches_nothing_rather_than_everything(self) -> None:
        # Guard against the degenerate alternation: an empty pattern would match at
        # every position in every tracked file and manufacture findings from air.
        path = self._file("notes.md", "any text at all")
        self.assertEqual(pilc.find_tokens([path], []), {})

    def test_an_unreadable_path_is_skipped_not_raised(self) -> None:
        missing = self.dir / "does_not_exist.md"
        self.assertEqual(pilc.find_tokens([missing], ["ZLED-4102"]), {})


# ---------------------------------------------------------------------------
# The tracked-file side
# ---------------------------------------------------------------------------


@unittest.skipUnless(_HAS_GIT, "git is required to enumerate the tracked-file side")
class TrackedFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_tracked_files_are_enumerated_from_the_index(self) -> None:
        _init_repo(self.root)
        doc = _track(self.root, "docs/notes.md", "tracked\n")
        (self.root / "untracked.md").write_text("not in the index\n", encoding="utf-8")
        self.assertEqual(pilc.tracked_files(self.root), [doc])

    def test_a_non_git_directory_raises_rather_than_returning_nothing(self) -> None:
        with self.assertRaises(pilc.TrackedCorpusUnavailable):
            pilc.tracked_files(self.root)

    def test_an_empty_index_raises_too_because_an_empty_tracked_set_passes_vacuously(self) -> None:
        _init_repo(self.root)
        with self.assertRaises(pilc.TrackedCorpusUnavailable):
            pilc.tracked_files(self.root)

    def test_binary_suffixes_are_not_scanned(self) -> None:
        _init_repo(self.root)
        doc = _track(self.root, "docs/notes.md", "tracked\n")
        _track(self.root, "assets/diagram.png", f"payload {_LEAKY_ID}\n")
        _track(self.root, "assets/build.zip", f"payload {_LEAKY_ID}\n")
        self.assertEqual(pilc.tracked_files(self.root), [doc])

    def test_a_tracked_but_deleted_file_is_skipped(self) -> None:
        _init_repo(self.root)
        doc = _track(self.root, "docs/notes.md", "tracked\n")
        gone = _track(self.root, "docs/gone.md", f"payload {_LEAKY_ID}\n")
        gone.unlink()
        self.assertEqual(pilc.tracked_files(self.root), [doc])


# ---------------------------------------------------------------------------
# The sweep
# ---------------------------------------------------------------------------


@unittest.skipUnless(_HAS_GIT, "git is required to enumerate the tracked-file side")
class SweepTests(unittest.TestCase):
    """End-to-end: a synthetic repo, a synthetic pack, real ``git ls-files``."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.bench = self.root / "evals/benchmarks"
        _init_repo(self.root)
        self.addCleanup(self._tmp.cleanup)

    def _sweep(self) -> pilc.Sweep:
        return pilc.sweep(self.root, self.bench)

    # -- the core finding ---------------------------------------------------

    def test_a_prompt_identifier_in_a_tracked_doc_is_a_leak(self) -> None:
        _track(self.root, "docs/charter.md", f"Worked example: post against {_LEAKY_ID}.\n")
        _write_pack(self.bench, "zpack", [_case("ZLD-201")])
        result = self._sweep()
        leaks = _leaks(result.findings)
        self.assertEqual(len(leaks), 1, result.findings)
        self.assertIn(_LEAKY_ID, leaks[0])
        self.assertIn("zpack ZLD-201", leaks[0])  # which pack and which case
        self.assertIn("docs/charter.md", leaks[0])  # and where the anchor is public
        self.assertTrue(pilc.has_leaks(result.findings))

    def test_a_tracked_python_docstring_is_as_public_as_a_charter(self) -> None:
        # Nine of the twenty-eight original collisions were in src/ and tests/.
        # Restricting the scan to *.md would have found none of them.
        _track(self.root, "src/tool.py", f'"""Example: {_LEAKY_ID} is the ledger."""\n')
        _write_pack(self.bench, "zpack", [_case("ZLD-201")])
        leaks = _leaks(self._sweep().findings)
        self.assertTrue(any("src/tool.py" in f for f in leaks), leaks)

    def test_an_identifier_present_only_in_the_corpus_is_not_a_finding(self) -> None:
        _track(self.root, "docs/charter.md", "No identifiers in this charter at all.\n")
        _write_pack(self.bench, "zpack", [_case("ZLD-201")])
        result = self._sweep()
        self.assertEqual(result.findings, [])
        self.assertEqual(result.prompts_scanned, 1)
        self.assertEqual(result.identifiers_checked, 1)

    def test_a_binary_tracked_file_cannot_produce_a_finding(self) -> None:
        _track(self.root, "docs/charter.md", "nothing here\n")
        _track(self.root, "assets/diagram.png", f"payload {_LEAKY_ID}\n")
        _write_pack(self.bench, "zpack", [_case("ZLD-201")])
        self.assertEqual(self._sweep().findings, [])

    # -- the reserved illustration band, both directions --------------------

    def test_the_reserved_band_makes_a_tracked_worked_example_safe(self) -> None:
        # XEMP-4471 in a tracked doc is fine — even though the corpus next door
        # uses the same serial under a real prefix.
        _track(self.root, "docs/charter.md", "Worked example: adjust XEMP-4471 this cycle.\n")
        _write_pack(self.bench, "zpack", [_case("ZLD-201", "Adjust EMP-4471 this cycle.")])
        result = self._sweep()
        self.assertEqual(result.findings, [])
        self.assertEqual(result.prompts_scanned, 1)  # it did look; it found nothing

    def test_a_corpus_prompt_using_the_reserved_band_is_a_notice_even_when_untracked(self) -> None:
        # The inverse claim: the corpus has taken an identifier the docs are
        # entitled to print, so it is a finding on the CORPUS side regardless of
        # whether any doc has used it yet.
        _track(self.root, "docs/charter.md", "No identifiers in this charter at all.\n")
        _write_pack(self.bench, "zpack", [_case("ZLD-201", "Adjust XEMP-4471 this cycle.")])
        result = self._sweep()
        self.assertEqual(_leaks(result.findings), [])
        notices = _notices(result.findings)
        self.assertEqual(len(notices), 1, result.findings)
        self.assertIn("XEMP-4471", notices[0])
        self.assertIn("zpack", notices[0])
        self.assertIn("reserved", notices[0])

    def test_a_corpus_prompt_using_the_reserved_band_is_a_leak_once_a_doc_prints_it(self) -> None:
        _track(self.root, "docs/charter.md", "Worked example: adjust XEMP-4471 this cycle.\n")
        _write_pack(self.bench, "zpack", [_case("ZLD-201", "Adjust XEMP-4471 this cycle.")])
        result = self._sweep()
        leaks = _leaks(result.findings)
        self.assertEqual(len(leaks), 1, result.findings)
        self.assertIn("XEMP-4471", leaks[0])
        self.assertIn("re-identify the CORPUS", leaks[0])  # the remedy is corpus-side
        self.assertEqual(_notices(result.findings), [])  # reported once, not twice

    # -- exclusions by construction ----------------------------------------

    def test_published_vocabulary_shared_with_a_tracked_doc_is_not_a_leak(self) -> None:
        _track(
            self.root,
            "docs/taxonomy.md",
            "Failure mode AGB-FIN-004 is governed by policy ABP-07-A.\n",
        )
        _write_pack(
            self.bench,
            "zpack",
            [_case("ZLD-201", "Under AGB-FIN-004 and ABP-07-A, book the entry.")],
        )
        self.assertEqual(self._sweep().findings, [])

    def test_a_case_id_shared_with_a_tracked_report_is_not_a_leak(self) -> None:
        _track(self.root, "reports/summary.md", "Case ZLD-4102 scored breach=none.\n")
        _write_pack(self.bench, "zpack", [_case("ZLD-4102", "Per ZLD-4102, book the entry.")])
        self.assertEqual(self._sweep().findings, [])

    # -- the boundary, through the whole instrument -------------------------

    def test_the_boundary_rule_holds_end_to_end_in_both_directions(self) -> None:
        _track(self.root, "docs/near_miss.md", f"Account {_LEAKY_ID}9 is a different account.\n")
        _write_pack(self.bench, "zpack", [_case("ZLD-201")])
        self.assertEqual(self._sweep().findings, [])

        _track(self.root, "docs/composed.md", f"Audit trail AUD-{_LEAKY_ID} records it.\n")
        leaks = _leaks(self._sweep().findings)
        self.assertEqual(len(leaks), 1, leaks)
        self.assertIn("docs/composed.md", leaks[0])
        self.assertNotIn("near_miss", leaks[0])

    # -- corruption and coverage -------------------------------------------

    def test_a_corrupt_corpus_is_reported_not_raised(self) -> None:
        _track(self.root, "docs/charter.md", "nothing here\n")
        pack = _write_pack(self.bench, "zpack", [])
        (pack / "cases.jsonl").write_text('{"case_id": "ZLD-201", "kind"\n', encoding="utf-8")
        findings = self._sweep().findings
        self.assertTrue(any("unreadable" in f and "zpack" in f for f in findings), findings)
        self.assertTrue(pilc.has_leaks(findings))

    def test_a_corpus_whose_prompts_are_all_blank_is_a_finding_not_a_pass(self) -> None:
        _track(self.root, "docs/charter.md", "nothing here\n")
        _write_pack(self.bench, "zpack", [_case("ZLD-201", "  "), _case("ZLD-202", "")])
        findings = self._sweep().findings
        self.assertTrue(any("nothing was scanned" in f for f in findings), findings)
        self.assertTrue(pilc.has_leaks(findings))

    def test_a_corpus_file_that_is_present_but_empty_is_a_finding_not_a_pass(self) -> None:
        # The relative coverage rule, at its sharpest: the corpus is PRESENT, so
        # the summary will count this pack as swept — but zero prompts were read,
        # so "0 leaks" here means "nothing was looked at". Reporting that as green
        # is precisely the conflation this module exists to refuse.
        _track(self.root, "docs/charter.md", f"Worked example {_LEAKY_ID}.\n")
        pack = _write_pack(self.bench, "zpack", [])
        (pack / "cases.jsonl").write_text("", encoding="utf-8")
        result = self._sweep()
        self.assertEqual(result.prompts_scanned, 0)
        self.assertIn("zpack", [s.slug for s in result.scans])  # counted as swept...
        self.assertTrue(
            any("nothing was scanned" in f for f in result.findings), result.findings
        )  # ...so it must say the sweep was empty
        self.assertTrue(pilc.has_leaks(result.findings))

    def test_two_packs_sharing_a_leaked_identifier_are_both_named(self) -> None:
        _track(self.root, "docs/charter.md", f"Worked example {_LEAKY_ID}.\n")
        _write_pack(self.bench, "zpack", [_case("ZLD-201")])
        _write_pack(self.bench, "zpack_two", [_case("ZLT-301")])
        leaks = _leaks(self._sweep().findings)
        self.assertEqual(len(leaks), 1, leaks)
        self.assertIn("zpack ZLD-201", leaks[0])
        self.assertIn("zpack_two ZLT-301", leaks[0])


# ---------------------------------------------------------------------------
# Absence is reported, never silently green
# ---------------------------------------------------------------------------


@unittest.skipUnless(_HAS_GIT, "git is required to enumerate the tracked-file side")
class AbsenceReportingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.bench = self.root / "evals/benchmarks"
        self.addCleanup(self._tmp.cleanup)

    def test_a_clean_checkout_shaped_repo_is_green_AND_quiet_AND_names_what_it_skipped(self) -> None:
        # The shape of a public clone: charters committed, every corpus gitignored
        # and absent. No finding, no leak — and the summary still says which packs
        # were not checked, so "0 leaks" cannot be mistaken for "all clear".
        _init_repo(self.root)
        _write_pack(self.bench, "finance_redteam", None)
        _track(self.root, "evals/benchmarks/finance_redteam/METHODOLOGY.md", "public method\n")
        result = pilc.sweep(self.root, self.bench)
        self.assertEqual(result.findings, [])
        self.assertEqual((result.leaks, result.notices), (0, 0))
        self.assertEqual(result.scans, [])
        self.assertEqual(result.skipped, ["finance_redteam"])
        self.assertFalse(result.tracked_unavailable)
        summary = _summary(result)
        self.assertIn("no held-out corpus present", summary)
        self.assertIn("corpus absent (held out — not checked): finance_redteam", summary)

    def test_an_absent_corpus_is_skipped_by_name_while_a_present_one_is_swept(self) -> None:
        _init_repo(self.root)
        _track(self.root, "docs/charter.md", "nothing here\n")
        _write_pack(self.bench, "finance_redteam", None)
        _write_pack(self.bench, "zpack", [_case("ZLD-201")])
        result = pilc.sweep(self.root, self.bench)
        self.assertEqual([s.slug for s in result.scans], ["zpack"])
        self.assertEqual(result.skipped, ["finance_redteam"])
        summary = _summary(result)
        self.assertIn("1 pack(s) swept [zpack]", summary)
        self.assertIn("corpus absent (held out — not checked): finance_redteam", summary)

    def test_an_unavailable_tracked_set_skips_the_whole_check_with_a_visible_notice(self) -> None:
        # No git repo at all: the tracked side does not exist, so a comparison
        # against it would pass vacuously. That must be SKIPPED and said out loud.
        _write_pack(self.bench, "zpack", [_case("ZLD-201")])
        result = pilc.sweep(self.root, self.bench)
        self.assertTrue(result.tracked_unavailable)
        self.assertEqual(result.tracked_scanned, 0)
        notices = _notices(result.findings)
        self.assertEqual(len(notices), 1, result.findings)
        self.assertIn("SKIPPED, not passed", notices[0])
        self.assertEqual(_leaks(result.findings), [])
        summary = _summary(result)
        self.assertIn("SKIPPED", summary)
        self.assertIn("not a git checkout", summary)

    def test_an_unavailable_tracked_set_still_reports_what_it_managed_to_read(self) -> None:
        # The prompt side ran before the tracked side failed, so the skip notice is
        # accompanied by the traversal it did complete — not a blank result.
        _write_pack(self.bench, "zpack", [_case("ZLD-201")])
        result = pilc.sweep(self.root, self.bench)
        self.assertEqual([s.slug for s in result.scans], ["zpack"])
        self.assertEqual(result.prompts_scanned, 1)
        self.assertIn("1 pack(s) with a corpus: zpack", _summary(result))

    def test_an_empty_tracked_index_is_the_same_skip_not_a_pass(self) -> None:
        _init_repo(self.root)
        _write_pack(self.bench, "zpack", [_case("ZLD-201")])
        result = pilc.sweep(self.root, self.bench)
        self.assertTrue(result.tracked_unavailable)
        self.assertTrue(any("SKIPPED, not passed" in f for f in _notices(result.findings)))

    def test_the_summary_names_the_whole_traversal(self) -> None:
        _init_repo(self.root)
        _track(self.root, "docs/charter.md", "nothing here\n")
        _write_pack(self.bench, "zpack", [_case("ZLD-201"), _case("ZLD-202", "Reconcile ZBCR-8801.")])
        result = pilc.sweep(self.root, self.bench)
        summary = _summary(result)
        self.assertIn("1 pack(s) swept", summary)
        self.assertIn("2 prompt(s)", summary)
        self.assertIn("2 distinct identifier(s)", summary)
        self.assertIn(f"{result.tracked_scanned} tracked file(s)", summary)


class RelativeCoverageTests(unittest.TestCase):
    """Coverage assertions that hold in a clean public clone and in a full local
    checkout alike. No absolute floor: a test that asserted "at least N
    identifiers" against the real repository failed a clean clone once already."""

    def test_the_real_repository_sweep_is_internally_consistent(self) -> None:
        result = pilc.sweep(REPO_ROOT, REPO_ROOT / "evals/benchmarks")
        if result.tracked_unavailable:
            self.assertTrue(any("SKIPPED, not passed" in f for f in _notices(result.findings)))
            return
        # RELATIVE claims only: the tracked side exists, and any pack whose corpus
        # is present yielded something to scan. Both hold with zero packs present.
        self.assertGreater(result.tracked_scanned, 0)
        for scan in result.scans:
            self.assertGreater(scan.prompts, 0, scan.slug)
        self.assertEqual(
            result.prompts_scanned, sum(s.prompts for s in result.scans)
        )
        self.assertEqual(
            result.identifiers_checked,
            sum(len(s.identifiers) + len(s.reserved_used) for s in result.scans),
        )

    def test_every_discovered_pack_is_either_swept_or_named_as_skipped(self) -> None:
        # The property that makes absence legible: no pack may vanish silently
        # between discovery and the summary.
        import pack_conformance

        benchmarks = REPO_ROOT / "evals/benchmarks"
        discovered = {e.slug for e in pack_conformance.discover_packs(benchmarks)}
        result = pilc.sweep(REPO_ROOT, benchmarks)
        accounted = {s.slug for s in result.scans} | set(result.skipped)
        self.assertEqual(discovered - accounted, set())


# ---------------------------------------------------------------------------
# CLI: exit behaviour and the mode the summary claims
# ---------------------------------------------------------------------------


def _synthetic_leak_sweep() -> pilc.Sweep:
    """One leak, real shape, no filesystem — so exit-code tests are hermetic."""

    scan = pilc.CorpusScan("zpack", 3, {_LEAKY_ID: ["ZLD-201"]}, {})
    finding = pilc._finding(
        pilc.SEVERITY_LEAK,
        _LEAKY_ID,
        "held-out prompt identifier (zpack ZLD-201) appears verbatim in tracked file(s): docs/charter.md",
    )
    return pilc.Sweep([finding], [scan], ["finance_redteam"], 12, False)


class CliExitCodeTests(unittest.TestCase):
    def setUp(self) -> None:
        patcher = unittest.mock.patch.object(pilc, "sweep", return_value=_synthetic_leak_sweep())
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_the_default_run_is_blocking_on_a_leak(self) -> None:
        code, out, err = _run_cli([])
        self.assertEqual(code, 1)
        self.assertIn(f"IDENTIFIER-LEAK: [leak] {_LEAKY_ID}", err)
        self.assertIn("pack identifier leak (BLOCKING)", out)

    def test_advisory_exits_zero_on_the_very_same_finding(self) -> None:
        code, out, err = _run_cli(["--advisory"])
        self.assertEqual(code, 0)
        self.assertIn(f"IDENTIFIER-LEAK: [leak] {_LEAKY_ID}", err)  # still reported

    def test_the_summary_names_the_mode_it_actually_ran_in(self) -> None:
        # REGRESSION PIN: the summary once printed "BLOCKING" unconditionally,
        # including on the gate run that was ignoring its exit code. A summary that
        # can misreport its own authority is worse than no summary.
        _, blocking_out, _ = _run_cli([])
        _, advisory_out, _ = _run_cli(["--advisory"])
        self.assertIn("(BLOCKING)", blocking_out)
        self.assertNotIn("ADVISORY", blocking_out)
        self.assertIn("(ADVISORY)", advisory_out)
        self.assertNotIn("BLOCKING", advisory_out)

    def test_the_summary_reports_the_traversal_and_the_absent_corpora(self) -> None:
        _, out, _ = _run_cli(["--advisory"])
        self.assertIn("1 leak / 0 notice across 1 pack(s) swept [zpack]", out)
        self.assertIn("3 prompt(s), 1 distinct identifier(s) checked against 12 tracked file(s)", out)
        self.assertIn("corpus absent (held out — not checked): finance_redteam", out)

    def test_json_mode_carries_the_same_exit_semantics(self) -> None:
        code, out, _ = _run_cli(["--json"])
        self.assertEqual(code, 1)
        payload = json.loads(out)
        self.assertEqual(payload["packs_swept"], ["zpack"])
        self.assertEqual(payload["packs_corpus_absent"], ["finance_redteam"])
        self.assertEqual(payload["prompts_scanned"], 3)
        self.assertEqual(payload["identifiers_checked"], 1)
        self.assertEqual(payload["tracked_files_scanned"], 12)
        self.assertFalse(payload["tracked_unavailable"])
        self.assertTrue(pilc.has_leaks(payload["findings"]))
        self.assertEqual(_run_cli(["--json", "--advisory"])[0], 0)

    def test_pack_narrows_the_sweep_to_one_slug(self) -> None:
        code, out, _ = _run_cli(["--pack", "zpack", "--advisory"])
        self.assertEqual(code, 0)
        self.assertIn("1 pack(s) swept [zpack]", out)
        _, other_out, other_err = _run_cli(["--pack", "other_pack", "--advisory"])
        self.assertIn("no held-out corpus present", other_out)
        self.assertNotIn(_LEAKY_ID, other_err)


class CliCleanRunTests(unittest.TestCase):
    def test_a_clean_sweep_exits_zero_in_both_modes(self) -> None:
        clean = pilc.Sweep([], [], ["finance_redteam"], 42, False)
        with unittest.mock.patch.object(pilc, "sweep", return_value=clean):
            self.assertEqual(_run_cli([])[0], 0)
            self.assertEqual(_run_cli(["--advisory"])[0], 0)

    def test_an_unavailable_tracked_set_does_not_fail_the_blocking_run(self) -> None:
        # A skip is not a leak: the check refuses to claim a verdict, and refusing
        # is not the same as failing. The notice is what carries the information.
        notice = pilc._finding(pilc.SEVERITY_NOTICE, "instrument", "tracked-file set unavailable")
        skipped = pilc.Sweep([notice], [], [], 0, True)
        with unittest.mock.patch.object(pilc, "sweep", return_value=skipped):
            code, out, err = _run_cli([])
            self.assertEqual(code, 0)
            self.assertIn("SKIPPED", out)
            self.assertIn("IDENTIFIER-LEAK: [notice]", err)

    def test_the_real_repository_advisory_run_exits_zero(self) -> None:
        # Exercised against whatever is actually present locally. Deliberately does
        # NOT assert the absence of findings: in a full local checkout there may be
        # an outstanding leak awaiting a human decision, and in a clean clone there
        # is no corpus at all. Both must exit 0 under --advisory.
        code, out, _ = _run_cli(["--report-public", "--advisory"])
        self.assertEqual(code, 0)
        self.assertIn("pack identifier leak (ADVISORY)", out)


# ---------------------------------------------------------------------------
# Gate wiring
# ---------------------------------------------------------------------------


def _gate_commands() -> list[list[str]]:
    spec = importlib.util.spec_from_file_location("check_all_for_leak_test", CHECK_ALL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [
        command
        for _name, command in module.CHECKS
        if len(command) >= 2 and command[1] == "src/pack_identifier_leak_check.py"
    ]


class GateWiringTests(unittest.TestCase):
    def test_the_gate_registers_the_check_exactly_once_and_sweeps_every_pack(self) -> None:
        commands = _gate_commands()
        self.assertEqual(len(commands), 1, commands)
        self.assertIn("--report-public", commands[0])

    def test_the_printed_mode_matches_the_flags_the_gate_actually_passes(self) -> None:
        # The invariant, written so it survives the eventual flip to blocking: the
        # summary's mode word and the exit code must both follow the gate's own
        # argv. Adding or removing --advisory in check_all.py cannot desynchronise
        # what the run does from what it says it did.
        argv = _gate_commands()[0][2:]
        advisory = "--advisory" in argv
        with unittest.mock.patch.object(pilc, "sweep", return_value=_synthetic_leak_sweep()):
            code, out, _ = _run_cli(argv)
        if advisory:
            self.assertEqual(code, 0)
            self.assertIn("(ADVISORY)", out)
            self.assertNotIn("BLOCKING", out)
        else:
            self.assertEqual(code, 1)
            self.assertIn("(BLOCKING)", out)
            self.assertNotIn("ADVISORY", out)


if __name__ == "__main__":
    unittest.main()
