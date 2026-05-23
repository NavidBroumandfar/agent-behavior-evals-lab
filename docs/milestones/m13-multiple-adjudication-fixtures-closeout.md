# Milestone 13 - Multiple Adjudication Fixture Families

Date: 2026-05-23

Status: Complete / review-ready

Milestone 13 moves adjudication-aware reporting from a single JSONL fixture to a manifest-backed set of committed public-safe adjudication fixture families.

M13 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M13.1 Added `traces/external/adjudication_manifest.json` as the committed index for adjudication fixture families.
- M13.2 Added `traces/external/adjudications.followup.example.jsonl` as a second public-safe adjudication fixture.
- M13.3 Extended adjudication-aware reports to show fixture family counts, paths, quality-gate inclusion status, and reviewer decisions by fixture.
- M13.4 Extended failure inspection to load reviewer annotations from the manifest-backed fixture set.
- M13.5 Extended adjudication regression snapshots to include fixture-family metadata and manifest-backed aggregate counts.
- M13.6 Wired the local quality gate to validate both adjudication fixtures and run manifest-backed reporting, failure inspection, and snapshot checks.

## Key Artifacts

Adjudication fixture families:

- `traces/external/adjudications.example.jsonl`
- `traces/external/adjudications.followup.example.jsonl`
- `traces/external/adjudication_manifest.json`

Reporting and regression:

- `src/adjudication_report.py`
- `src/adjudication_regression_check.py`
- `src/inspect_failures.py`
- `reports/comparisons/adjudication_summary_report.md`
- `reports/comparisons/adjudicated_aggregate_report.md`
- `reports/comparisons/adjudication_regression_snapshot.json`
- `reports/comparisons/failure_inspection.md`

Quality gate and tests:

- `scripts/check_all.py`
- `tests/test_adjudication_reporting.py`
- `tests/test_adjudication_regression_check.py`
- `tests/test_validate_adjudications.py`

## What The Repo Can Now Do

- Load multiple committed adjudication JSONL fixtures through one manifest.
- Reject mismatched fixture record counts and undeclared adjudication source traces.
- Report reviewer decision counts both globally and per fixture family.
- Carry all fixture-family reviewer annotations into failure inspection.
- Detect drift in manifest-backed adjudication aggregates through the snapshot checker.

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

The gate now validates both committed adjudication fixture files, regenerates manifest-backed adjudication reports, regenerates failure inspection with manifest annotations, checks the adjudication regression snapshot, and enforces the current optional review thresholds.

## Recommended Next Milestone

Milestone 14 should harden review governance across fixture families:

1. Add profile/category-specific review coverage thresholds.
2. Add per-fixture reviewer status metadata for unresolved discussion queues.
3. Add promotion status reporting for reviewed fixtures in the manifest.
4. Add manifest-focused negative tests for safety assertion failures and duplicate fixture IDs.
5. Continue blocking live execution from deterministic quality-gate paths.
