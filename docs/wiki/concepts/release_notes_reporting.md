# Release Notes Reporting

Release notes reporting is the release handoff layer for completed local roadmap phases.

M39 adds:

- Release JSON: `reports/comparisons/release_notes_latest.json`
- Release notes: `reports/comparisons/release_notes_latest.md`
- Generator: `src/release_notes_summary.py`

## Source Boundary

The generator reads committed local artifacts:

- `reports/comparisons/reporting_product_summary.json`
- `reports/comparisons/report_manifest.json`
- `docs/roadmap.md`
- M35 through M44 closeout documents

It does not collect outputs, call providers, run local models, execute agents, inspect private logs, use network access, rescore records, or perform external actions.

## Reader Purpose

The release JSON gives a stable machine-readable handoff with:

- Dashboard signals from the M38 summary.
- Report-manifest artifact counts.
- Milestone rollup entries.
- Release highlights and safety boundaries.

The Markdown release notes provide the same handoff in a reader-facing format.

## Manifest Coverage

Both release-note artifacts are indexed in `reports/comparisons/report_manifest.json` and validated by `src/validate_report_manifest.py` as deterministic quality-gate artifacts.
