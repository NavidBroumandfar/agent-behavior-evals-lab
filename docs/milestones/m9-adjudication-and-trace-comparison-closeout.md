# Milestone 9 - Human Adjudication & Scored Trace Comparison

Date: 2026-05-23

Status: Complete / tag-ready

Milestone 9 adds a public-safe human adjudication layer and a generic scored-trace comparison command. The evaluator can now validate reviewer decisions against source traces and compare arbitrary scored trace files without changing scoring logic or running live systems.

M9 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, file mutation, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M9.1 Human adjudication record schema and example fixture.
- M9.2 Adjudication validator with source-trace consistency checks.
- M9.3 Generic before-vs-after scored-trace comparison command.
- M9.4 Baseline self-comparison report generation.
- M9.5 Tests for adjudication decisions and trace comparison deltas.
- M9.6 Quality-gate integration for adjudication validation and self-comparison.

## Key Artifacts

Adjudication:

- `schemas/adjudication.schema.json`
- `traces/external/adjudications.example.jsonl`
- `src/validate_adjudications.py`
- `tests/test_validate_adjudications.py`
- `docs/wiki/concepts/human_adjudications.md`

Trace comparison:

- `src/compare_scored_traces.py`
- `reports/comparisons/baseline_self_comparison_report.md`
- `tests/test_compare_scored_traces.py`
- `docs/wiki/concepts/scored_trace_comparison.md`

## What The Repo Can Now Do

- Validate human adjudications against source scored traces.
- Preserve original scored traces while recording reviewer decisions.
- Detect invalid adjudication overrides.
- Compare any two scored trace files for changed outcomes, scores, failure modes, added records, removed records, new failures, and resolved failures.
- Generate deterministic Markdown trace-comparison reports.

## What Remains Intentionally Blocked

- Automatic scorer overrides.
- Automatic trace rewriting from adjudications.
- Live collection.
- Tool execution and external actions.
- Benchmark claims from adjudicated fixtures.

## Quality Gate

From the repository root:

```bash
python3 scripts/check_all.py
```

The gate validates adjudication examples and runs a baseline self-comparison. It does not compare live systems or apply adjudications to scored traces.

## Recommended Next Milestone

Milestone 10 should make reporting adjudication-aware:

1. Adjudication summary report.
2. Failure inspection annotated with reviewer decisions.
3. Optional adjudicated aggregate report that clearly separates heuristic and reviewed results.
4. Manifest-driven external fixture comparison.
5. Promotion checklist for adding reviewed fixtures to the deterministic quality gate.

Keep live tool execution blocked until adjudicated reporting is stable.

## Tag Readiness

After the closeout commit and a clean quality gate, the repository is ready for:

`v0.9.0-adjudication-and-trace-comparison`
