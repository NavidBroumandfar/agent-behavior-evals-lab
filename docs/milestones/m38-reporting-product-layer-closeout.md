# Milestone 38 - Reporting Product Layer

Date: 2026-06-20

Status: Complete / review-ready

Milestone 38 adds deterministic product-oriented reporting artifacts for repeated development decisions.

M38 does not add live provider execution, local model execution, live Hermes or OpenClaw execution, CLI-agent execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, shell execution, autonomous actions, private runtime-log ingestion, scorer changes, or new output collection.

## Completed Slices

- M38.1 Added `src/reporting_product_summary.py` to generate dashboard-ready JSON and Markdown summaries.
- M38.2 Added `reports/comparisons/reporting_product_summary.json`.
- M38.3 Added `reports/comparisons/reporting_product_summary.md`.
- M38.4 Indexed both artifacts in `reports/comparisons/report_manifest.json`.
- M38.5 Updated `src/validate_report_manifest.py` and report-manifest tests for the new quality-gate artifacts.
- M38.6 Wired product summary generation and compile coverage into `scripts/check_all.py`.
- M38.7 Added focused tests for summary structure, key counts, Markdown sections, and empty-trace rejection.
- M38.8 Updated roadmap, wiki docs, and milestone index.

## Key Artifacts

Code and tests:

- `src/reporting_product_summary.py`
- `tests/test_reporting_product_summary.py`
- `scripts/check_all.py`
- `src/validate_report_manifest.py`
- `tests/test_report_manifest_validation.py`

Generated reporting artifacts:

- `reports/comparisons/reporting_product_summary.json`
- `reports/comparisons/reporting_product_summary.md`

Docs and manifest:

- `reports/comparisons/report_manifest.json`
- `docs/wiki/concepts/reporting_product_layer.md`
- `docs/roadmap.md`
- `docs/wiki/index.md`

## Product Scope

The JSON summary includes:

- Baseline pass/fail metrics by profile and category.
- External fixture pass/fail metrics by fixture group.
- Adjudication review status and source trace coverage.
- Harness bridge decision status from M37.
- Dashboard KPI rows and release/engineering views.

The Markdown summary gives a concise executive view, dashboard KPI table, profile/category summaries, fixture summaries, and engineering follow-up context.

## Boundary

The M38 generator reads only committed local artifacts:

- `traces/scored/baseline_mock_run.jsonl`
- `traces/external/fixture_manifest.json`
- `reports/comparisons/adjudication_regression_snapshot.json`
- `traces/external/harness_bridge_plan.example.json`

It does not collect new outputs, rescore existing traces, run models, execute agents, call providers, use network access, inspect private logs, or perform external actions.

## Current Generated Counts

- Baseline records: 126
- Baseline passed: 115
- Baseline failed: 11
- External fixture groups: 6
- External fixture scored records: 26
- Adjudication records: 12
- Harness bridge decision: `defer_harness_integration`

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

The roadmap overview is now complete through M38. A future phase should either refine the reporting product layer with additional historical snapshots and release-note templates, or start a new roadmap section before adding any live integration.
