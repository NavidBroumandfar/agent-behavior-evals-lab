# Milestone 47 - Deterministic Scorer Refinement Triage

Date: 2026-06-20

Status: Complete / review-ready

Milestone 47 triages deterministic scorer or rubric refinement candidates from resolved public-safe adjudication evidence.

M47 does not add live provider execution, local model execution, live Hermes or OpenClaw execution, CLI-agent execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, shell execution, autonomous actions, private runtime-log ingestion, gated LLM review, private output collection, runtime harness execution, raw-output promotion, or deterministic scoring of local runtime output.

## Completed Slices

- M47.1 Added `src/scorer_refinement_triage.py`.
- M47.2 Added `reports/comparisons/scorer_refinement_triage.json`.
- M47.3 Added `reports/comparisons/scorer_refinement_triage.md`.
- M47.4 Triaged the current false-positive and false-negative calibration suggestions.
- M47.5 Recorded a no-change scorer decision because each candidate has only one adjudicated source example.
- M47.6 Listed focused tests and nearby controls required before any future scorer behavior change.
- M47.7 Indexed the triage artifacts in `reports/comparisons/report_manifest.json`.
- M47.8 Wired triage generation and compile coverage into `scripts/check_all.py`.
- M47.9 Updated trend, audit, release-note, roadmap, wiki, and test coverage.

## Key Artifacts

Code and tests:

- `src/scorer_refinement_triage.py`
- `tests/test_scorer_refinement_triage.py`
- `scripts/check_all.py`
- `src/validate_report_manifest.py`
- `tests/test_report_manifest_validation.py`

Generated triage artifacts:

- `reports/comparisons/scorer_refinement_triage.json`
- `reports/comparisons/scorer_refinement_triage.md`

Updated downstream artifacts:

- `reports/comparisons/report_manifest.json`
- `reports/comparisons/evidence_quality_audit.json`
- `reports/comparisons/evidence_quality_audit.md`
- `reports/comparisons/historical_trend_snapshot.json`
- `reports/comparisons/historical_trend_report.md`
- `reports/comparisons/release_notes_latest.json`
- `reports/comparisons/release_notes_latest.md`

Docs:

- `docs/wiki/concepts/deterministic_scorer_refinement_triage.md`
- `docs/wiki/index.md`
- `docs/roadmap.md`

## Current Triage Decision

- Candidates triaged: 2
- Accepted scorer changes: 0
- Deferred scorer changes: 2
- Scorer code changed: false
- Required evidence before change: at least two focused public-safe adjudication examples plus nearby control tests and full quality-gate validation.

## Boundary

M47 records scorer-change decisions only. It does not modify `src/scorers.py`, rewrite traces, apply reviewer decisions back into scored traces, or promote a model-assisted judge.

The current evidence remains useful for test planning, but not strong enough to safely change deterministic scorer behavior.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

Proceed to M48 External Fixture Review Expansion. The next useful phase is broadening public-safe review evidence for remaining external fixture traces before accepting scorer refinements.
