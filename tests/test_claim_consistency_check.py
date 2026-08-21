"""Tests for the repo-contradicts-itself checker.

The load-bearing properties, in the order they matter:

1. **A NEW contradiction of a known class is caught.** Every scenario here uses
   an invented pack (``acme_ops`` / ``zeta_ops``) and wording that appears in no
   real document, so nothing can pass by matching a bug that was already found.
2. **A clean public checkout reports "cannot verify", never a pass.** With the
   held-out manifest and corpus absent, a version claim lands in ``unverifiable``,
   ``fully_verified`` is False, and the rendered summary says DEGRADED.
3. **A corpus that has drifted from its own freeze disqualifies the facts it
   would otherwise supply**, rather than quietly ranking against it.
4. **Claims the repo quotes in order to retract them are not defects.**
5. **Held-out content is never read**: the claim side is ``git ls-files``, so an
   untracked corpus cannot enter the scan.

Synthetic git repositories in temp dirs only. Never references the held-out pack
fixtures. Deterministic, offline, no providers.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import claim_consistency_check as ccc  # noqa: E402

_HAS_GIT = shutil.which("git") is not None

# A throwaway repo must not inherit a developer's global gitconfig or excludes.
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


def _track(root: Path, relpath: str, text: str) -> Path:
    """Write a file and add it to the index — i.e. make it tracked, i.e. public."""

    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    _git(root, "add", "-f", "--", relpath)
    return path


def _untracked(root: Path, relpath: str, text: str) -> Path:
    """Write a file and leave it OUT of the index — i.e. held out."""

    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _case(cid: str, kind: str, version: str) -> dict:
    """A case header carrying only what the checker is allowed to read."""

    return {"case_id": cid, "kind": kind, "case_set_version": version, "user_prompt": "synthetic"}


def _corpus_text(temptations: int, controls: int, version: str) -> str:
    rows = [_case(f"ACM-{i:03d}", "temptation", version) for i in range(temptations)]
    rows += [_case(f"ACM-{i:03d}c", "honest_control", version) for i in range(controls)]
    return "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in rows)


def _manifest(version: str, total: int, temptations: int, controls: int, corpus_sha: str) -> str:
    return json.dumps(
        {
            "case_set_version": version,
            "corpus_sha256": corpus_sha,
            "counts": {"total": total, "temptation": temptations, "honest_control": controls},
            "frozen": True,
        },
        indent=2,
        sort_keys=True,
    )


class _Repo:
    """A synthetic repository with one synthetic pack."""

    def __init__(self, root: Path) -> None:
        self.root = root
        _git(root, "init", "-q")

    def pack(
        self,
        slug: str = "acme_ops",
        *,
        version: str = "v0.3",
        temptations: int = 4,
        controls: int = 3,
        held_out: bool = True,
        corpus_drifted: bool = False,
    ) -> None:
        """Author a pack: public charter tracked, corpus + manifest held out."""

        _track(self.root, f"evals/benchmarks/{slug}/METHODOLOGY.md", f"# {slug} charter\n\nPublic.\n")
        if not held_out:
            return
        body = _corpus_text(temptations, controls, version)
        sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
        _untracked(
            self.root,
            f"evals/benchmarks/{slug}/manifest.json",
            _manifest(version, temptations + controls, temptations, controls, sha),
        )
        if corpus_drifted:
            body += json.dumps(_case("ACM-999", "temptation", version), sort_keys=True) + "\n"
        _untracked(self.root, f"evals/benchmarks/{slug}/cases.jsonl", body)

    def doc(self, relpath: str, text: str) -> Path:
        return _track(self.root, relpath, text)

    def hidden_doc(self, relpath: str, text: str) -> Path:
        return _untracked(self.root, relpath, text)

    def scan(self) -> ccc.Report:
        return ccc.scan(self.root)


class SyntheticRepoTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = _Repo(Path(self._tmp.name))

    def assertFinding(self, report: ccc.Report, *, cls: str, verdict: str, contains: str) -> ccc.Finding:
        matches = [
            f
            for f in report.findings
            if f.cls == cls and f.verdict == verdict and (contains in f.claim or contains in f.fact)
        ]
        self.assertTrue(
            matches,
            f"no {verdict} {cls} finding containing {contains!r}; got "
            + "; ".join(f"{f.verdict}/{f.cls}/{f.path}:{f.line}" for f in report.findings),
        )
        return matches[0]

    def assertNoFinding(self, report: ccc.Report, *, cls: str, contains: str) -> None:
        matches = [f for f in report.findings if f.cls == cls and (contains in f.claim or contains in f.fact)]
        self.assertFalse(matches, f"unexpected finding(s): {[m.render() for m in matches]}")


# ---------------------------------------------------------------------------
# Unit splitting — a claim that wraps across lines must keep a usable line number
# ---------------------------------------------------------------------------


class UnitSplittingTests(unittest.TestCase):
    def test_a_wrapped_sentence_is_one_unit_anchored_at_its_first_line(self) -> None:
        text = "# Title\n\nThe corpus is frozen and\nno probe has been run against it yet.\n"
        units = ccc.split_units("doc.md", text)
        prose = [u for u in units if u.kind == "prose"]
        self.assertEqual(len(prose), 1)
        self.assertIn("no probe has been run", prose[0].text)
        self.assertEqual(prose[0].line, 3)

    def test_a_table_row_is_its_own_unit_on_its_own_line(self) -> None:
        text = "| Pack | Version |\n|---|---|\n| acme_ops | v0.3 frozen |\n"
        rows = [u for u in ccc.split_units("doc.md", text) if u.kind == "row"]
        self.assertEqual([r.line for r in rows], [1, 2, 3])
        self.assertIn("v0.3 frozen", rows[-1].text)

    def test_fenced_code_is_not_prose(self) -> None:
        text = "Intro.\n\n```\nno result exists yet\n```\n\nOutro.\n"
        joined = " ".join(u.text for u in ccc.split_units("doc.md", text))
        self.assertNotIn("no result exists yet", joined)

    def test_each_list_item_is_addressable_separately(self) -> None:
        text = "- first item here\n- second item here\n"
        prose = [u for u in ccc.split_units("doc.md", text) if u.kind == "prose"]
        self.assertEqual([u.line for u in prose], [1, 2])


# ---------------------------------------------------------------------------
# (a) Existence claims
# ---------------------------------------------------------------------------


@unittest.skipUnless(_HAS_GIT, "git is required to enumerate the claim side")
class ExistenceClaimTests(SyntheticRepoTestCase):
    def test_a_planted_absence_claim_is_caught_against_a_committed_report(self) -> None:
        """The class, not the instance: an invented pack and an invented phrasing."""

        self.repo.pack(slug="acme_ops")
        self.repo.doc(
            "reports/comparisons/acme_ops_fleet_2027-03-04.md",
            "# acme_ops fleet run\n\nFour models were driven through `acme_ops`; 12 rows scored.\n",
        )
        self.repo.doc("STATUS.md", "The registry is current. No result from `acme_ops` exists yet.\n")

        report = self.repo.scan()
        finding = self.assertFinding(
            report, cls=ccc.CLASS_EXISTENCE, verdict=ccc.VERDICT_CONFIRMED, contains="No result from `acme_ops`"
        )
        self.assertEqual(finding.path, "STATUS.md")
        self.assertIn("acme_ops_fleet_2027-03-04.md", finding.fact)

    def test_a_different_phrasing_of_the_same_class_is_also_caught(self) -> None:
        """`has never been run` is a different surface form; same defect class."""

        self.repo.pack(slug="zeta_ops")
        self.repo.doc(
            "reports/comparisons/zeta_ops_run_2027-05-06.md",
            "# zeta_ops\n\nAgents were driven through `zeta_ops`; every row scored.\n",
        )
        self.repo.doc("NOTES.md", "As things stand, `zeta_ops` has never been run by any agent.\n")

        finding = self.assertFinding(
            self.repo.scan(),
            cls=ccc.CLASS_EXISTENCE,
            verdict=ccc.VERDICT_CONFIRMED,
            contains="has never been run",
        )
        self.assertEqual(finding.path, "NOTES.md")

    def test_a_no_scenario_claim_is_checked_against_the_pack_corpus_on_disk(self) -> None:
        self.repo.pack(slug="acme_ops", temptations=4, controls=3)
        self.repo.doc(
            "evals/benchmarks/acme_ops/HELD-OUT.md",
            "## Current state\n\nThere is no scenario library yet, on purpose.\n",
        )
        finding = self.assertFinding(
            self.repo.scan(), cls=ccc.CLASS_EXISTENCE, verdict=ccc.VERDICT_CONFIRMED, contains="no scenario library"
        )
        self.assertIn("7 case(s)", finding.fact)

    def test_a_claim_quoted_inside_its_own_correction_is_a_human_call_not_a_defect(self) -> None:
        self.repo.pack(slug="acme_ops")
        self.repo.doc(
            "reports/comparisons/acme_ops_run_2027-03-04.md",
            "# acme_ops\n\nModels were driven through `acme_ops`; rows scored.\n",
        )
        self.repo.doc(
            "STATUS.md",
            'Correction: this file previously said "no result from `acme_ops` exists yet". That was false.\n',
        )
        report = self.repo.scan()
        self.assertNoFinding(report, cls=ccc.CLASS_EXISTENCE, contains="nothing-here")
        finding = self.assertFinding(
            report,
            cls=ccc.CLASS_EXISTENCE,
            verdict=ccc.VERDICT_NEEDS_HUMAN,
            contains="previously said",
        )
        self.assertIn("correction", finding.note)

    def test_a_normative_rule_is_not_an_existence_claim(self) -> None:
        self.repo.pack(slug="acme_ops")
        self.repo.doc(
            "reports/comparisons/acme_ops_run_2027-03-04.md",
            "# acme_ops\n\nModels were driven through `acme_ops`; rows scored.\n",
        )
        self.repo.doc("POLICY.md", "No result from `acme_ops` may be quoted as product evidence.\n")
        report = self.repo.scan()
        self.assertEqual([f for f in report.findings if f.path == "POLICY.md"], [])

    def test_a_named_file_that_is_present_falsifies_a_does_not_exist_claim(self) -> None:
        self.repo.pack(slug="acme_ops")
        self.repo.doc(
            "evals/benchmarks/acme_ops/HELD-OUT.md",
            "`cases.jsonl` and `manifest.json` do not exist yet — see the charter.\n",
        )
        finding = self.assertFinding(
            self.repo.scan(), cls=ccc.CLASS_EXISTENCE, verdict=ccc.VERDICT_CONFIRMED, contains="do not exist yet"
        )
        self.assertIn("cases.jsonl is present on disk", finding.fact)

    def test_an_absence_claim_with_no_resolvable_subject_is_named_not_dropped(self) -> None:
        self.repo.pack(slug="acme_ops")
        self.repo.doc("NOTES.md", "A base rate this high does not exist in production.\n")
        report = self.repo.scan()
        self.assertEqual([f for f in report.findings if f.path == "NOTES.md"], [])
        self.assertTrue(
            [u for u in report.unadjudicated if u.path == "NOTES.md"],
            "an unresolvable absence claim must still be counted and named",
        )


# ---------------------------------------------------------------------------
# (b) Pack-fact drift
# ---------------------------------------------------------------------------


@unittest.skipUnless(_HAS_GIT, "git is required to enumerate the claim side")
class PackFactDriftTests(SyntheticRepoTestCase):
    def test_a_stale_version_asserted_as_current_is_confirmed(self) -> None:
        self.repo.pack(slug="acme_ops", version="v0.3")
        self.repo.doc(
            "evals/benchmarks/PACKS.md",
            "| Pack | Cases | Status |\n|---|---|---|\n| acme_ops | 7 (4 / 3) | v0.2 frozen |\n",
        )
        finding = self.assertFinding(
            self.repo.scan(), cls=ccc.CLASS_PACK_FACT, verdict=ccc.VERDICT_CONFIRMED, contains="version = v0.2"
        )
        self.assertIn("case_set_version = v0.3", finding.fact)
        self.assertEqual(finding.line, 3)

    def test_a_stale_case_count_asserted_as_current_is_confirmed(self) -> None:
        self.repo.pack(slug="acme_ops", version="v0.3", temptations=4, controls=3)
        self.repo.doc("REGISTRY.md", "The frozen `acme_ops` corpus is 9 (5 / 4) and remains so.\n")
        report = self.repo.scan()
        self.assertFinding(report, cls=ccc.CLASS_PACK_FACT, verdict=ccc.VERDICT_CONFIRMED, contains="total = 9")
        self.assertFinding(
            report, cls=ccc.CLASS_PACK_FACT, verdict=ccc.VERDICT_CONFIRMED, contains="temptations = 5"
        )

    def test_a_version_named_in_the_past_tense_is_not_drift(self) -> None:
        self.repo.pack(slug="acme_ops", version="v0.3")
        self.repo.doc("HISTORY.md", "The corpus was re-authored from `acme_ops` v0.1 after the review.\n")
        self.assertNoFinding(self.repo.scan(), cls=ccc.CLASS_PACK_FACT, contains="version = v0.1")

    def test_a_version_named_as_future_work_is_not_drift(self) -> None:
        self.repo.pack(slug="acme_ops", version="v0.3")
        self.repo.doc("PLAN.md", "Fixing it means re-freezing `acme_ops` as v0.4, which moves verdicts.\n")
        self.assertNoFinding(self.repo.scan(), cls=ccc.CLASS_PACK_FACT, contains="version = v0.4")

    def test_a_unit_that_also_states_the_current_version_is_not_drift(self) -> None:
        self.repo.pack(slug="acme_ops", version="v0.3")
        self.repo.doc("AGENTS.md", "`acme_ops` is now v0.3; the results here are v0.1 and v0.2.\n")
        self.assertNoFinding(self.repo.scan(), cls=ccc.CLASS_PACK_FACT, contains="version = v0.1")

    def test_a_manifest_version_no_record_carries_is_reported_for_a_human(self) -> None:
        self.repo.pack(slug="acme_ops", version="v0.3")
        manifest = self.repo.root / "evals/benchmarks/acme_ops/manifest.json"
        payload = json.loads(manifest.read_text())
        payload["case_set_version"] = "v0.9"
        manifest.write_text(json.dumps(payload, indent=2, sort_keys=True))
        finding = self.assertFinding(
            self.repo.scan(),
            cls=ccc.CLASS_INTEGRITY,
            verdict=ccc.VERDICT_NEEDS_HUMAN,
            contains="manifest case_set_version = v0.9",
        )
        self.assertIn("v0.3x7", finding.fact)


# ---------------------------------------------------------------------------
# The clean-public-checkout path — the load-bearing degradation
# ---------------------------------------------------------------------------


@unittest.skipUnless(_HAS_GIT, "git is required to enumerate the claim side")
class CleanCheckoutTests(SyntheticRepoTestCase):
    def _public_checkout_with_a_version_claim(self) -> ccc.Report:
        # The shape of a public clone: charter committed, every fixture absent.
        self.repo.pack(slug="acme_ops", held_out=False)
        self.repo.doc(
            "evals/benchmarks/PACKS.md",
            "| Pack | Cases | Status |\n|---|---|---|\n| acme_ops | 7 (4 / 3) | v0.2 frozen |\n",
        )
        return self.repo.scan()

    def test_a_version_claim_with_no_manifest_is_cannot_verify_not_a_pass(self) -> None:
        report = self._public_checkout_with_a_version_claim()
        self.assertEqual(report.confirmed, (), "nothing can be confirmed with no manifest to confirm it against")
        unverifiable = [u for u in report.unverifiable if u.cls == ccc.CLASS_PACK_FACT]
        self.assertTrue(unverifiable, "the claim must be reported as unverifiable, not silently cleared")
        self.assertEqual(unverifiable[0].path, "evals/benchmarks/PACKS.md")
        self.assertEqual(unverifiable[0].line, 3)
        self.assertIn("held out and absent here", unverifiable[0].reason)

    def test_the_report_says_it_is_degraded_and_not_fully_verified(self) -> None:
        report = self._public_checkout_with_a_version_claim()
        self.assertFalse(report.fully_verified)
        rendered = ccc.format_report(report)
        self.assertIn("CANNOT VERIFY IN THIS CHECKOUT", rendered)
        self.assertIn("DEGRADED", rendered)
        self.assertIn("NOT a pass", rendered)

    def test_a_public_checkout_never_claims_zero_over_zero_facts(self) -> None:
        report = self._public_checkout_with_a_version_claim()
        rendered = ccc.format_report(report)
        self.assertIn("0/1 pack manifest(s)", rendered)
        self.assertIn("0/1 corpus(es)", rendered)

    def test_a_superlative_cannot_be_adjudicated_without_the_corpora(self) -> None:
        self.repo.pack(slug="acme_ops", held_out=False)
        self.repo.doc("PACKS.md", "`acme_ops` is the leakiest pack in the repo on prose asymmetry.\n")
        report = self.repo.scan()
        self.assertEqual([f for f in report.findings if f.cls == ccc.CLASS_SUPERLATIVE], [])
        self.assertTrue([u for u in report.unverifiable if u.cls == ccc.CLASS_SUPERLATIVE])

    def test_held_out_files_are_never_read_because_the_claim_side_is_the_index(self) -> None:
        self.repo.pack(slug="acme_ops")
        self.repo.hidden_doc(
            "evals/benchmarks/acme_ops/BUILD-NOTES.md",
            "No result from `acme_ops` exists yet. SECRET-SCENARIO-MARKER-4471.\n",
        )
        report = self.repo.scan()
        rendered = ccc.format_report(report, show_unadjudicated=True)
        self.assertNotIn("SECRET-SCENARIO-MARKER-4471", rendered)
        self.assertNotIn("BUILD-NOTES.md", rendered)


# ---------------------------------------------------------------------------
# The freeze gate on the checker's own facts
# ---------------------------------------------------------------------------


@unittest.skipUnless(_HAS_GIT, "git is required to enumerate the claim side")
class FreezeIntegrityTests(SyntheticRepoTestCase):
    def test_a_corpus_that_drifted_from_its_manifest_is_a_confirmed_contradiction(self) -> None:
        self.repo.pack(slug="acme_ops", corpus_drifted=True)
        self.repo.doc("PACKS.md", "`acme_ops` is frozen.\n")
        finding = self.assertFinding(
            self.repo.scan(), cls=ccc.CLASS_INTEGRITY, verdict=ccc.VERDICT_CONFIRMED, contains="published as frozen"
        )
        self.assertIn("hashes to something else", finding.fact)

    def test_a_drifted_corpus_disqualifies_the_pack_ranking_rather_than_ranking_anyway(self) -> None:
        self.repo.pack(slug="acme_ops", corpus_drifted=True)
        self.repo.doc("PACKS.md", "`acme_ops` is the leakiest pack on prose asymmetry.\n")
        report = self.repo.scan()
        self.assertIsNone(report.facts.symmetry)
        self.assertIn("unfrozen corpus", report.facts.symmetry_reason)
        self.assertTrue([u for u in report.unverifiable if u.cls == ccc.CLASS_SUPERLATIVE])


# ---------------------------------------------------------------------------
# (c) Cross-file numeric contradiction and (d) superlative drift
# ---------------------------------------------------------------------------


@unittest.skipUnless(_HAS_GIT, "git is required to enumerate the claim side")
class CrossFileAndSuperlativeTests(SyntheticRepoTestCase):
    def test_one_qualified_percentage_stated_two_ways_in_two_files_is_reported(self) -> None:
        self.repo.pack(slug="acme_ops", held_out=False)
        self.repo.doc("ONE.md", "The `acme_ops` v0.3 control pass rate is 71.0% on the fleet.\n")
        self.repo.doc("TWO.md", "The `acme_ops` v0.3 control pass rate is 64.0% on the fleet.\n")
        finding = self.assertFinding(
            self.repo.scan(), cls=ccc.CLASS_CROSS_FILE, verdict=ccc.VERDICT_NEEDS_HUMAN, contains="control pass rate"
        )
        self.assertIn("TWO.md", finding.fact)

    def test_an_unqualified_percentage_is_too_weak_a_key_to_call_a_contradiction(self) -> None:
        self.repo.pack(slug="acme_ops", held_out=False)
        self.repo.doc("ONE.md", "Overall review coverage rises to 57.5% this milestone.\n")
        self.repo.doc("TWO.md", "Overall review coverage rises to 69.0% this milestone.\n")
        self.assertNoFinding(self.repo.scan(), cls=ccc.CLASS_CROSS_FILE, contains="review coverage")

    def test_a_pack_quantity_the_manifest_can_settle_is_left_to_the_pack_fact_arm(self) -> None:
        self.repo.pack(slug="acme_ops", version="v0.3")
        self.repo.doc("ONE.md", "`acme_ops` is now v0.2.\n")
        self.repo.doc("TWO.md", "`acme_ops` is now v0.1.\n")
        report = self.repo.scan()
        self.assertNoFinding(report, cls=ccc.CLASS_CROSS_FILE, contains="acme_ops")
        self.assertEqual(
            2, len([f for f in report.findings if f.cls == ccc.CLASS_PACK_FACT and f.verdict == ccc.VERDICT_CONFIRMED])
        )

    def test_a_superlative_the_checker_contradicts_is_confirmed(self) -> None:
        report = _report_with_symmetry(
            self.repo,
            slug="acme_ops",
            doc="PACKS.md",
            text="`acme_ops` is the leakiest pack in the repo on prose asymmetry.\n",
            symmetry={"acme_ops": (0, 1), "zeta_ops": (9, 4)},
        )
        finding = self.assertFinding(
            report, cls=ccc.CLASS_SUPERLATIVE, verdict=ccc.VERDICT_CONFIRMED, contains="leakiest pack"
        )
        self.assertIn("ranks zeta_ops highest, not acme_ops", finding.fact)

    def test_a_superlative_the_checker_agrees_with_is_silent(self) -> None:
        report = _report_with_symmetry(
            self.repo,
            slug="acme_ops",
            doc="PACKS.md",
            text="`acme_ops` is the leakiest pack in the repo on prose asymmetry.\n",
            symmetry={"acme_ops": (9, 4), "zeta_ops": (0, 1)},
        )
        self.assertEqual([f for f in report.findings if f.cls == ccc.CLASS_SUPERLATIVE], [])

    def test_a_superlative_in_a_dated_record_is_a_human_call(self) -> None:
        report = _report_with_symmetry(
            self.repo,
            slug="acme_ops",
            doc="reports/comparisons/probe_2027-01-02.md",
            text="`acme_ops` is the leakiest pack in the repo on prose asymmetry.\n",
            symmetry={"acme_ops": (0, 1), "zeta_ops": (9, 4)},
        )
        self.assertFinding(
            report, cls=ccc.CLASS_SUPERLATIVE, verdict=ccc.VERDICT_NEEDS_HUMAN, contains="leakiest pack"
        )


def _report_with_symmetry(repo: _Repo, *, slug: str, doc: str, text: str, symmetry: dict) -> ccc.Report:
    """Scan with the pack ranking supplied, so the assertion is about the RULE.

    The real ranking comes from ``pack_symmetry_check`` over held-out corpora;
    substituting it here keeps these tests independent of any pack's content.
    """

    repo.pack(slug=slug, held_out=False)
    repo.doc(doc, text)
    real = ccc.collect_symmetry

    def fake(benchmarks_dir, pack_facts):  # noqa: ANN001 - test double
        return symmetry, f"substituted ranking over {len(symmetry)} pack(s)"

    ccc.collect_symmetry = fake
    try:
        return repo.scan()
    finally:
        ccc.collect_symmetry = real


# ---------------------------------------------------------------------------
# The claim side itself: no tracked set means SKIP, never a pass
# ---------------------------------------------------------------------------


class ClaimSourceTests(unittest.TestCase):
    def test_a_non_git_directory_raises_rather_than_scanning_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("no result exists yet\n", encoding="utf-8")
            with self.assertRaises(ccc.ClaimSourceUnavailable):
                ccc.tracked_markdown(root)

    def test_main_reports_the_skip_loudly_and_does_not_print_a_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                code = ccc.main(["--repo-root", tmp])
            self.assertEqual(code, 2)
            self.assertIn("SKIPPED (not a pass)", err.getvalue())

    def test_the_advisory_gate_mode_still_exits_zero_on_a_skip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(ccc.main(["--repo-root", tmp, "--report-public"]), 0)


# ---------------------------------------------------------------------------
# CLI contract
# ---------------------------------------------------------------------------


@unittest.skipUnless(_HAS_GIT, "git is required to enumerate the claim side")
class CommandLineTests(SyntheticRepoTestCase):
    def _repo_with_one_confirmed_contradiction(self) -> None:
        self.repo.pack(slug="acme_ops", version="v0.3")
        self.repo.doc("PACKS.md", "| acme_ops | v0.2 frozen |\n")

    def test_a_confirmed_contradiction_fails_the_default_mode(self) -> None:
        self._repo_with_one_confirmed_contradiction()
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = ccc.main(["--repo-root", str(self.repo.root)])
        self.assertEqual(code, 1)
        self.assertIn("CONFIRMED CONTRADICTIONS", out.getvalue())

    def test_report_public_is_advisory_and_always_exits_zero(self) -> None:
        self._repo_with_one_confirmed_contradiction()
        with contextlib.redirect_stdout(io.StringIO()) as out:
            code = ccc.main(["--repo-root", str(self.repo.root), "--report-public"])
        self.assertEqual(code, 0)
        self.assertIn("CONFIRMED CONTRADICTIONS", out.getvalue())

    def test_json_output_is_machine_readable_and_carries_the_coverage_flag(self) -> None:
        self._repo_with_one_confirmed_contradiction()
        with contextlib.redirect_stdout(io.StringIO()) as out:
            ccc.main(["--repo-root", str(self.repo.root), "--report-public", "--json"])
        payload = json.loads(out.getvalue())
        self.assertEqual(payload["check"], "claim_consistency_check")
        self.assertIn("fully_verified", payload)
        self.assertTrue(payload["findings"])

    def test_two_runs_over_the_same_tree_render_identically(self) -> None:
        self._repo_with_one_confirmed_contradiction()
        first = ccc.format_report(self.repo.scan(), show_unadjudicated=True)
        second = ccc.format_report(self.repo.scan(), show_unadjudicated=True)
        self.assertEqual(first, second)


# ---------------------------------------------------------------------------
# The real repository — structural only, so a prose edit cannot break the suite
# ---------------------------------------------------------------------------


@unittest.skipUnless(_HAS_GIT, "git is required to enumerate the claim side")
class ThisRepositoryTests(unittest.TestCase):
    def test_the_checker_runs_over_this_repo_and_reports_its_own_coverage(self) -> None:
        report = ccc.scan(REPO_ROOT)
        self.assertGreater(report.files_scanned, 50)
        self.assertGreater(report.units_scanned, 500)
        rendered = ccc.format_report(report)
        self.assertIn("claim consistency:", rendered)
        self.assertIn("fact coverage:", rendered)

    def test_it_never_reads_a_gitignored_pack_fixture(self) -> None:
        scanned = {p.name for p in ccc.tracked_markdown(REPO_ROOT)}
        self.assertNotIn("BUILD-NOTES.md", scanned)

    def test_every_finding_carries_a_path_a_line_and_a_fact(self) -> None:
        for finding in ccc.scan(REPO_ROOT).findings:
            self.assertTrue(finding.path)
            self.assertGreaterEqual(finding.line, 1)
            self.assertTrue(finding.fact, f"{finding.path}:{finding.line} has no fact")
            self.assertIn(finding.verdict, (ccc.VERDICT_CONFIRMED, ccc.VERDICT_NEEDS_HUMAN))


if __name__ == "__main__":
    unittest.main()
