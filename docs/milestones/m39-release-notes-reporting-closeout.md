# Milestone 39 - Release Notes Reporting

Date: 2026-06-20

Status: Complete / review-ready

Milestone 39 adds deterministic release-note artifacts on top of the M38 reporting product layer.

M39 does not add live provider execution, local model execution, live Hermes or OpenClaw execution, CLI-agent execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, shell execution, autonomous actions, private runtime-log ingestion, scorer changes, or new output collection.

## Completed Slices

- M39.1 Added `src/release_notes_summary.py` to generate release-note JSON and Markdown.
- M39.2 Added `reports/comparisons/release_notes_latest.json`.
- M39.3 Added `reports/comparisons/release_notes_latest.md`.
- M39.4 Added milestone rollup coverage for M35 through M39.
- M39.5 Indexed both release-note artifacts in `reports/comparisons/report_manifest.json`.
- M39.6 Updated report-manifest validation expectations and tests.
- M39.7 Wired release-note generation and compile coverage into `scripts/check_all.py`.
- M39.8 Updated roadmap, wiki docs, and milestone index.

## Key Artifacts

Code and tests:

- `src/release_notes_summary.py`
- `tests/test_release_notes_summary.py`
- `scripts/check_all.py`
- `src/validate_report_manifest.py`
- `tests/test_report_manifest_validation.py`

Generated release artifacts:

- `reports/comparisons/release_notes_latest.json`
- `reports/comparisons/release_notes_latest.md`

Docs and manifest:

- `reports/comparisons/report_manifest.json`
- `docs/wiki/concepts/release_notes_reporting.md`
- `docs/roadmap.md`
- `docs/wiki/index.md`

## Release Scope

The JSON release snapshot includes:

- Dashboard signals from the M38 product summary.
- Report-manifest artifact counts.
- Milestone rollup from M35 through M39.
- Release highlights, readiness status, and public-safe boundaries.

The Markdown release notes provide a reader-facing handoff with summary, highlights, dashboard snapshot, milestone rollup, boundaries, and source paths.

## Boundary

The M39 generator reads only committed local artifacts:

- `reports/comparisons/reporting_product_summary.json`
- `reports/comparisons/report_manifest.json`
- `docs/roadmap.md`
- M35 through M39 milestone closeouts

It does not collect new outputs, rescore traces, run models, execute agents, call providers, use network access, inspect private logs, or perform external actions.

## Current Generated Counts

- Milestones summarized: 5
- Report artifacts indexed before release-note manifest entries: at least 15
- Baseline records surfaced from M38 summary: 126
- External fixture records surfaced from M38 summary: 26
- Harness bridge decision surfaced from M37/M38: `defer_harness_integration`

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

Future work should start a new roadmap section before any live integration. A conservative next step would be historical comparison snapshots across committed release-note summaries, still sourced only from local deterministic artifacts.
