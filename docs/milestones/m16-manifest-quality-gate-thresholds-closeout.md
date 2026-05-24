# Milestone 16 - Manifest Quality-Gate Thresholds

Date: 2026-05-24

Status: Complete / review-ready

Milestone 16 moves committed adjudication quality-gate threshold policy from repeated CLI arguments into the adjudication manifest.

M16 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M16.1 Added optional `quality_gate_thresholds` policy to `traces/external/adjudication_manifest.json`.
- M16.2 Added manifest validation for scalar source-trace coverage and global `needs_discussion` thresholds.
- M16.3 Added manifest validation for profile, category, and fixture-specific threshold maps.
- M16.4 Updated `src/adjudication_regression_check.py` to apply manifest thresholds by default for manifest-backed checks.
- M16.5 Kept CLI threshold arguments as explicit local overrides.
- M16.6 Updated `scripts/check_all.py` to rely on manifest-declared threshold policy.

## Key Artifacts

Manifest and validation:

- `traces/external/adjudication_manifest.json`
- `src/adjudication_report.py`
- `src/adjudication_regression_check.py`

Quality gate and tests:

- `scripts/check_all.py`
- `tests/test_adjudication_reporting.py`
- `tests/test_adjudication_regression_check.py`

Docs:

- `README.md`
- `docs/wiki/concepts/adjudication_aware_reporting.md`
- `docs/wiki/concepts/human_adjudications.md`
- `docs/wiki/concepts/reporting_regression_snapshots.md`

## What The Repo Can Now Do

- Load committed adjudication threshold policy from the manifest-backed path by default.
- Reject invalid manifest threshold fields, non-finite percentages, out-of-range percentages, and negative integer caps.
- Preserve local CLI override workflows for experiments without changing committed manifest policy.
- Run the local quality gate without duplicating adjudication thresholds in `scripts/check_all.py`.

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

The gate now loads committed adjudication thresholds from `traces/external/adjudication_manifest.json`.

## Recommended Next Milestone

Milestone 17 should harden the manifest contract further:

1. Add a dedicated JSON Schema for `traces/external/adjudication_manifest.json`.
2. Validate the manifest schema independently from report generation.
3. Document threshold field semantics in a short manifest contract page.
4. Continue blocking live execution from deterministic quality-gate paths.
