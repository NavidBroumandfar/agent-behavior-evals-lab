# Milestone 15 - Status-Aware Adjudication Thresholds

Date: 2026-05-24

Status: Complete / review-ready

Milestone 15 adds status-aware quality-gate thresholds for manifest-backed adjudication fixtures.

M15 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M15.1 Added review coverage snapshots by profile.
- M15.2 Added review coverage snapshots by behavior category.
- M15.3 Added repeatable CLI thresholds for profile-specific review coverage.
- M15.4 Added repeatable CLI thresholds for category-specific review coverage.
- M15.5 Added repeatable CLI thresholds for fixture-specific `needs_discussion` caps.
- M15.6 Wired the local quality gate to enforce explicit passing thresholds for the current public-safe fixture families.

## Key Artifacts

Regression checker and gate:

- `src/adjudication_regression_check.py`
- `scripts/check_all.py`
- `reports/comparisons/adjudication_regression_snapshot.json`

Tests and docs:

- `tests/test_adjudication_regression_check.py`
- `docs/wiki/concepts/adjudication_aware_reporting.md`
- `docs/wiki/concepts/reporting_regression_snapshots.md`

## What The Repo Can Now Do

- Fail the adjudication regression check when a configured profile has too little review coverage.
- Fail the adjudication regression check when a configured category has too little review coverage.
- Fail the adjudication regression check when a configured fixture family has too many unresolved `needs_discussion` records.
- Report threshold failures with the exact profile, category, or fixture family that violated the configured limit.

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

The gate now enforces source-trace coverage, profile coverage, category coverage, global unresolved discussion count, and per-fixture unresolved discussion caps.

## Recommended Next Milestone

Milestone 16 should move threshold policy from CLI arguments into the adjudication manifest:

1. Add an optional `quality_gate_thresholds` block to `traces/external/adjudication_manifest.json`.
2. Let `src/adjudication_regression_check.py` load manifest-declared thresholds by default.
3. Keep CLI threshold arguments as explicit overrides for local experiments.
4. Continue blocking live execution from deterministic quality-gate paths.
