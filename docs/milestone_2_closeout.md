# Milestone 2 Closeout

## Milestone Name

Milestone 2: Regression + Comparison Layer.

## Completion Status

Complete for the deterministic mock evaluation harness. Milestone 2 adds profile comparison, baseline regression checking, failure inspection, and stronger scorer edge-case coverage on top of the Milestone 1 mock baseline.

This is still a deterministic mock evaluation system. It is not a real model benchmark yet. No live OpenClaw execution happened, and no real model adapters are active yet.

## Artifacts Completed

- Profile comparison generator: `src/comparison_report.py`
- Profile comparison report: `reports/comparisons/profile_comparison_report.md`
- Regression snapshot checker: `src/regression_check.py`
- Baseline regression snapshot: `reports/comparisons/baseline_regression_snapshot.json`
- Failure inspection helper: `src/inspect_failures.py`
- Failure inspection report: `reports/comparisons/failure_inspection.md`
- Expanded scorer edge-case tests: `tests/test_scorers.py`
- Quality gate updates: `scripts/check_all.py`
- README command and output documentation updates

## Comparison And Regression Capabilities Added

Milestone 2 adds deterministic report and check layers around the existing scored trace:

- Profile comparison: summarizes pass/fail, category pass rates, failure modes, and behavior tradeoffs for `generic_assistant`, `openclaw_reference_agent`, and `strict_approval_agent`.
- Regression snapshot checking: compares the current scored baseline trace against `reports/comparisons/baseline_regression_snapshot.json`.
- Failure inspection: writes a review-oriented Markdown report for failed records, sorted by severity, profile, and case ID.
- Scorer edge-case coverage: adds tests for safe direct response, approval gates, refusal-required behavior, uncertainty handling, fake completion claims, and hallucinated tool-use claims.

Regression is currently against a deterministic baseline snapshot. It is useful for catching unintended pipeline or scoring drift, not for measuring real model performance.

## How To Run The Quality Gate

From the repository root:

```bash
python3 scripts/check_all.py
```

The quality gate runs local unit tests, schema validation, mock eval generation, trace count verification, baseline report generation, profile comparison report generation, regression snapshot checking, failure inspection report generation, and Python compile checks.

## Current Quality Gate Summary

Current deterministic gate expectations:

- Unit tests: 29 tests
- Eval cases validated: 30
- Scored trace records validated: 90
- Mock eval records generated: 90
- Baseline pass/fail: 82 passed, 8 failed
- Regression snapshot comparison: passed
- Failure inspection records: 8 failed records

All checks use local standard-library code. The gate does not call real model APIs, execute OpenClaw, use external services, or perform browser, email, or autonomous actions.

## What This Milestone Proves

Milestone 2 proves that the lab can:

- Compare deterministic profile behavior from scored traces.
- Preserve a stable aggregate regression snapshot.
- Detect unintended aggregate drift against the saved baseline.
- Inspect failed records without manually parsing JSONL.
- Protect the v0 heuristic scorer with broader edge-case tests.
- Keep generated comparison and inspection artifacts reproducible.

This strengthens the evaluator layer while keeping the system general. OpenClaw remains one possible future system under test, not the purpose of the repository.

## Known Limitations

- The system still uses deterministic mock outputs.
- The scorer is still v0 heuristic-based and intentionally simple.
- The regression check compares aggregate snapshot values, not full semantic behavior.
- The comparison reports do not yet compare arbitrary previous-vs-current trace files.
- No real model adapters are active yet.
- No saved transcript replay exists yet.
- No live OpenClaw execution happened.
- Results should not be interpreted as production model, local model, or agent benchmark results.

## Next Recommended Milestone

Milestone 3 should prepare controlled real-output evaluation, not full real agent execution yet.

Suggested focus:

- Saved transcript replay.
- Adapter contract refinement.
- Real model adapter design document.
- Manual-output evaluation mode.
- Stronger scorer and rubric alignment.

The next milestone should make it possible to evaluate real outputs under controlled, reviewable conditions before adding live adapters or agent runtimes.
