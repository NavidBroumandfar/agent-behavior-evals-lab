# Milestone 12 - Reviewed Adjudication Coverage

Date: 2026-05-23

Status: Complete / tag-ready

Milestone 12 broadens the public-safe adjudication fixture and adds review coverage controls while keeping adjudications as report-time overlays over existing scored traces.

M12 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M12.1 Expanded the committed adjudication fixture from 2 to 5 records.
- M12.2 Added examples for all reviewer decision types: `uphold_score`, `override_pass`, `override_fail`, and `needs_discussion`.
- M12.3 Added a `Needs Discussion Queue` to the adjudication summary report.
- M12.4 Added optional adjudication regression thresholds for minimum review coverage and maximum unresolved discussion count.
- M12.5 Wired the local quality gate to require at least 5.0% review coverage and no more than 2 `needs_discussion` records for the current fixture.
- M12.6 Exercised the reviewed fixture promotion checklist end to end in tests by validating a promoted fixture manifest entry after required artifacts exist.

## Key Artifacts

Adjudication fixture and reports:

- `traces/external/adjudications.example.jsonl`
- `src/adjudication_report.py`
- `reports/comparisons/adjudication_summary_report.md`
- `reports/comparisons/adjudicated_aggregate_report.md`

Regression and quality gate:

- `src/adjudication_regression_check.py`
- `reports/comparisons/adjudication_regression_snapshot.json`
- `scripts/check_all.py`
- `tests/test_adjudication_regression_check.py`

Promotion checklist coverage:

- `tests/test_promote_reviewed_outputs.py`
- `docs/wiki/concepts/reviewed_fixture_quality_gate_promotion.md`

## What The Repo Can Now Do

- Demonstrate every adjudication decision type in committed public-safe fixture data.
- Report unresolved `needs_discussion` cases as a review queue.
- Detect adjudication snapshot drift and optional review-threshold failures.
- Validate that promoted reviewed-output manifest entries can satisfy the deterministic fixture manifest checklist once required artifacts exist.

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

The gate now validates the expanded adjudication fixture, regenerates adjudication-aware reports, checks the updated adjudication regression snapshot, and enforces the current optional review thresholds.

## Recommended Next Milestone

Milestone 13 should prepare for multiple adjudication fixture families:

1. Support more than one committed adjudication JSONL input.
2. Add reviewer status summaries across fixture families.
3. Add profile/category-specific review coverage thresholds.
4. Add promotion status reporting for reviewed fixtures in the manifest.
5. Continue blocking live execution from deterministic quality-gate paths.
