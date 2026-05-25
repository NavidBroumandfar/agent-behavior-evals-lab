# Milestone 18 - Manifest Validator Report Loader Integration

Date: 2026-05-25

Status: Complete / review-ready

Milestone 18 makes the standalone adjudication manifest validator the preflight contract for manifest-backed report loading.

M18 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M18.1 Added a reusable `load_validated_manifest` entrypoint to `src/validate_adjudication_manifest.py`.
- M18.2 Updated `src/adjudication_report.py` to validate manifests through the standalone validator before constructing report dataclasses.
- M18.3 Removed duplicated manifest shape, safety assertion, review-status, path, and threshold validation ownership from the report loader path.
- M18.4 Kept report-time adjudication record checks in the report loader, including undeclared source trace references and duplicate adjudication targets.
- M18.5 Added a report-loader test proving validator-owned threshold-key failures are surfaced before report dataclass construction.
- M18.6 Updated docs to clarify manifest validation ownership.

## Key Artifacts

Manifest validation and report loading:

- `src/validate_adjudication_manifest.py`
- `src/adjudication_report.py`
- `schemas/adjudication_manifest.schema.json`

Tests and docs:

- `tests/test_adjudication_reporting.py`
- `docs/wiki/concepts/adjudication_manifest_contract.md`
- `docs/wiki/concepts/adjudication_aware_reporting.md`
- `docs/wiki/concepts/human_adjudications.md`
- `docs/wiki/concepts/reporting_regression_snapshots.md`

## What The Repo Can Now Do

- Reuse the standalone adjudication manifest validator from manifest-backed report loading.
- Fail manifest-backed reports and regression checks on schema, fixture path, fixture count, safety assertion, review status, and threshold-key errors before report dataclass construction.
- Keep report-loader validation focused on adjudication record relationships that require loading fixture records.
- Maintain deterministic local quality gates without live execution or external actions.

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

The gate now validates the adjudication manifest both as an explicit check and as the report-loader preflight for manifest-backed reporting and regression paths.

## Recommended Next Milestone

Milestone 19 should add schema coverage for generated report metadata:

1. Add a small machine-readable report manifest for generated comparison artifacts.
2. Validate report paths, generation inputs, and snapshot dependencies.
3. Keep Markdown reports as human-readable outputs while tracking deterministic report provenance separately.
4. Continue blocking live execution from deterministic quality-gate paths.
