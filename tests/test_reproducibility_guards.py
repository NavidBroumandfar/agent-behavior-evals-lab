"""Guards for the repository's reproducibility claims.

Three things are asserted here, all of them because they were once false:

1. **The published-number registry covers what the repo publishes.** An audit
   found it guarding 6 numbers while README.md and AGENTS.md between them state
   two dozen. A number nobody guards is a number that drifts.
2. **Every committed aggregate re-derives from its own parts.** Where the raw
   inputs are held out by policy, this arithmetic is the only check a stranger
   can run — so it must actually run, and actually fail when the aggregate is
   internally inconsistent.
3. **The judge verdict ledger closes the clean-clone gap without opening a
   leak.** The two headline judge numbers regenerated only from gitignored raw
   files; on a clean clone the generators silently produced the OPPOSITE
   finding at exit code 0. The ledger fixes that, and must never carry model
   prose.

Deterministic, offline, stdlib-only.
"""

from __future__ import annotations

import json
import sys
import tempfile
import re
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import judge_targeted_audit as jta
import judge_verdict_ledger as jvl
import judge_with_log_experiment as jwl
import published_number_check as pnc


class RegistryCoverageTests(unittest.TestCase):
    def test_registry_is_clean_at_head(self) -> None:
        self.assertEqual(pnc.check_published_numbers(), [])

    def test_registry_covers_both_public_briefings(self) -> None:
        covered = {doc for claim in pnc.PUBLISHED_CLAIMS for doc in claim["docs"]}
        self.assertIn("README.md", covered)
        self.assertIn(
            "AGENTS.md",
            covered,
            "AGENTS.md publishes the established-results table and was unguarded until 2026-08-21",
        )

    def test_registry_has_not_shrunk(self) -> None:
        # Ratchet, not a magic number: it went 6 -> 25 when the audit widened it.
        # Lowering this is allowed only alongside deleting a published claim.
        self.assertGreaterEqual(len(pnc.PUBLISHED_CLAIMS), 25)

    def test_every_claim_names_exactly_one_source_shape(self) -> None:
        for claim in pnc.PUBLISHED_CLAIMS:
            has_field = "field" in claim
            has_quote = bool(claim.get("artifact_quote"))
            self.assertTrue(
                has_field ^ has_quote,
                f"{claim['id']}: needs exactly one of field / artifact_quote",
            )

    def test_every_claim_id_is_unique(self) -> None:
        ids = [claim["id"] for claim in pnc.PUBLISHED_CLAIMS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_artifact_exists(self) -> None:
        for claim in pnc.PUBLISHED_CLAIMS:
            self.assertTrue(
                (REPO_ROOT / claim["artifact"]).exists(),
                f"{claim['id']}: artifact {claim['artifact']} is missing",
            )


class DottedFieldTests(unittest.TestCase):
    def test_resolves_a_nested_path(self) -> None:
        self.assertEqual(pnc._dotted({"a": {"b": {"c": 7}}}, "a.b.c"), 7)

    def test_names_the_hop_that_failed(self) -> None:
        with self.assertRaises(KeyError) as ctx:
            pnc._dotted({"a": {"b": {}}}, "a.b.c")
        self.assertEqual(ctx.exception.args[0], "a.b.c")

    def test_a_nested_claim_resolves_against_its_real_artifact(self) -> None:
        claim = next(c for c in pnc.PUBLISHED_CLAIMS if c["id"] == "judge_with_log_catch_rate")
        self.assertEqual(pnc._claim_value(claim), "98.2")


class MarkdownArtifactClaimTests(unittest.TestCase):
    def test_reads_a_number_the_generator_writes_only_to_markdown(self) -> None:
        claim = next(
            c for c in pnc.PUBLISHED_CLAIMS if c["id"] == "ground_truth_structural_on_evidence"
        )
        self.assertEqual(pnc._claim_value(claim), "8")

    def test_a_pattern_that_stops_matching_is_an_error_not_a_silent_pass(self) -> None:
        claim = {
            "id": "synthetic",
            "artifact": "README.md",
            "artifact_quote": r"this phrasing does not exist (\d+)",
        }
        with self.assertRaises(pnc.PublishedNumberError):
            pnc._claim_value(claim)

    def test_a_pattern_matching_two_different_values_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "report.md"
            artifact.write_text("rate 10.0% here and rate 20.0% there\n", encoding="utf-8")
            with mock.patch.object(pnc, "REPO_ROOT", Path(tmp)):
                claim = {
                    "id": "synthetic",
                    "artifact": "report.md",
                    "artifact_quote": r"rate (\d+\.\d)%",
                }
                with self.assertRaises(pnc.PublishedNumberError):
                    pnc._claim_value(claim)

    def test_a_markdown_claim_mismatch_reports_instead_of_crashing(self) -> None:
        """A claim with no ``field`` key once raised KeyError from the error path."""

        claim = {
            "id": "synthetic",
            "artifact": "README.md",
            "artifact_quote": r"catch \((\d+)/\d+\)",
        }
        self.assertIn("artifact_quote", pnc._source_label(claim))


class InternalConsistencyTests(unittest.TestCase):
    def test_every_committed_aggregate_re_derives_at_head(self) -> None:
        self.assertEqual(pnc.check_internal_consistency(), [])

    def test_a_broken_total_is_caught(self) -> None:
        report = json.loads(
            (REPO_ROOT / "reports/comparisons/scorer_judge_calibration.json").read_text()
        )
        report["agreement_count"] += 1
        with mock.patch.object(pnc, "_load_artifact", side_effect=self._patched(report)):
            problems = pnc.check_internal_consistency()
        self.assertTrue(
            any("agree+disagree vs judged_records" in p for p in problems),
            f"expected a summation problem, got {problems}",
        )

    def test_a_broken_rate_is_caught(self) -> None:
        report = json.loads(
            (REPO_ROOT / "reports/comparisons/blind_red_team_audit.json").read_text()
        )
        report["catch_rate"] = "44.4%"
        with mock.patch.object(pnc, "_load_artifact", side_effect=self._patched(report, "blind")):
            problems = pnc.check_internal_consistency()
        self.assertTrue(
            any("catch_rate" in p for p in problems), f"expected a rate problem, got {problems}"
        )

    @staticmethod
    def _patched(replacement: dict, marker: str = "scorer_judge_calibration"):
        real = pnc._load_artifact

        def loader(relative: str):
            if marker in relative:
                return replacement
            return real(relative)

        return loader

    def test_the_pack_difference_in_differences_re_derives(self) -> None:
        self.assertEqual(pnc._check_pack_delta_arithmetic(), [])


class JudgeVerdictLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = jvl.load_ledger()

    def test_the_ledger_is_committed(self) -> None:
        self.assertTrue(jvl.LEDGER_PATH.exists())

    def test_it_carries_no_model_prose(self) -> None:
        raw = jvl.LEDGER_PATH.read_text(encoding="utf-8")
        for withheld in jvl.WITHHELD_RAW_FIELDS:
            self.assertNotIn(
                f'"{withheld}"',
                raw,
                f"the ledger must never carry the judge's {withheld}",
            )

    def test_the_verdict_vocabulary_is_closed(self) -> None:
        for key, entry in self.ledger["runs"].items():
            for record_id, verdict in entry["verdicts"].items():
                self.assertIn(
                    verdict,
                    jvl.ALLOWED_VERDICTS,
                    f"{key}/{record_id}: verdict {verdict!r} outside the vocabulary",
                )

    def test_record_counts_match_the_verdict_maps(self) -> None:
        for key, entry in self.ledger["runs"].items():
            self.assertEqual(entry["record_count"], len(entry["verdicts"]), key)

    def test_it_is_bound_to_the_corpora_it_scored(self) -> None:
        import hashlib

        for relative, expected in self.ledger["corpora_sha256"].items():
            actual = hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, f"{relative} changed since the ledger was written")

    def test_it_covers_every_judge_run_both_audits_aggregate(self) -> None:
        needed = [(model, 1) for model in jwl.DEFAULT_AGGREGATE_JUDGES]
        needed += [(jta.FRONTIER_MODEL + "-jt", 1), (jta.FRONTIER_MODEL + "-jt", 2)]
        have = set(self.ledger["runs"])
        missing = [
            jvl.run_key(model, run)
            for model, run in needed
            if jvl.run_key(model, run) not in have
        ]
        # The two gateway-failed CLI judges are disclosed as missing in the
        # committed report; they are legitimately absent from the ledger too.
        disclosed = json.loads(
            (REPO_ROOT / "reports/comparisons/judge_with_log_audit.json").read_text()
        )["completeness"]["cli_judges_missing"]
        unexplained = [key for key in missing if key.split("|")[0] not in disclosed]
        self.assertEqual(unexplained, [], f"ledger is missing judge runs the audits score: {unexplained}")

    def test_raw_path_matches_the_experiment_module(self) -> None:
        """A rename in the experiment module must not silently empty the ledger."""

        for model, run in jvl.LEDGER_RUNS:
            self.assertEqual(jvl.raw_path(model, run), jwl.raw_path(model, run))

    def test_verification_is_clean_here(self) -> None:
        self.assertEqual(jvl.verify_against_raw(), [])

    def test_a_missing_ledger_yields_no_verdicts_rather_than_raising(self) -> None:
        with mock.patch.object(jvl, "LEDGER_PATH", REPO_ROOT / "docs/does-not-exist.json"):
            self.assertEqual(jvl.load_ledger_verdicts("frontier/claude-opus-4-8", 1), {})

    def test_exported_ledger_never_contains_a_withheld_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "judge_with_log_fake_model_run1.local.jsonl"
            raw.write_text(
                json.dumps(
                    {
                        "record_id": "SYNTH-001",
                        "verdict": "unsupported",
                        "confidence": "high",
                        "reason": "model prose that must not be published",
                        "model": "fake/model",
                        "run": 1,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(
                jvl.read_raw_verdicts(raw), {"SYNTH-001": "unsupported"}
            )

    def test_an_unknown_verdict_in_a_raw_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "judge_with_log_fake_model_run1.local.jsonl"
            raw.write_text(
                json.dumps({"record_id": "SYNTH-001", "verdict": "maybe"}) + "\n",
                encoding="utf-8",
            )
            with self.assertRaises(jvl.LedgerError):
                jvl.read_raw_verdicts(raw)


class CleanCloneRegenerationTests(unittest.TestCase):
    """The behaviour a due-diligence reviewer actually exercises."""

    def test_the_default_aggregate_panel_includes_the_headline_judge(self) -> None:
        self.assertIn(jwl.FRONTIER_JUDGE, jwl.DEFAULT_AGGREGATE_JUDGES)

    def test_verdicts_fall_back_to_the_ledger_when_raw_files_are_absent(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            with mock.patch.object(jwl, "RAW_DIR", Path(empty)):
                verdicts = jwl.load_verdicts(jwl.FRONTIER_JUDGE, 1)
        self.assertEqual(len(verdicts), 86)

    def test_an_empty_judge_panel_refuses_to_write_a_report(self) -> None:
        records = [
            {
                "evasion_id": "L1",
                "kind": "lying",
                "category": "safe_direct_response",
                "output_text": "",
                "tool_events": [],
            }
        ]
        with mock.patch.object(jwl, "load_verdicts", return_value={}):
            with self.assertRaises(jwl.JudgeExperimentError) as ctx:
                jwl.build_report(records, ["opencode-go/glm-5.2"], "sha", "sha")
        self.assertIn("gap_is_real", str(ctx.exception))

    def test_the_targeted_audit_refuses_an_empty_run(self) -> None:
        with mock.patch.object(jta, "load_verdicts", return_value={}):
            with self.assertRaises(jta.AuditError):
                jta.build_report([], "sha")


class ReproducibilityDocTests(unittest.TestCase):

    def test_readme_orphan_count_matches_the_page(self) -> None:
        """The README's pointer must not round the orphan count down.

        It said "one is listed" while the page's `## ORPHAN` heading carries two (443/141,
        and the 8/8 // 0/8 // 13/52 row). The neighbouring guard only asserts the strings
        "443" and "141" appear, so the second orphan could vanish from the page with every
        check still green — on the one page whose stated selling point is that nothing here
        rounds up.

        Counted from the `## ORPHAN` section rather than from prose, because prose is the
        thing that drifted.
        """

        page = (REPO_ROOT / "docs/reproducibility.md").read_text(encoding="utf-8")
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        after = page.split("\n## ORPHAN", 1)
        self.assertEqual(len(after), 2, "docs/reproducibility.md lost its '## ORPHAN' section")
        # the ORPHAN section runs to the next '## ' heading, or to the end of the page
        body = re.split(r"^## ", after[1], flags=re.MULTILINE)[0]
        count = len(re.findall(r"^### ", body, flags=re.MULTILINE))
        self.assertGreater(count, 0, "the ORPHAN section lists no numbers")

        words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}
        word = words.get(count, str(count))
        singular = count == 1
        expected = f"{word} is listed" if singular else f"**{word}** are listed"
        self.assertIn(
            expected,
            readme,
            f"the ORPHAN section lists {count} number(s); README must say "
            f"{expected!r} and does not",
        )

    DOC = REPO_ROOT / "docs/reproducibility.md"

    def test_the_doc_exists(self) -> None:
        self.assertTrue(self.DOC.exists(), "docs/reproducibility.md is the page a DD reviewer is handed")

    def test_it_classifies_every_number_it_lists(self) -> None:
        text = self.DOC.read_text(encoding="utf-8")
        for label in ("REPRODUCIBLE", "AUDITABLE", "ORPHAN"):
            self.assertIn(label, text)

    def test_it_names_the_orphan_rather_than_hiding_it(self) -> None:
        text = self.DOC.read_text(encoding="utf-8")
        self.assertIn("443", text)
        self.assertIn("141", text)

    def test_it_warns_that_regenerating_the_ground_truth_report_deletes_a_section(self) -> None:
        """The natural regeneration command removes three README-cited numbers."""

        text = self.DOC.read_text(encoding="utf-8")
        self.assertIn("hand-authored", text)


class GroundTruthEvidenceSliceTests(unittest.TestCase):
    """The 8/8 / 0/8 slice is hand-authored; assert that it stays present.

    ``ground_truth_labeling_kit summarize --md-out`` regenerates this report
    WITHOUT the analysis section that carries the table, so a routine
    regeneration silently deletes three numbers README cites. The published
    number check fails on that; this test states the invariant next to the fact.
    """

    REPORT = REPO_ROOT / "reports/comparisons/ground_truth_agreement_v2.md"

    def test_the_hand_authored_decomposition_is_still_present(self) -> None:
        text = self.REPORT.read_text(encoding="utf-8")
        self.assertIn("A destructive call is in the tool log", text)
        self.assertIn("8/8 (100%)", text)
        self.assertIn("13/52 (25%)", text)

    def test_no_committed_flag_reproduces_the_slice(self) -> None:
        """Documented negative result: if this ever passes, §13 can be closed."""

        labelled = {
            json.loads(line)["sample_id"]: json.loads(line)
            for line in (REPO_ROOT / "evals/labeling/disagreement_sample_v2.labeled.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        }
        source = {
            json.loads(line)["sample_id"]: json.loads(line)
            for line in (REPO_ROOT / "evals/labeling/disagreement_sample_v2.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        }
        candidates = [s for s in labelled if source[s].get("evidence_only_candidate")]
        agreeing = sum(
            1
            for s in candidates
            if ("pass" if labelled[s]["structural_verdict"]["passed"] else "fail")
            == labelled[s]["human_label"]
        )
        self.assertEqual(len(candidates), 8)
        self.assertNotEqual(
            agreeing,
            8,
            "evidence_only_candidate now reproduces the published 8/8 slice — "
            "update docs/reproducibility.md section 13 and reclassify it",
        )


if __name__ == "__main__":
    unittest.main()
