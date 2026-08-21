"""Verify every number this repo publishes still matches its committed artifact.

Numbers drift. A figure gets corrected in a report and survives in the README,
or a generator is re-run and the prose is not — and the first person to notice
is a skeptical evaluator reproducing the claim, which is the worst possible
moment. That has already happened here twice.

This check closes it structurally. Each published claim below names:

- the artifact that PRODUCES the number (a committed generator output),
- the field in that artifact,
- the documents that QUOTE it,
- ``quotes``: regexes with ONE capture group, matching every place the doc
  states this number, and
- ``retired``: values the claim used to have, which must no longer appear.

**Every capture must equal the artifact's current value** — presence-checking
alone is not enough, because a doc that states the number twice can drift in
one place and still contain the right value in the other. Wired into the repo
gate, so a number cannot silently drift again.

Three mechanisms, added 2026-08-21 when an audit found the registry covered
only 6 of the repository's published numbers:

- ``field`` accepts a **dotted path** (``decision.median_cli_judge_catch_rate``),
  so a number that lives inside a nested aggregate is checkable too.
- ``artifact_quote`` names a regex against a **Markdown artifact** instead of a
  JSON field, for numbers whose only home is a report file. Two sub-cases, and
  the difference matters:
  * generator output the generator writes only to Markdown (every pack run
    figure), and
  * a hand-authored analysis section inside an otherwise generated file. The
    ground-truth evidence slice (8/8, 0/8, 13/52) is the live example: those
    rows are **not** produced by ``ground_truth_labeling_kit summarize``, and
    re-running it over the same tracked labels **deletes them**. Guarding them
    this way is deliberate — a regeneration that silently drops three
    README-cited numbers now fails the gate instead of passing quietly.
- ``check_internal_consistency`` re-derives each committed aggregate from its
  own parts — a rate against its numerator and denominator, a total against its
  components, a difference-in-differences against the two differences it came
  from. That is what makes an **auditable** number auditable rather than merely
  asserted: the raw inputs may be held out, but the arithmetic on the published
  aggregate is checkable by anyone. See ``docs/reproducibility.md`` for which
  numbers are reproducible from a clean clone and which are only auditable.

Deterministic and standard-library only.

Exit codes:
    0 - every published number matches its artifact
    1 - a number is stale, missing, or a retired value survives
    2 - usage or input error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from statistics import median
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

# Published claims. Add a row when a number reaches a public document; move the
# old value into `retired` when it changes.
PUBLISHED_CLAIMS: tuple[dict[str, Any], ...] = (
    {
        "id": "self_authored_catch_rate",
        "artifact": "reports/comparisons/verifier_evasion_audit.json",
        "field": "catch_rate",
        "docs": ("README.md",),
        "quotes": (r"(\d+\.\d)% catch on the \*\*self-authored\*\*", r"\((\d+\.\d)% on the corpus its own author wrote"),
        "retired": ("91.7%", "92.9%", "93.2%", "93.5%", "97.8%"),
    },
    {
        "id": "blind_catch_rate",
        "artifact": "reports/comparisons/blind_red_team_audit.json",
        "field": "catch_rate",
        "docs": ("README.md",),
        "quotes": (r"\*\*(\d+\.\d)% catch \(\d+/\d+\)", r"it catches \*\*(\d+\.\d)%\*\*"),
        "retired": (),
    },
    {
        "id": "blind_lying_records",
        "artifact": "reports/comparisons/blind_red_team_audit.json",
        "field": "lying_records",
        "docs": ("README.md",),
        "quotes": (r"catch \(\d+/(\d+)\)",),
        "retired": (),
    },
    {
        "id": "keyword_judge_agreement",
        "artifact": "reports/comparisons/scorer_judge_calibration.json",
        "field": "agreement_rate",
        "docs": ("README.md",),
        "quotes": (r"(\d+\.\d)% agreement across 6 local models", r"(\d+\.\d)% judge agreement over 700"),
        "retired": ("55.1%",),
    },
    {
        "id": "keyword_false_alarms",
        "artifact": "reports/comparisons/scorer_judge_calibration.json",
        "field": "scorer_failed_judge_passed",
        "docs": ("README.md",),
        "quotes": (r"over-strict by (\d+) false alarms",),
        "retired": ("290",),
    },
    {
        "id": "fleet_structural_agreement",
        "artifact": "reports/comparisons/sandbox_fleet_scorer_judge_calibration.json",
        "field": "agreement_rate",
        "docs": ("README.md",),
        "quotes": (r"(\d+\.\d)% agreement across 8 framework",),
        "retired": ("69.7%",),
    },
    # ---- widened 2026-08-21: the six rows above left most published numbers
    # unguarded. Everything below is a number a reader can find in README.md or
    # AGENTS.md that had no drift protection at all.
    {
        "id": "keyword_judge_misses",
        "artifact": "reports/comparisons/scorer_judge_calibration.json",
        "field": "scorer_passed_judge_failed",
        "docs": ("README.md",),
        "quotes": (r"vs (\d+) misses",),
        "retired": (),
    },
    {
        "id": "keyword_judged_records",
        "artifact": "reports/comparisons/scorer_judge_calibration.json",
        "field": "judged_records",
        "docs": ("README.md",),
        "quotes": (r"(\d+) model records\]", r"judge agreement over (\d+)\s+records"),
        "retired": (),
    },
    {
        "id": "fleet_judged_records",
        "artifact": "reports/comparisons/sandbox_fleet_scorer_judge_calibration.json",
        "field": "judged_records",
        "docs": ("README.md",),
        "quotes": (r"(\d+) real-agent records\]",),
        "retired": (),
    },
    {
        "id": "fleet_evidence_only_catches",
        "artifact": "reports/comparisons/sandbox_fleet_scorer_judge_calibration.json",
        "field": "structural_catch_analysis.evidence_only_catches",
        "docs": ("README.md",),
        "quotes": (r"including (\d+) evidence-only",),
        "retired": (),
    },
    {
        "id": "blind_caught_count",
        "artifact": "reports/comparisons/blind_red_team_audit.json",
        "field": "caught",
        "docs": ("README.md",),
        "quotes": (r"catch \((\d+)/\d+\)",),
        "retired": (),
    },
    {
        "id": "ground_truth_records",
        "artifact": "reports/comparisons/ground_truth_agreement_v2.json",
        "field": "records",
        "docs": ("README.md",),
        "quotes": (
            r"contested records, n=(\d+)\]",
            r"— (\d+) records where the deterministic",
        ),
        "retired": (),
    },
    # The evidence-slice figures (8/8, 0/8, 13/52) are HAND-AUTHORED analysis
    # inside reports/comparisons/ground_truth_agreement_v2.md, not generator
    # output: `ground_truth_labeling_kit summarize` does not compute them, and
    # re-running it deletes the whole section. The slice definition ("a
    # destructive call is in the tool log") is not encoded anywhere in the repo
    # and does not reproduce from `evidence_only_candidate` (5/8, 3/8) or from
    # `is_destructive_event` (n=6). See docs/reproducibility.md. Guarded here so
    # a regeneration cannot quietly remove three numbers README cites.
    {
        "id": "ground_truth_structural_on_evidence",
        "artifact": "reports/comparisons/ground_truth_agreement_v2.md",
        "artifact_quote": r"\| \*\*(\d+)/8 \(100%\)\*\*",
        "docs": ("README.md",),
        "quotes": (r"matched the human (\d+)/8",),
        "retired": (),
    },
    {
        "id": "ground_truth_evidence_slice_size",
        "artifact": "reports/comparisons/ground_truth_agreement_v2.md",
        "artifact_quote": r"\*\* \| \*\*0/(\d+) \(0%\)\*\*",
        "docs": ("README.md",),
        "quotes": (r"and the judge 0/(\d+)\*\*",),
        "retired": (),
    },
    {
        "id": "ground_truth_keyword_on_no_evidence",
        "artifact": "reports/comparisons/ground_truth_agreement_v2.md",
        "artifact_quote": r"keyword rubric only \| \d+ \| (\d+)/52",
        "docs": ("README.md",),
        "quotes": (r"over-strict and lost (\d+)/52",),
        "retired": (),
    },
    # ---- AGENTS.md: the "established results" table was entirely unguarded.
    {
        "id": "agents_blind_catch_rate",
        "artifact": "reports/comparisons/blind_red_team_audit.json",
        "field": "catch_rate",
        "docs": ("AGENTS.md",),
        "quotes": (r"deterministic structural checker \| (\d+\.\d)% catch",),
        "retired": (),
    },
    {
        "id": "judge_with_log_catch_rate",
        "artifact": "reports/comparisons/judge_with_log_audit.json",
        "field": "decision.median_cli_judge_catch_rate",
        "docs": ("AGENTS.md",),
        "quotes": (r"\*\*with tool-log access\*\* \| ~(\d+\.\d)% catch",),
        "retired": (),
    },
    {
        "id": "judge_targeted_catch_rate",
        "artifact": "reports/comparisons/judge_targeted_audit.json",
        "field": "frontier_run1.catch_rate",
        "docs": ("AGENTS.md",),
        "quotes": (r"\| (\d+\.\d)% catch — no meaningful degradation",),
        "retired": (),
    },
    # ---- Pack results. Raw runs are held out by policy, so these are auditable
    # rather than reproducible; the committed pack report is still the artifact
    # AGENTS.md must not drift from.
    {
        "id": "finance_a4_trajectories",
        "artifact": "evals/benchmarks/finance_redteam/reports/A4-baseline-v0.5-2026-07-26.md",
        "artifact_quote": r"\*\*(\d+)/159 trajectories completed",
        "docs": ("AGENTS.md",),
        "quotes": (r"\| (\d+)/159 trajectories",),
        "retired": (),
    },
    {
        "id": "finance_a4_provoking_temptations",
        "artifact": "evals/benchmarks/finance_redteam/reports/A4-baseline-v0.5-2026-07-26.md",
        "artifact_quote": r"\*\*(\d+) of \d+ temptations\*\*",
        "docs": ("AGENTS.md",),
        "quotes": (r"(\d+) of \d+ temptations drove",),
        "retired": (),
    },
    {
        "id": "finance_b05_pre_rate",
        "artifact": "evals/benchmarks/finance_redteam/reports/B05-delta-v0.6-2026-07-26.md",
        "artifact_quote": r"= \*\*(\d+\.\d)%\*\* \| \d+/\d+ =",
        "docs": ("AGENTS.md",),
        "quotes": (r"violation rate (\d+\.\d)% →",),
        "retired": (),
    },
    {
        "id": "finance_b05_post_rate",
        "artifact": "evals/benchmarks/finance_redteam/reports/B05-delta-v0.6-2026-07-26.md",
        "artifact_quote": (
            r"\*\*Retrofitted \(\d+ cases\)\*\* \| \d+/\d+ = \*\*\d+\.\d%\*\* "
            r"\| \d+/\d+ = \*\*(\d+\.\d)%\*\*"
        ),
        "docs": ("AGENTS.md",),
        "quotes": (r"→ (\d+\.\d)% on retrofitted",),
        "retired": (),
    },
    {
        "id": "finance_b05_control_delta",
        "artifact": "evals/benchmarks/finance_redteam/reports/B05-delta-v0.6-2026-07-26.md",
        "artifact_quote": r"\| Unchanged \(\d+ cases\) \|[^|]+\|[^|]+\| \+(\d+\.\d) pts \|",
        "docs": ("AGENTS.md",),
        "quotes": (r"vs \+(\d+\.\d)pp on \d+ unchanged controls",),
        "retired": (),
    },
    {
        "id": "finance_b05_difference_in_differences",
        "artifact": "evals/benchmarks/finance_redteam/reports/B05-delta-v0.6-2026-07-26.md",
        "artifact_quote": r"\*\*Difference-in-differences: \+(\d+\.\d) points\.\*\*",
        "docs": ("AGENTS.md",),
        "quotes": (r"difference-in-differences \+(\d+\.\d) points",),
        "retired": (),
    },
    {
        "id": "finance_b05_noise_floor",
        "artifact": "evals/benchmarks/finance_redteam/reports/B05-delta-v0.6-2026-07-26.md",
        "artifact_quote": r"\*\*(\d+\.\d)% of unchanged temptation",
        "docs": ("AGENTS.md",),
        "quotes": (r"noise floor of (\d+\.\d)%",),
        "retired": (),
    },
)

# The blind corpus is frozen: its hash must match the manifest recorded before
# any fix, or the pre/post-fix comparison is meaningless.
FROZEN_CORPORA: tuple[dict[str, str], ...] = (
    {
        "corpus": "evals/adversarial/blind_red_team_cases.jsonl",
        "manifest": "evals/adversarial/blind_red_team_manifest.json",
        "manifest_field": "corpus_sha256",
    },
)


class PublishedNumberError(Exception):
    """A published number no longer matches its artifact."""


# Aggregates whose raw inputs are held out by policy cannot be re-run by a
# stranger. What a stranger CAN do is check that the committed aggregate is
# arithmetically consistent with its own parts — that a rate matches its
# numerator over its denominator, that components sum to the total, that a
# difference-in-differences is the difference of the two differences reported
# beside it. That is the whole content of the word "auditable" in
# docs/reproducibility.md, so it is enforced rather than asserted.
#
# Tolerance: rates are stored rounded to 1dp while some derived figures
# (Youden's J) are computed from the unrounded values, so a re-derivation can
# legitimately land 0.1 away. Anything larger is drift.
RATE_TOLERANCE = 0.15


def _load_artifact(relative: str) -> dict[str, Any]:
    path = REPO_ROOT / relative
    if not path.exists():
        raise PublishedNumberError(f"artifact missing: {relative}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PublishedNumberError(f"{relative}: invalid JSON: {exc.msg}") from exc


def _artifact_text(relative: str) -> str:
    path = REPO_ROOT / relative
    if not path.exists():
        raise PublishedNumberError(f"artifact missing: {relative}")
    return path.read_text(encoding="utf-8")


def _dotted(artifact: dict[str, Any], field: str) -> Any:
    """Resolve ``a.b.c`` inside a nested aggregate. Raises when any hop is absent."""

    node: Any = artifact
    walked: list[str] = []
    for part in field.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(".".join(walked + [part]))
        node = node[part]
        walked.append(part)
    return node


def _source_label(claim: dict[str, Any]) -> str:
    """Human-readable 'where this number comes from', for both claim shapes."""

    if claim.get("artifact_quote"):
        return f"{claim['artifact']} (matched by artifact_quote)"
    return f"{claim['artifact']}:{claim['field']}"


def _claim_value(claim: dict[str, Any]) -> str:
    """The current value of a claim, from a JSON field or a Markdown artifact.

    Exactly one of ``field`` / ``artifact_quote`` must be set. A Markdown
    artifact is still a *generator output*, not prose someone typed: the
    numbers reached for this way are the ones their generator writes only into
    the report, never into a JSON field.
    """

    relative = claim["artifact"]
    quote = claim.get("artifact_quote")
    if quote:
        matches = re.findall(quote, _artifact_text(relative))
        if not matches:
            raise PublishedNumberError(
                f"{claim['id']}: artifact_quote {quote!r} matched nothing in {relative} — "
                "the generated report changed shape, update the claim registry"
            )
        distinct = {str(m) for m in matches}
        if len(distinct) > 1:
            raise PublishedNumberError(
                f"{claim['id']}: artifact_quote {quote!r} matched several different values "
                f"in {relative}: {sorted(distinct)} — tighten the pattern"
            )
        return str(matches[0])
    artifact = _load_artifact(relative)
    try:
        return str(_dotted(artifact, claim["field"]))
    except KeyError as exc:
        raise PublishedNumberError(
            f"{claim['id']}: field {claim['field']!r} not in {relative} (missing at {exc.args[0]!r})"
        ) from exc


def _corpus_sha256(relative: str) -> str:
    import hashlib

    path = REPO_ROOT / relative
    if not path.exists():
        raise PublishedNumberError(f"corpus missing: {relative}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_published_numbers() -> list[str]:
    """Return a list of problems; empty means every published number is current."""

    problems: list[str] = []
    doc_cache: dict[str, str] = {}

    def doc_text(name: str) -> str:
        if name not in doc_cache:
            path = REPO_ROOT / name
            doc_cache[name] = path.read_text(encoding="utf-8") if path.exists() else ""
            if not doc_cache[name]:
                problems.append(f"document missing or empty: {name}")
        return doc_cache[name]

    for claim in PUBLISHED_CLAIMS:
        try:
            current = _claim_value(claim)
        except PublishedNumberError as exc:
            problems.append(str(exc))
            continue
        for doc in claim["docs"]:
            text = doc_text(doc)
            if not text:
                continue
            quotes = claim.get("quotes", ())
            if not quotes:
                if current not in text:
                    problems.append(
                        f"{claim['id']}: {doc} does not quote the current value {current!r} "
                        f"from {_source_label(claim)}"
                    )
            else:
                found_any = False
                for pattern in quotes:
                    for match in re.finditer(pattern, text):
                        found_any = True
                        stated = match.group(1)
                        if stated.rstrip("%") != current.rstrip("%"):
                            problems.append(
                                f"{claim['id']}: {doc} states {stated!r} but "
                                f"{_source_label(claim)} is {current!r} "
                                f"(context: {match.group(0)[:60]!r})"
                            )
                if not found_any:
                    problems.append(
                        f"{claim['id']}: {doc} contains no recognizable statement of this number "
                        f"(expected one of {quotes}) — prose changed shape, update the claim registry"
                    )
            for stale in claim["retired"]:
                if stale in text:
                    problems.append(
                        f"{claim['id']}: {doc} still contains the retired value {stale!r} "
                        f"(current is {current!r})"
                    )

    for frozen in FROZEN_CORPORA:
        try:
            manifest = _load_artifact(frozen["manifest"])
            actual = _corpus_sha256(frozen["corpus"])
        except PublishedNumberError as exc:
            problems.append(str(exc))
            continue
        expected = str(manifest.get(frozen["manifest_field"], ""))
        if actual != expected:
            problems.append(
                f"frozen corpus {frozen['corpus']} changed after freeze "
                f"(manifest {expected[:12]}..., actual {actual[:12]}...) — "
                "pre/post-fix comparisons against it are no longer valid"
            )

    return problems


def _rate(numerator: float, denominator: float) -> float:
    return (numerator / denominator * 100) if denominator else 0.0


def _pct(value: Any) -> float:
    return float(str(value).rstrip("%"))


def _close(actual: float, stated: Any, label: str, problems: list[str]) -> None:
    if abs(actual - _pct(stated)) > RATE_TOLERANCE:
        problems.append(f"{label}: re-derived {actual:.1f} but the artifact states {stated}")


def _equal(actual: Any, stated: Any, label: str, problems: list[str]) -> None:
    if actual != stated:
        problems.append(f"{label}: re-derived {actual!r} but the artifact states {stated!r}")


def check_internal_consistency() -> list[str]:
    """Re-derive each committed aggregate from the parts it publishes beside it."""

    problems: list[str] = []

    for relative in (
        "reports/comparisons/scorer_judge_calibration.json",
        "reports/comparisons/sandbox_fleet_scorer_judge_calibration.json",
    ):
        try:
            report = _load_artifact(relative)
        except PublishedNumberError as exc:
            problems.append(str(exc))
            continue
        name = Path(relative).stem
        parts = (
            report["agreement_count"]
            + report["scorer_failed_judge_passed"]
            + report["scorer_passed_judge_failed"]
        )
        _equal(parts, report["judged_records"], f"{name}: agree+disagree vs judged_records", problems)
        _close(
            _rate(report["agreement_count"], report["judged_records"]),
            report["agreement_rate"],
            f"{name}: agreement_rate",
            problems,
        )

    for relative in (
        "reports/comparisons/blind_red_team_audit.json",
        "reports/comparisons/verifier_evasion_audit.json",
    ):
        try:
            report = _load_artifact(relative)
        except PublishedNumberError as exc:
            problems.append(str(exc))
            continue
        name = Path(relative).stem
        _equal(
            report["lying_records"] + report["honest_twins"],
            report["records"],
            f"{name}: lying+twins vs records",
            problems,
        )
        _close(
            _rate(report["caught"], report["lying_records"]),
            report["catch_rate"],
            f"{name}: catch_rate",
            problems,
        )
        _equal(
            len(report["missed_records"]),
            report["lying_records"] - report["caught"],
            f"{name}: named misses vs lying-caught",
            problems,
        )
        _close(
            _rate(report["twin_false_positives"], report["honest_twins"]),
            report["twin_false_positive_rate"],
            f"{name}: twin_false_positive_rate",
            problems,
        )

    try:
        gt = _load_artifact("reports/comparisons/ground_truth_agreement_v2.json")
    except PublishedNumberError as exc:
        problems.append(str(exc))
    else:
        _equal(len(gt["per_record"]), gt["records"], "ground_truth_v2: per_record vs records", problems)
        for side in ("structural", "judge"):
            agree = sum(1 for row in gt["per_record"] if row[f"{side}_agrees_with_human"])
            _equal(agree, gt[f"{side}_agree_count"], f"ground_truth_v2: {side}_agree_count", problems)
            _close(
                _rate(gt[f"{side}_agree_count"], gt["records"]) / 100,
                gt[f"{side}_vs_human_agreement"],
                f"ground_truth_v2: {side}_vs_human_agreement",
                problems,
            )

    try:
        jwl = _load_artifact("reports/comparisons/judge_with_log_audit.json")
    except PublishedNumberError as exc:
        problems.append(str(exc))
    else:
        for model, row in jwl["judges"].items():
            for run_key in ("scores_run1", "scores_run2"):
                scores = row.get(run_key)
                if not scores:
                    continue
                label = f"judge_with_log[{model}/{run_key}]"
                _close(
                    _rate(scores["lying_caught"], scores["lying_scored"]),
                    scores["catch_rate"],
                    f"{label}: catch_rate",
                    problems,
                )
                _equal(
                    scores["lying_scored"] + scores["lying_parse_errors"],
                    jwl["lying_records"],
                    f"{label}: lying scored+errors vs corpus",
                    problems,
                )
                _equal(
                    scores["twins_scored"] + scores["twin_parse_errors"],
                    jwl["honest_twins"],
                    f"{label}: twins scored+errors vs corpus",
                    problems,
                )
                _equal(
                    len(scores["missed_record_ids"]),
                    scores["lying_scored"] - scores["lying_caught"],
                    f"{label}: named misses",
                    problems,
                )
                _close(
                    scores["catch_rate"] - scores["twin_false_positive_rate"],
                    scores["youden_j"],
                    f"{label}: youden_j",
                    problems,
                )
        cli_rates = [
            jwl["judges"][m]["scores_run1"]["catch_rate"]
            for m in jwl["completeness"]["cli_judges_with_run1"]
        ]
        if cli_rates:
            _close(
                float(median(cli_rates)),
                jwl["decision"]["median_cli_judge_catch_rate"],
                "judge_with_log: median_cli_judge_catch_rate",
                problems,
            )

    try:
        jt = _load_artifact("reports/comparisons/judge_targeted_audit.json")
    except PublishedNumberError as exc:
        problems.append(str(exc))
    else:
        _equal(
            jt["scored_lying"] + jt["scored_twins"],
            jt["scored_records"],
            "judge_targeted: lying+twins vs scored_records",
            problems,
        )
        _close(
            jt["frontier_run1"]["catch_rate"] - jt["decision"]["blind_corpus_comparison"],
            jt["decision"]["delta_vs_blind_corpus"],
            "judge_targeted: delta_vs_blind_corpus",
            problems,
        )
        per_lens_caught = sum(lens["caught"] for lens in jt["frontier_per_lens_run1"].values())
        _equal(
            per_lens_caught,
            jt["frontier_run1"]["lying_caught"],
            "judge_targeted: per-lens catches vs total",
            problems,
        )

    problems.extend(_check_pack_delta_arithmetic())
    return problems


_B05_ROW_RE = re.compile(
    r"\| (?:\*\*)?(Retrofitted|Unchanged) \(\d+ cases\)(?:\*\*)? "
    r"\| (\d+)/(\d+) = (?:\*\*)?(\d+\.\d)%(?:\*\*)? "
    r"\| (\d+)/(\d+) = (?:\*\*)?(\d+\.\d)%(?:\*\*)? "
    r"\| (?:\*\*)?\+(\d+\.\d) pts"
)


def _check_pack_delta_arithmetic() -> list[str]:
    """The B-05 difference-in-differences, re-derived from its own table.

    The underlying run is held out (raw trajectories are gitignored), so this
    is the only check a stranger can run on +29.2 — and it is a real one: each
    published rate must equal its own numerator over its own denominator, each
    arm delta must equal the difference of its two rates, and the headline DiD
    must equal the difference of the two arm deltas.
    """

    relative = "evals/benchmarks/finance_redteam/reports/B05-delta-v0.6-2026-07-26.md"
    problems: list[str] = []
    try:
        text = _artifact_text(relative)
    except PublishedNumberError as exc:
        return [str(exc)]

    rows = {match[0]: match[1:] for match in _B05_ROW_RE.findall(text)}
    for arm in ("Retrofitted", "Unchanged"):
        if arm not in rows:
            problems.append(f"B05: no '{arm}' rate row found — the report changed shape")
    if problems:
        return problems

    deltas: dict[str, float] = {}
    for arm, (num_a, den_a, rate_a, num_b, den_b, rate_b, delta) in rows.items():
        _close(_rate(int(num_a), int(den_a)), rate_a, f"B05[{arm}]: v0.5 rate", problems)
        _close(_rate(int(num_b), int(den_b)), rate_b, f"B05[{arm}]: v0.6 rate", problems)
        _close(float(rate_b) - float(rate_a), delta, f"B05[{arm}]: arm delta", problems)
        deltas[arm] = float(delta)

    stated = re.search(r"Difference-in-differences: \+(\d+\.\d) points", text)
    if not stated:
        problems.append("B05: no difference-in-differences statement found")
    else:
        _close(
            deltas["Retrofitted"] - deltas["Unchanged"],
            stated.group(1),
            "B05: difference-in-differences",
            problems,
        )
    return problems


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify published numbers match their committed artifacts.")
    parser.add_argument("--self-check", action="store_true", help="Run the check (default).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    parse_args(sys.argv[1:] if argv is None else argv)
    try:
        problems = check_published_numbers()
        problems.extend(check_internal_consistency())
    except PublishedNumberError as exc:
        print(f"published number check error: {exc}", file=sys.stderr)
        return 2
    if problems:
        print("published number check FAILED:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print(
        f"published number check passed: {len(PUBLISHED_CLAIMS)} claims match their artifacts; "
        "every committed aggregate re-derives from its own parts; frozen corpora intact"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
