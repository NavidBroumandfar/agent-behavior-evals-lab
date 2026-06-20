# Milestone 50 - Deterministic Scorer Change Decision

Date: 2026-06-21

Status: Complete / review-ready

Milestone 50 decides whether the M49 scorer candidate controls justify changing the deterministic v0 scorer.

M50 records a durable no-change scorer decision. It does not add live provider execution, local model execution, live Hermes or OpenClaw execution, CLI-agent execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, shell execution, autonomous actions, private runtime-log ingestion, gated LLM review, private output collection, runtime harness execution, raw-output promotion, scored trace rewrites, or scorer behavior changes.

## Completed Slices

- M50.1 Added `src/scorer_change_decision.py`.
- M50.2 Added `reports/comparisons/scorer_change_decision.json`.
- M50.3 Added `reports/comparisons/scorer_change_decision.md`.
- M50.4 Added focused tests for the no-change decision, conflicting safe clarification evidence, approval-disclosure guardrails, and Markdown output.
- M50.5 Indexed the new decision artifacts in `reports/comparisons/report_manifest.json`.
- M50.6 Wired the decision generator into `scripts/check_all.py`.
- M50.7 Updated evidence audit, historical trend snapshots, release notes, roadmap, wiki, and report-manifest validation.

## Decision Outcome

- Candidates evaluated: 2
- Accepted scorer changes: 0
- Rubric-only no-change decisions: 2
- Scorer code changed: false
- Scored trace behavior changed: false
- Decision: `rubric_only_no_scorer_change`

## Rationale

The safe low-friction clarification candidate remains a no-change decision because the same strict-profile output text is adjudicated differently across nearby safe cases. One reviewed case treats the brief-vs-detailed preference question as acceptable, while three reviewed nearby safe cases uphold `over_refusal`. A broad output-only scorer exception would hide those upheld failures.

The approval-disclosure candidate remains a no-change decision because the current evidence contains one false negative and one nearby positive control, but tightening the heuristic would change committed scored trace behavior for a reviewed record. The current adjudication schema validates original scorer fields against current scored traces, so scorer-versioned historical guardrails should exist before any trace-changing scorer update.

## Key Artifacts

Code and tests:

- `src/scorer_change_decision.py`
- `tests/test_scorer_change_decision.py`
- `scripts/check_all.py`

Generated decision artifacts:

- `reports/comparisons/scorer_change_decision.json`
- `reports/comparisons/scorer_change_decision.md`

Updated downstream artifacts:

- `reports/comparisons/report_manifest.json`
- `reports/comparisons/evidence_quality_audit.json`
- `reports/comparisons/evidence_quality_audit.md`
- `reports/comparisons/historical_trend_snapshot.json`
- `reports/comparisons/historical_trend_report.md`
- `reports/comparisons/release_notes_latest.json`
- `reports/comparisons/release_notes_latest.md`

Docs:

- `docs/wiki/concepts/scorer_change_decision.md`
- `docs/wiki/index.md`
- `docs/roadmap.md`

## Boundary

M50 is a decision and reporting phase only. It does not modify `src/scorers.py`, regenerate traces due to scorer behavior changes, apply reviewer decisions back into scored traces, or accept model-assisted judging.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

Proceed to M51 Scorer Versioning Guardrails. The next useful phase is adding explicit scorer-version or pre-change outcome metadata so future scorer changes can preserve historical adjudication context without rewriting review history.
