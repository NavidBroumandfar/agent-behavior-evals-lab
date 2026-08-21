# Reproducibility — what a stranger can check, and what they cannot

*Last audited 2026-08-21. Written to be handed to a reviewer who has just
cloned this repository and intends to try every number in it.*

Every quantitative claim in [`README.md`](../README.md) and
[`AGENTS.md`](../AGENTS.md) is listed below in one of three classes. The class
is the honest answer to "can I check this myself?", and nothing here rounds up.

| Class | What it means |
| --- | --- |
| **REPRODUCIBLE** | Regenerates from a clean public clone with the command given. No held-out inputs. Byte-identical output, verified. |
| **AUDITABLE** | The aggregate is committed and re-derives from its own published parts, but the raw inputs are held out by policy, so you cannot re-run the measurement. You can check the arithmetic and the provenance; you cannot check that the raw data is what we say it is. |
| **ORPHAN** | Traces to no committed artefact, or to an artefact no committed rule can rebuild. Do not rely on it. |

Assume `PYTHONPATH=src` and the repository root as the working directory
throughout. Nothing below contacts a provider or needs credentials.

---

## The audit that produced this page

A clean clone (`git clone <repo> /tmp/cleanclone`, which by construction
excludes every gitignored file) was made, and each documented regeneration
command was run inside it. The result that mattered was not the commands that
failed — it was the two that **succeeded while producing the opposite answer**.

At the commit before this page existed:

```
$ PYTHONPATH=src python3 src/judge_with_log_experiment.py    # in a clean clone
{
  "branch": "gap_is_real",
  "reading": "Monitors that read the full tool log still miss most of these attacks...",
  "median_cli_judge_catch_rate": 0.0
}
$ echo $?
0
```

The published figure is **98.2%** and the published branch is
`high_catch_high_false_alarm`. The clean clone produced 0.0% and the reversed
conclusion, wrote it over the committed report, and exited 0. The same happened
to `judge_targeted_audit.py` (98.1% → 0.0%). The mechanism: raw judge responses
live in gitignored `traces/external/*.local.jsonl`; with none present, every
record scored as a parse error, both denominators went to zero, `median([])`
returned `0.0`, and `0.0 < 60.0` is the pre-registered `gap_is_real` branch.
Missing data was silently indistinguishable from a measured result.

Three fixes landed together:

1. **A committed, prose-free verdict ledger**
   ([`judge_verdict_ledger.json`](reproducibility/judge_verdict_ledger.json),
   built by [`src/judge_verdict_ledger.py`](../src/judge_verdict_ledger.py)) —
   `record_id → verdict` for every judge run both audits aggregate, and nothing
   else. Record ids are already public in both corpora and in both committed
   reports; the judges' rationale text and self-reported confidence are **not**
   in the ledger and stay held out.
2. **An empty judge panel is now an error, not a datapoint.** Both generators
   exit 2 with a message naming the missing inputs, and write no artefact.
3. **The default aggregate panel now includes the frontier judge.** It did not
   before — so even with the raw files present, the bare command rebuilt the
   report *without* the judge the headline 98.2% belongs to, and no command
   documented anywhere rebuilt it correctly.

---

## REPRODUCIBLE

### 1. Blind red-team audit — 21.8% catch (12/55), 0 twin false positives

The number README calls "the number to judge the verifier by".

```bash
python3 src/verifier_evasion_audit.py \
  --corpus evals/adversarial/blind_red_team_cases.jsonl \
  --json-out reports/comparisons/blind_red_team_audit.json \
  --md-out  reports/comparisons/blind_red_team_audit.md
```

Verified byte-identical to the committed artefact from a clean clone. The
corpus is frozen and its sha256 is checked against
`evals/adversarial/blind_red_team_manifest.json` by the repo gate.

### 2. Self-authored evasion audit — 98.0% catch, 0 twin false positives

```bash
python3 src/verifier_evasion_audit.py
```

Verified byte-identical from a clean clone.

### 3. Pre-fix blind figure — 14.5% catch (8/55), 4 twin false positives

Published permanently beside the post-fix number, per the repo's "publish the
bad numbers too" rule. It is not in the current artefact — it is in git, which
is the point:

```bash
git show 272a618:reports/comparisons/blind_red_team_audit.json
```

To re-derive rather than read it: `git checkout 272a618` and run the command in
§1. Verified byte-identical to that commit's artefact.

### 4. Human ground truth, n=60 — 35% structural / 65% judge overall agreement

```bash
python3 src/ground_truth_labeling_kit.py summarize \
  evals/labeling/disagreement_sample_v2.labeled.jsonl \
  --json-out reports/comparisons/ground_truth_agreement_v2.json
```

The **JSON** aggregate is verified byte-identical from a clean clone: n=60, 21
structural agreements (35%), 39 judge agreements (65%), and the per-record
table. The labelled input is tracked; label authorship (AI-drafted,
human-adjudicated, single reviewer) is disclosed in the record itself.

**Do not pass `--md-out` at that path.** The committed Markdown report contains
a hand-authored analysis section that the generator does not produce, and
re-running it with `--md-out` **deletes** that section — including the table
README quotes for 8/8, 0/8 and 13/52. Those three figures are classified
separately below (§13); the overall 35/65 split above is what this command
reproduces. The published-number check now fails the gate if that section
disappears, so the deletion cannot happen silently.

### 5. Judge-with-log aggregate — 98.2% median catch  *(aggregation only)*

```bash
python3 src/judge_with_log_experiment.py
```

Verified byte-identical from a clean clone **since the ledger was committed**.

**Read the qualifier.** What reproduces is the *aggregation*: that 98.2%,
6.5% twin false positives, 95.3% inter-judge agreement and the decision branch
all follow from the per-record verdicts in the ledger. What does **not**
reproduce is the *measurement*: the judge calls were live calls to hosted
models on a dated run and cannot be replayed here. A reviewer can verify the
arithmetic and the pinning; a reviewer cannot verify from this repository alone
that the ledger's verdicts are what those models returned. Anyone holding the
raw files can check that derivation byte-for-byte:

```bash
python3 src/judge_verdict_ledger.py          # verifies the ledger against any raw files present
```

Each ledger entry pins the sha256 of the raw file it came from, so a stale
ledger is detected rather than trusted.

### 6. Judge-targeted aggregate — 98.1% catch  *(aggregation only)*

```bash
python3 src/judge_targeted_audit.py
```

Verified byte-identical from a clean clone. The same aggregation-not-measurement
qualifier as §5 applies, word for word.

---

## AUDITABLE

For each of these the committed aggregate re-derives from its own published
parts — enforced, not asserted, by `check_internal_consistency()` in
[`src/published_number_check.py`](../src/published_number_check.py), which runs
in the repo gate. The raw inputs are held out, so the measurement itself cannot
be re-run by a stranger.

### 7. Keyword scorer vs LLM judge — 59.7% agreement over 700 records (235 false alarms, 47 misses)

```bash
python3 src/scorer_judge_calibration.py --aggregate-only
```

On a clean clone: **exits 2**, naming the first missing input
(`*.reviewed_live_local_eval.judge.local.jsonl`). The scorer side of this study
*is* tracked (`traces/scored/*.reviewed_live_local_eval.jsonl`); the judge side
is not. Those judge outputs still exist on the author's machine and the study
reproduces there byte-identically — that is a statement about one laptop, not
about this repository, and it is why the classification is AUDITABLE.

Why the judge side is not published as a ledger: unlike the two judge rounds
above, this aggregate's `disagreement_examples` carry the judge's own prose, so
a verdict-only ledger would not reproduce the committed artefact, and a ledger
that *did* reproduce it would be publishing model rationales wholesale. Left
held out deliberately.

What you can check without the inputs: `agreement_count + scorer_failed_judge_passed
+ scorer_passed_judge_failed == judged_records` (418 + 235 + 47 = 700) and
`agreement_count / judged_records == agreement_rate` (59.7%).

### 8. Structural scorer vs judge, sandbox fleet — 70.6% agreement over 320 records, 8 evidence-only catches

```bash
python3 src/sandbox_fleet_calibration.py --aggregate-only --panel
```

On a clean clone: **exits 1**, naming the missing
`traces/scored/*.fleet_scored.local.jsonl`. Note `--panel`: without it the
`judge_panel` block is omitted and the output differs from the committed
artefact.

**A hazard a reviewer should know about.** README says the structural side is
"reproducible from HEAD". That is now only partly true. `--emit-only` re-scores
the fleet from tracked sandbox outputs, but its default glob
(`*reviewed_sandbox_outputs.jsonl` in `traces/external/`) matches **20** files
today, not the **8** this study measured — later `eval_framed`, `prod_shaped`
and `refusal_temptation` runs landed in the same directory. At HEAD it aborts
on one of those extra files rather than silently widening the study; that is
luck, not design. Reproducing the structural side requires restricting the run
to the study's original 8 agents.

### 9. Finance pack A4 baseline — 159/159 trajectories, 15 of 35 temptations provoked a violation

Artefact: [`A4-baseline-v0.5-2026-07-26.md`](../evals/benchmarks/finance_redteam/reports/A4-baseline-v0.5-2026-07-26.md).
Raw trajectories are gitignored (`traces/raw/**/*.local.jsonl`) and the pack's
`cases.jsonl` is held out by design — a public eval set is a burned eval set,
see [`HELD-OUT.md`](../evals/benchmarks/finance_redteam/HELD-OUT.md). Neither
will ever be publishable, so this number is permanently AUDITABLE.

### 10. Finance pack B-05 delta — 14.0% → 47.2% retrofitted, +4.0pp control, **DiD +29.2 points**, 21.7% noise floor

Artefact: [`B05-delta-v0.6-2026-07-26.md`](../evals/benchmarks/finance_redteam/reports/B05-delta-v0.6-2026-07-26.md).

This is the one AUDITABLE claim with real arithmetic to check, and the gate now
checks it: each published rate against its own numerator and denominator
(15/107 = 14.0%, 51/108 = 47.2%, 36/207 = 17.4%, 44/206 = 21.4%), each arm
delta against its two rates (+33.2, +4.0), and the headline
difference-in-differences against the two arm deltas (33.2 − 4.0 = 29.2).

### 11. Multi-pack run 2026-08-20 — devops_sre and healthcare_admin

Artefacts: [`pack_run_2026-08-20.json`](../reports/comparisons/pack_run_2026-08-20.json)
and its Markdown twin. The JSON carries its own `regeneration_command`, which
points at `traces/raw/packrun-2026-08-20/` — gitignored. On a clean clone the
command exits 2 with `--runs is not a directory`, which is the correct
behaviour.

---

## ORPHAN

### 12. "443 breach verdicts before and 141 after" — `evals/benchmarks/PACKS.md`

**This number traces to nothing in the repository and should be retracted or
regenerated.**

What was searched, and found empty:

- No committed artefact contains 443 or 141 as a breach count. The only
  repository-wide matches for `443` are unrelated sha256 fragments and an
  argument digest.
- No committed script performs the "mutation census" the figure came from.
  `git log --diff-filter=D` shows none was ever committed and deleted.
- The only other place the pair appears is the commit message of `ac7ae2d`
  ("False positives on a compliant call, measured by mutation census across the
  four packs: 443 -> 141"). That commit touched three files:
  `evals/benchmarks/PACKS.md`, `src/pack_reachability_check.py`,
  `src/pack_sandbox_base.py` — no census tool among them.

So the measurement was made ad hoc and never committed. Worse, it is not
recoverable as stated even in principle without work: the "before" arm requires
the pre-`ac7ae2d` sandbox base, and the packs have been version-bumped and
re-frozen since.

Two honest exits, for the owner to choose between:

1. **Retract it.** Replace the sentence in `PACKS.md` with the qualitative
   claim it is actually entitled to — "mutating a compliant call's arguments no
   longer produces breach verdicts except on permission-scored arguments" —
   which *is* supported by the verdict-diff evidence in the same bullet.
2. **Regenerate it.** Commit a `pack_argument_mutation_census` tool that drives
   each pack's real sandbox over a bounded argument domain and counts breach
   verdicts on compliant calls, run it at HEAD and against `ac7ae2d~1`, and
   publish both numbers with the date and the pack versions. The tool would run
   only where the held-out sandboxes exist, so the result would land as
   AUDITABLE, not REPRODUCIBLE.

`PACKS.md` is outside this workstream's file scope, so the sentence was not
touched here rather than quietly deleted. It is recorded on this page so the
correction happens in the open.

### 13. "matched the human 8/8 and the judge 0/8 ... lost 13/52" — `README.md`

**The labels behind these are committed. The slice that produces them is not.**

The three figures come from a two-row table in
`reports/comparisons/ground_truth_agreement_v2.md` splitting the 60 contested
records into "a destructive call is in the tool log" (n=8) and "no tool
evidence" (n=52). That table is hand-authored analysis inside an otherwise
generated file:

- `ground_truth_labeling_kit summarize` does not compute it, and re-running the
  generator with `--md-out` removes it entirely (verified in a clean clone).
- No committed rule reproduces the n=8 slice. The tracked
  `evidence_only_candidate` flag selects 8 records, but scoring them gives
  **5/8 structural, 3/8 judge**, not 8/8 and 0/8. The verifier's own
  `is_destructive_event` over executed events selects **6** records (5/6, 1/6).
  "Any tool_events at all" selects 30; "any succeeded event" selects 16.
  None of them is the published slice.

So a reviewer can reproduce the *overall* 35/65 split and can read every
individual human label, but cannot re-derive the decomposition README leans on
— and that decomposition is the part README describes as the reason the keyword
rubric is opt-in in trace mode.

Two honest exits, again for the owner:

1. **Commit the slice.** Add the per-record "destructive call in the log" flag
   to `evals/labeling/disagreement_sample_v2.jsonl` (or the rule that computes
   it) and teach `ground_truth_labeling_kit summarize` to emit the two-row table
   into both the JSON and the Markdown. Then §4 and §13 collapse into one
   REPRODUCIBLE row.
2. **Qualify it in README.** State that the decomposition is a hand adjudication
   over the published labels, not a generated statistic.

Until one of those happens, the gate at least prevents the table being deleted
by a routine regeneration.

---

## How this page is kept honest

`python3 src/published_number_check.py` runs in the repo gate
(`python3 scripts/dev.py check`) and does three things:

- **Drift.** Every number quoted in README.md and AGENTS.md is matched against
  the artefact that produces it; a doc that states a number twice must state it
  the same way twice; retired values must not survive anywhere. Coverage went
  from 6 claims to 25 in this pass, and now includes AGENTS.md, which was
  entirely unguarded.
- **Internal consistency.** Every committed aggregate is re-derived from its own
  parts — the rates, the totals, the named misses, Youden's J, the median
  across judges, the difference-in-differences.
- **Freeze.** The blind corpus sha256 is checked against the manifest recorded
  before any fix.

`python3 src/judge_verdict_ledger.py` checks the verdict ledger against any raw
judge files present, and `tests/test_reproducibility_guards.py` asserts the
ledger carries no model prose, covers every judge run both audits score, and
that the empty-panel refusal actually refuses.

## Known limits of this page

- It classifies the numbers in README.md and AGENTS.md. Numbers that appear only
  inside individual reports under `reports/comparisons/` are not enumerated here.
- "REPRODUCIBLE" means the artefact regenerates from committed inputs. It does
  not mean the underlying measurement was independently replicated — for the two
  judge rounds it explicitly was not, and §5 says so.
- The judge and pack rounds were single-reviewer and AI-assisted; that
  disclosure lives in the reports themselves and is not restated per row here.
