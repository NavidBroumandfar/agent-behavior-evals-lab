# Reporting Product Layer

The reporting product layer turns existing deterministic artifacts into a compact product view for repeated development decisions.

M38 adds:

- Dashboard JSON: `reports/comparisons/reporting_product_summary.json`
- Markdown summary: `reports/comparisons/reporting_product_summary.md`
- Generator: `src/reporting_product_summary.py`

## Source Boundary

The generator reads committed local artifacts:

- `traces/scored/baseline_mock_run.jsonl`
- `traces/external/fixture_manifest.json`
- `reports/comparisons/adjudication_regression_snapshot.json`
- `traces/external/harness_bridge_plan.example.json`

It does not collect outputs, call providers, run local models, execute agents, inspect private logs, use network access, rescore records, or perform external actions.

## Reader Views

The JSON snapshot is dashboard-ready and includes:

- Baseline pass/fail metrics by profile and category.
- External fixture group pass/fail metrics.
- Adjudication review status and coverage.
- Harness bridge decision status.
- Product KPI rows for dashboards or release notes.

The Markdown report gives a concise executive view and an engineering view grounded in the same JSON summary sources.

## Manifest Coverage

Both M38 artifacts are indexed in `reports/comparisons/report_manifest.json` and validated by `src/validate_report_manifest.py` as deterministic quality-gate artifacts.
