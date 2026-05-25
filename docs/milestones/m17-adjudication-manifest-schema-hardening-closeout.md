# Milestone 17 - Adjudication Manifest Schema Hardening

Date: 2026-05-25

Status: Complete / review-ready

Milestone 17 makes the adjudication manifest a first-class validated contract before report generation or regression checks consume it.

M17 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M17.1 Added `schemas/adjudication_manifest.schema.json`.
- M17.2 Added `src/validate_adjudication_manifest.py` as a standalone manifest validator.
- M17.3 Validated manifest shape, fixture paths, fixture record counts, source trace references, quality-gate statuses, and public-safe assertions.
- M17.4 Validated threshold map keys against declared fixture IDs and profile/category labels found in referenced scored traces.
- M17.5 Added focused positive and negative tests for the adjudication manifest validator.
- M17.6 Wired adjudication manifest validation into `scripts/check_all.py` before adjudication reports and regression checks.

## Key Artifacts

Manifest contract:

- `schemas/adjudication_manifest.schema.json`
- `traces/external/adjudication_manifest.json`
- `src/validate_adjudication_manifest.py`

Quality gate and tests:

- `scripts/check_all.py`
- `tests/test_adjudication_manifest_validation.py`

Docs:

- `README.md`
- `docs/wiki/concepts/adjudication_manifest_contract.md`
- `docs/wiki/concepts/adjudication_aware_reporting.md`
- `docs/wiki/concepts/human_adjudications.md`
- `docs/wiki/concepts/reporting_regression_snapshots.md`

## What The Repo Can Now Do

- Validate the adjudication manifest independently of report generation code.
- Reject missing or unexpected manifest fields before downstream consumers run.
- Reject unsafe safety assertions and quality-gate fixtures with `draft` or `blocked` review status.
- Reject fixture record-count mismatches and invalid repository path references.
- Reject typoed threshold keys for fixture, profile, or behavior category thresholds.

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

The gate now validates `traces/external/adjudication_manifest.json` against `schemas/adjudication_manifest.schema.json` before adjudication reporting and regression checks run.

## Recommended Next Milestone

Milestone 18 should reduce duplicate manifest validation logic:

1. Reuse the standalone manifest validator in report-loading tests where practical.
2. Compare report-loader validation and manifest-schema validation error coverage.
3. Keep report-generation behavior unchanged while making manifest validation ownership clearer.
4. Continue blocking live execution from deterministic quality-gate paths.
