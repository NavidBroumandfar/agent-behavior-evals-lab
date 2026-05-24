# Milestone 14 - Adjudication Fixture Status Governance

Date: 2026-05-24

Status: Complete / review-ready

Milestone 14 adds review status governance to manifest-backed adjudication fixture families.

M14 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M14.1 Added required fixture status metadata to `traces/external/adjudication_manifest.json`.
- M14.2 Validated `review_status`, `owner`, `status_notes`, and `last_reviewed_at` for each adjudication fixture.
- M14.3 Blocked `draft` and `blocked` review statuses from quality-gate-included adjudication fixtures.
- M14.4 Surfaced fixture status metadata in adjudication summary reports.
- M14.5 Added fixture status metadata to adjudication regression snapshots.
- M14.6 Added negative tests for duplicate fixture IDs, unsafe safety assertions, invalid review statuses, and quality-gate/status mismatches.

## Key Artifacts

Manifest and governance:

- `traces/external/adjudication_manifest.json`
- `src/adjudication_report.py`
- `src/adjudication_regression_check.py`

Reports and snapshots:

- `reports/comparisons/adjudication_summary_report.md`
- `reports/comparisons/adjudication_regression_snapshot.json`

Tests and docs:

- `tests/test_adjudication_reporting.py`
- `tests/test_adjudication_regression_check.py`
- `docs/wiki/concepts/adjudication_aware_reporting.md`
- `docs/wiki/concepts/human_adjudications.md`
- `docs/wiki/concepts/reporting_regression_snapshots.md`
- `docs/wiki/concepts/reviewed_fixture_quality_gate_promotion.md`

## What The Repo Can Now Do

- Show whether each adjudication fixture is `draft`, `reviewed`, `needs_discussion`, or `blocked`.
- Record an owner, status notes, and last-reviewed timestamp for each fixture family.
- Reject invalid fixture review status values.
- Reject quality-gate fixtures that are still draft or blocked.
- Track fixture status changes through deterministic snapshot diffs.

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

The gate validates adjudication fixture status metadata through the manifest-backed report and snapshot paths.

## Recommended Next Milestone

Milestone 15 should add status-aware coverage controls:

1. Add profile/category-specific review coverage thresholds.
2. Add optional maximum unresolved `needs_discussion` thresholds by fixture family.
3. Add CLI output that identifies which fixture family caused a threshold failure.
4. Continue blocking live execution from deterministic quality-gate paths.
