# Milestone 45 - External Fixture Adjudication Coverage

Date: 2026-06-20

Status: Complete / review-ready

Milestone 45 increases reviewer coverage for committed public-safe external fixture groups before any runtime-native evidence expansion.

M45 does not add live provider execution, local model execution, live Hermes or OpenClaw execution, CLI-agent execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, shell execution, autonomous actions, private runtime-log ingestion, scorer changes, gated LLM review, private output collection, runtime harness execution, raw-output promotion, or deterministic scoring of local runtime output.

## Completed Slices

- M45.1 Added `traces/external/external_fixture_adjudications.example.jsonl`.
- M45.2 Registered the fixture in `traces/external/adjudication_manifest.json`.
- M45.3 Added reviewer decisions for selected public-safe transcript expansion records.
- M45.4 Added reviewer decisions for selected normalized adapter-output records.
- M45.5 Kept all M45 decisions as report-time adjudications; no scored trace or scorer behavior was changed.
- M45.6 Regenerated adjudication reports, regression snapshot, scorer calibration summary, reporting product summary, evidence quality audit, historical trend snapshot, and release notes.
- M45.7 Wired the new adjudication fixture validation into `scripts/check_all.py`.
- M45.8 Updated roadmap, wiki docs, and unit tests for the expanded review universe.

## Key Artifacts

Adjudication fixtures and manifest:

- `traces/external/external_fixture_adjudications.example.jsonl`
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

Code and tests:

- `scripts/check_all.py`
- `src/evidence_quality_audit.py`
- `src/historical_trend_snapshot.py`
- `src/release_notes_summary.py`
- `tests/test_validate_adjudications.py`
- `tests/test_adjudication_manifest_validation.py`
- `tests/test_adjudication_reporting.py`
- `tests/test_adjudication_regression_check.py`
- `tests/test_scorer_calibration_summary.py`
- `tests/test_evidence_quality_audit.py`
- `tests/test_historical_trend_snapshot.py`
- `tests/test_release_notes_summary.py`

Docs:

- `docs/wiki/concepts/external_fixture_adjudication_coverage.md`
- `docs/wiki/index.md`
- `docs/roadmap.md`

## Current Review Coverage

- Adjudication fixture families: 3
- Adjudication records: 20
- Source traces reviewed: 3
- External source traces reviewed: 2
- New M45 external fixture adjudications: 8
- New M45 unresolved discussion records: 0
- Public-safe transcript expansion review coverage: 4 of 8 records
- Normalized adapter-output review coverage: 4 of 4 records

## Boundary

M45 adds reviewer coverage over existing committed scored traces only. It does not promote raw runtime output, run a target system, change deterministic scorer logic, or apply reviewer decisions back into scored traces.

Reviewer decisions remain separate from heuristic scores. Calibration summaries and adjudicated aggregate reports may interpret reviewed records, but the original scored traces remain unchanged.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

Proceed to M46 Needs-Discussion Resolution. The next useful phase is resolving the remaining public-safe `needs_discussion` adjudication queue before accepting any deterministic scorer or rubric refinements.
