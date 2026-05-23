# Milestone 10 - Adjudication-Aware Reporting

Date: 2026-05-23

Status: Complete / tag-ready

Milestone 10 makes reporting adjudication-aware while preserving the M9 boundary: reviewer decisions are report-time overlays over existing scored traces, not automatic trace rewrites.

M10 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M10.1 Adjudication summary report.
- M10.2 Adjudicated aggregate report that separates full heuristic trace results, reviewed heuristic results, and reviewed adjudicated results.
- M10.3 Failure inspection annotations for reviewer decisions.
- M10.4 Manifest-driven external fixture comparison.
- M10.5 Reviewed fixture quality-gate promotion checklist.
- M10.6 Quality-gate integration for adjudication-aware reporting.

## Key Artifacts

Adjudication-aware reports:

- `src/adjudication_report.py`
- `reports/comparisons/adjudication_summary_report.md`
- `reports/comparisons/adjudicated_aggregate_report.md`
- `tests/test_adjudication_reporting.py`
- `docs/wiki/concepts/adjudication_aware_reporting.md`

Manifest-driven fixture comparison:

- `src/compare_external_fixtures.py`
- `tests/test_compare_external_fixtures.py`
- `reports/comparisons/external_fixture_comparison_report.md`

Promotion checklist:

- `docs/wiki/concepts/reviewed_fixture_quality_gate_promotion.md`

## What The Repo Can Now Do

- Summarize public-safe human adjudications across source traces, reviewers, profiles, decisions, and reviewed records.
- Generate an adjudicated aggregate report without rewriting scored traces.
- Annotate failure inspection output with matching reviewer decisions.
- Build external fixture comparison source groups from `traces/external/fixture_manifest.json`.
- Use a documented checklist before admitting promoted reviewed fixtures to deterministic quality-gate coverage.

## What Remains Intentionally Blocked

- Automatic scorer overrides.
- Automatic trace rewriting from adjudications.
- Live collection.
- Tool execution and external actions.
- Benchmark claims from adjudicated or external fixtures.

## Quality Gate

From the repository root:

```bash
python3 scripts/check_all.py
```

The gate now validates adjudications, generates adjudication-aware reports, verifies those reports exist, and keeps manifest-driven fixture comparison in the deterministic local check.

## Recommended Next Milestone

Milestone 11 should broaden schema and regression hardening:

1. Shared JSONL loading/reporting utilities to reduce duplication.
2. Schema-level validation coverage for adjudication-aware report inputs.
3. Regression snapshots for adjudication summary counts.
4. Additional reviewed fixture examples once the promotion checklist has been exercised.
5. Continued separation between saved-output reporting and live adapter execution.
