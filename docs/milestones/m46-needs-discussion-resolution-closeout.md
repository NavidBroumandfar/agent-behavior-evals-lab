# Milestone 46 - Needs-Discussion Resolution

Date: 2026-06-20

Status: Complete / review-ready

Milestone 46 resolves the remaining public-safe adjudication records that were still marked `needs_discussion`.

M46 does not add live provider execution, local model execution, live Hermes or OpenClaw execution, CLI-agent execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, shell execution, autonomous actions, private runtime-log ingestion, scorer changes, gated LLM review, private output collection, runtime harness execution, raw-output promotion, or deterministic scoring of local runtime output.

## Completed Slices

- M46.1 Resolved `ADJ-BASELINE-APPROVAL-004-GENERIC-001` from `needs_discussion` to `uphold_score`.
- M46.2 Resolved `ADJ-BASELINE-UNCERTAINTY-001-GENERIC-001` from `needs_discussion` to `uphold_score`.
- M46.3 Resolved `ADJ-FOLLOWUP-SAFE-009-STRICT-001` from `needs_discussion` to `uphold_score`.
- M46.4 Updated `traces/external/adjudication_manifest.json` review statuses and thresholds to require zero unresolved discussion records.
- M46.5 Regenerated adjudication reports, regression snapshot, scorer calibration summary, reporting product summary, evidence quality audit, historical trend snapshot, and release notes.
- M46.6 Updated roadmap, wiki docs, and unit tests for the resolved review queue.

## Key Artifacts

Adjudication fixtures and manifest:

- `traces/external/adjudications.example.jsonl`
- `traces/external/adjudications.followup.example.jsonl`
- `traces/external/adjudication_manifest.json`

Updated reports and snapshots:

- `reports/comparisons/adjudication_summary_report.md`
- `reports/comparisons/adjudicated_aggregate_report.md`
- `reports/comparisons/adjudication_regression_snapshot.json`
- `reports/comparisons/scorer_calibration_summary.json`
- `reports/comparisons/scorer_calibration_summary.md`
- `reports/comparisons/evidence_quality_audit.json`
- `reports/comparisons/evidence_quality_audit.md`
- `reports/comparisons/historical_trend_snapshot.json`
- `reports/comparisons/historical_trend_report.md`

Docs and tests:

- `docs/wiki/concepts/needs_discussion_resolution.md`
- `docs/wiki/index.md`
- `docs/roadmap.md`
- `tests/test_adjudication_reporting.py`
- `tests/test_adjudication_regression_check.py`
- `tests/test_scorer_calibration_summary.py`
- `tests/test_historical_trend_snapshot.py`
- `tests/test_release_notes_summary.py`

## Current Review State

- Adjudication records: 20
- Source traces reviewed: 3
- Reviewer decisions still marked `needs_discussion`: 0
- Ambiguous calibration reviews: 0
- Changed reviewer results: 2
- Accepted scorer changes: 0

## Boundary

M46 resolves reviewer interpretation records only. It does not apply reviewer decisions back into scored traces, change `src/scorers.py`, or promote a model-assisted judge.

The two existing overrides remain report-time adjudicated interpretations. The original heuristic scored traces remain unchanged.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

Proceed to M47 Deterministic Scorer Refinement Triage. The next useful phase is deciding whether the resolved adjudication evidence supports any narrow scorer or rubric refinement, with focused tests required before accepting behavior changes.
