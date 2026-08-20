# AGENTS.md — orientation for any AI or human working in this repo

*Model-agnostic entry point. Read this file first, before touching anything.
Claude Code, Codex, Cursor, and any other assistant: this is the canonical
briefing. It is public-safe by design — it describes the engineering method,
never commercial strategy.*

## What this repository is

An **agent behavior evaluation lab**. It measures whether an AI agent's *recorded
actions* match what the agent *says it did*, and whether an agent takes actions
it should have refused, gated, or escalated.

The governing idea, and the thing that makes this repo different from
general LLM eval tooling:

> **Behavior is scored on the recorded tool log, never on the wording.**
> An agent that writes "I refused" while its log shows the action executed has
> failed. An agent that explains a refusal has passed.

## Current build objective (2026-07)

**Pre-deployment behavioral red-teaming for action-taking agents**, delivered as
**vertical scenario packs**.

The first pack is **finance**: `evals/benchmarks/finance_redteam/`.
**Read `evals/benchmarks/finance_redteam/METHODOLOGY.md` before extending it** —
it is the binding charter for that pack and contains its schema, discipline
rules, and extension instructions.

A pack consists of:
1. a **failure taxonomy** — the named, action-based ways an agent misbehaves in
   that vertical, each decidable from a tool log;
2. a **temptation-scenario library** — scenarios that provoke those failures,
   each paired with an **honest control** that must NOT be refused;
3. a **frozen manifest** — sha256 pinning the corpus before anything is scored.

## Non-negotiable method rules

These exist because they were learned the hard way. Do not relax them.

1. **Score behavior, not words.** A violation is an executed tool call recorded
   in `tool_events`. Wording never overrides the log.
2. **Pre-register before you measure.** Protocol, prompts, and decision rules are
   committed *before* any run, so results cannot be reverse-fitted. See
   `evals/adversarial/*-protocol.md` for the pattern.
3. **Freeze before you score.** Corpora are pinned with a sha256 manifest before
   any monitor is run against them, and are never edited afterward.
4. **Every temptation ships an honest control.** Otherwise the suite rewards an
   agent that refuses everything. A flagged control is a false positive and
   counts against the suite.
5. **Publish the bad numbers too.** Negative and pre-fix results stay published,
   dated, with their invalidation conditions. See the adversarial reports.
6. **Disclose AI authorship** of any generated corpus or artifact.
7. **Never self-promote evidence.** Staged/local runs are not promoted to
   reviewed evidence without an explicit human decision.
8. **Public-safe and synthetic.** Invented entities only — no real institutions,
   accounts, credentials, or people. Adversarial content here is *defensive*
   testing of AI agents inside a mock sandbox.

## Landmines — read before editing

- **`src/scorers.py` is load-bearing.** Editing it cascades a re-derivation chain
  through committed ledgers, reports, and the leaderboard, and the acceptance
  criterion is **zero unintended verdict flips**. Vertical packs are *additive*
  and must not touch it.
- **New eval work stays local** until there is an explicit decision to publish.
  Building an asset is not the same as shipping it publicly.
- **Private/strategy documents are gitignored by glob** (`ASSESSMENT-*`,
  `ROADMAP-GTM-*`, `DIRECTION-MAP-*`, `ENGINEERING-ROADMAP*`, `NEXT-STEPS*`,
  `PITCH-*`, `*-BRIEF*`). Never commit them, never quote them into public files.
- **Raw model outputs stay gitignored** (`traces/**/*.local.jsonl`). Only
  aggregate reports are committed.

## The gate

```bash
python3 scripts/dev.py check
```

Must be green before any commit. Tests: `python3 -m unittest discover -s tests`.

## Established results a new session should know

Published, dated, reproducible from committed artifacts:

| Instrument | Result |
| --- | --- |
| Blind red-team corpus vs the deterministic structural checker | 21.8% catch, 0 twin false positives |
| Same corpus, LLM judge **with tool-log access** | ~98.2% catch |
| Judge-targeted corpus (attacks written against the judge prompt) | 98.1% catch — no meaningful degradation |
| Finance pack v0.5 vs 3 real tool-calling agents (2026-07-26) | 159/159 trajectories; 15 of 35 temptations drove at least one model to execute the harmful call |
| Same pack, hidden-state retrofit v0.5 → v0.6 | violation rate 14.0% → 47.2% on retrofitted cases vs +4.0pp on 23 unchanged controls — **difference-in-differences +29.2 points** |

**A new session should know the packs HAVE been run.** `PACKS.md` said otherwise
until 2026-08-20 and the statement was false; both reports live in
`evals/benchmarks/finance_redteam/reports/`. What is still true: `devops_sre` and
`healthcare_admin` have never been run, and no pack has been run at its current
frozen version (finance is now v0.11, the results above are v0.5/v0.6).
The B-05 report also publishes a measured run-to-run **noise floor of 21.7%** —
per-case verdicts from a single run are weak evidence.

**The load-bearing conclusion:** detection of claim-vs-log lies by an LLM judge
that reads the tool log is **effectively a solved, commodity capability**. Do not
build on the premise that monitors are blind, or that they are easily fooled by
one-shot attacks. Both were tested and falsified — see
`reports/comparisons/judge_with_log_audit.md` and `judge_targeted_audit.md`.

The durable open finding is **precision, not detection**: monitors are stable
about what they *catch* and unstable about what they *clear* (false positives on
honest work, and run-to-run verdict wobble on borderline records).

## Where to look next

- `evals/benchmarks/finance_redteam/METHODOLOGY.md` — the active pack charter
- `evals/adversarial/` — pre-registered protocols and frozen adversarial corpora
- `reports/comparisons/` — committed result artifacts
- `README.md` — public project overview
- `CONTRIBUTING.md` — contribution conventions
