# Milestone 29 - Report Manifest Quality-Gate Coverage

Date: 2026-05-25

Status: Complete / review-ready

Milestone 29 hardens the report artifact manifest so every known deterministic quality-gate report and snapshot remains indexed as a quality-gate artifact.

M29 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M29.1 Added an explicit expected quality-gate report/snapshot path set to `src/validate_report_manifest.py`.
- M29.2 Added local validation that all expected paths are present in `report_artifacts` with `quality_gate_included=true`.
- M29.3 Added focused tests for missing quality-gate artifacts and artifacts accidentally marked outside the quality gate.
- M29.4 Updated report-manifest docs, README, and wiki milestone indexes.

## Key Artifacts

Code and tests:

- `src/validate_report_manifest.py`
- `tests/test_report_manifest_validation.py`

Docs:

- `docs/wiki/concepts/report_artifact_manifest.md`
- `README.md`
- `docs/wiki/index.md`

## What The Repo Can Now Do

- Fail fast if a known quality-gate report or snapshot is removed from `reports/comparisons/report_manifest.json`.
- Fail if a known deterministic quality-gate artifact is kept in the manifest but marked outside the quality gate.
- Keep report provenance audit coverage deterministic and local.

## What Remains Intentionally Blocked

- Report regeneration from the manifest validator.
- Scorer changes or trace rewriting.
- Live collection, model calls, agent execution, network access, credentials, or external actions.
- Treating generated reports as benchmark claims.

## Quality Gate

From the repository root:

```bash
python3 scripts/check_all.py
```

The gate validates the report manifest after the indexed reports and snapshots are generated.

## Recommended Next Milestone

Milestone 30 should continue deterministic manifest governance only if there is an obvious local invariant to enforce. A possible candidate is checking that report manifest artifact IDs and labels follow stable naming conventions, but stop if that becomes a style preference rather than a correctness rule.
