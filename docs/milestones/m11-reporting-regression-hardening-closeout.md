# Milestone 11 - Reporting Regression Hardening

Date: 2026-05-23

Status: Complete / tag-ready

Milestone 11 hardens the M10 reporting layer with shared utilities and deterministic adjudication regression snapshots. The goal is to make reviewer-report drift visible before more reviewed fixtures are added.

M11 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M11.1 Shared reporting utilities for JSON loading, path display, percentages, Markdown writes, deterministic JSON writes, and nested snapshot comparison.
- M11.2 Adjudication regression snapshot builder and checker.
- M11.3 Committed adjudication regression snapshot for the public-safe example fixture.
- M11.4 Tests for adjudication snapshot counts and mismatch reporting.
- M11.5 Quality-gate integration for adjudication regression checks.
- M11.6 Documentation updates for snapshot-backed adjudication reporting.

## Key Artifacts

Shared utilities:

- `src/reporting_utils.py`

Adjudication regression:

- `src/adjudication_regression_check.py`
- `reports/comparisons/adjudication_regression_snapshot.json`
- `tests/test_adjudication_regression_check.py`

Updated report stack:

- `src/adjudication_report.py`
- `src/inspect_failures.py`
- `src/regression_check.py`
- `scripts/check_all.py`

## What The Repo Can Now Do

- Compare current adjudication reporting aggregates against a committed deterministic snapshot.
- Detect drift in reviewer decision counts, reviewed result counts, review coverage, reviewed profiles/categories, and reviewed failure-mode distributions.
- Share path display, JSON loading, text writing, percentage, pass-count, and nested comparison helpers across report/check scripts.
- Keep adjudication report changes visible in the local quality gate before reviewed fixture coverage expands.

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

The gate now validates adjudications, generates adjudication-aware reports, checks adjudication aggregate counts against `reports/comparisons/adjudication_regression_snapshot.json`, and verifies deterministic reports exist.

## Recommended Next Milestone

Milestone 12 should broaden reviewed fixture coverage while preserving the hardened reporting boundary:

1. Add a small second adjudication fixture family or expanded public-safe examples.
2. Add unresolved `needs_discussion` reporting and optional coverage thresholds.
3. Exercise the reviewed fixture promotion checklist end to end.
4. Keep adjudicated results separate from heuristic trace history.
5. Continue blocking live execution from deterministic quality-gate paths.
