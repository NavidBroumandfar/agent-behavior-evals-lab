# Milestone 43 - Historical Trend Snapshots

Date: 2026-06-20

Status: Complete / review-ready

Milestone 43 adds deterministic evaluator-health trend snapshots generated from committed local reports, manifests, snapshots, and scored traces.

M43 does not add live provider execution, local model execution, live Hermes or OpenClaw execution, CLI-agent execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, shell execution, autonomous actions, private runtime-log ingestion, scorer changes, gated LLM review, private output collection, or runtime harness execution.

## Completed Slices

- M43.1 Added `src/historical_trend_snapshot.py`.
- M43.2 Added `reports/comparisons/historical_trend_snapshot.json`.
- M43.3 Added `reports/comparisons/historical_trend_report.md`.
- M43.4 Trended pass rates, failure modes, adjudication outcomes, fixture counts, and report-manifest coverage.
- M43.5 Added versioned checkpoint rows for baseline, M40, M41, M42, and M43 review context.
- M43.6 Indexed both trend artifacts in `reports/comparisons/report_manifest.json`.
- M43.7 Wired trend generation and compile coverage into `scripts/check_all.py`.
- M43.8 Updated the evidence audit, release notes, docs, and tests for the new trend layer.

## Key Artifacts

Code and tests:

- `src/historical_trend_snapshot.py`
- `tests/test_historical_trend_snapshot.py`
- `scripts/check_all.py`
- `src/validate_report_manifest.py`
- `tests/test_report_manifest_validation.py`
- `src/evidence_quality_audit.py`
- `tests/test_evidence_quality_audit.py`
- `src/release_notes_summary.py`
- `tests/test_release_notes_summary.py`

Generated trend artifacts:

- `reports/comparisons/historical_trend_snapshot.json`
- `reports/comparisons/historical_trend_report.md`

Docs and manifest:

- `reports/comparisons/report_manifest.json`
- `docs/wiki/concepts/historical_trend_snapshots.md`
- `docs/roadmap.md`
- `docs/wiki/index.md`

## Current Trend Snapshot

- Baseline pass rate: 91.3%
- External fixture pass rate: 55.9%
- External fixture groups: 7
- External fixture scored records: 34
- Adjudication records: 12
- Changed adjudication results: 2
- Report artifacts indexed: 24
- JSON snapshots indexed: 7
- Markdown reports indexed: 17

## Boundary

The trend artifacts describe evaluator health and committed fixture coverage. They do not rank models, agents, Hermes, OpenClaw, hosted systems, or production behavior.

Pass-rate movement can reflect fixture changes, scorer changes, adjudication changes, or report coverage changes. It should be reviewed as evaluator instrumentation drift unless a future promoted fixture explicitly supports stronger claims.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

Proceed to M44 Optional Non-Gated Runtime Trial only if the trial remains manual, non-gated, disposable, public-safe, and excluded from deterministic scoring until reviewed output is promoted through an existing fixture format.
