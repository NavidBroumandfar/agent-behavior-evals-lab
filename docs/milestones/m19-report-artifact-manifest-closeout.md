# Milestone 19 - Report Artifact Manifest

Date: 2026-05-25

Status: Complete / review-ready

Milestone 19 adds machine-readable provenance coverage for generated reports and regression snapshots.

M19 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M19.1 Added `reports/comparisons/report_manifest.json` as the generated report/snapshot artifact index.
- M19.2 Added `schemas/report_manifest.schema.json`.
- M19.3 Added `src/validate_report_manifest.py` to validate report artifact provenance metadata.
- M19.4 Validated artifact paths, generator scripts, declared input paths, snapshot dependencies, artifact suffixes, JSON snapshot parseability, and public-safe assertions.
- M19.5 Added focused positive and negative tests for report manifest validation.
- M19.6 Wired report manifest validation into `scripts/check_all.py` after report generation and baseline self-comparison.

## Key Artifacts

Report manifest contract:

- `reports/comparisons/report_manifest.json`
- `schemas/report_manifest.schema.json`
- `src/validate_report_manifest.py`

Quality gate and tests:

- `scripts/check_all.py`
- `tests/test_report_manifest_validation.py`

Docs:

- `README.md`
- `docs/wiki/concepts/report_artifact_manifest.md`
- `docs/wiki/concepts/reporting_regression_snapshots.md`

## What The Repo Can Now Do

- Track generated report and snapshot artifacts in a deterministic local manifest.
- Verify each indexed artifact exists and has the expected artifact type.
- Verify generator script paths and declared local inputs exist.
- Verify snapshot dependencies point to indexed JSON snapshot artifacts.
- Reject unsafe report artifact safety assertions.

## What Remains Intentionally Blocked

- Automatic scorer overrides.
- Automatic trace rewriting from adjudications.
- Live collection.
- Tool execution and external actions.
- Benchmark claims from generated reports or external fixtures.

## Quality Gate

From the repository root:

```bash
python3 scripts/check_all.py
```

The gate now validates `reports/comparisons/report_manifest.json` after all indexed report artifacts are generated.

## Recommended Next Milestone

Milestone 20 should reduce duplicated schema-subset validation code:

1. Move the small local JSON Schema subset validator into a shared utility module.
2. Update adjudication manifest and report manifest validators to use the shared helper.
3. Keep validator-specific semantic checks in their owning modules.
4. Continue blocking live execution from deterministic quality-gate paths.
