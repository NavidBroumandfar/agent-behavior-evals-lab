# Milestone 2 Plan

## Milestone Name

Milestone 2: Regression + Comparison Layer.

## Goal

Add comparison and regression capabilities on top of the deterministic Milestone 1 harness so the lab can detect behavior differences across profiles now, and later across runs, prompts, model versions, or agent adapters.

## Why This Milestone Matters

Milestone 1 proves that the evaluator can produce stable scored traces and reports. Milestone 2 should make those traces useful for change detection. The lab needs a way to answer practical questions such as:

- Which profile performs better or worse by category?
- Which failure modes changed between two runs?
- Did a scorer, prompt, profile, or case change improve behavior or introduce regressions?
- Which specific case/profile pairs need human inspection?

This keeps the repository oriented around evaluation quality rather than any single system under test. OpenClaw remains one possible future target, not the purpose of the lab.

## Current Baseline From Milestone 1

Milestone 1 is complete and tagged as `v0.1.0-mock-harness`.

Current baseline:

- Deterministic mock harness only.
- 30 eval cases across four categories.
- 3 simulated profiles.
- 90 scored trace records in `traces/scored/baseline_mock_run.jsonl`.
- Baseline report in `reports/baseline_report.md`.
- v0 heuristic scorer in `src/scorers.py`.
- Local quality gate in `scripts/check_all.py`.

The baseline is not a real model benchmark. No live OpenClaw execution has happened, and no real model adapters are active.

## Proposed Deliverables

- Profile comparison report derived from existing scored traces.
- Comparison report generator, likely `src/comparison_report_generator.py`.
- Regression snapshot artifact that records expected aggregate metrics for a known baseline.
- Previous-vs-current comparison logic for detecting pass/fail, category, profile, and failure-mode changes.
- Scorer edge-case tests for known heuristic boundaries.
- Failure inspection helper for listing failed case/profile records with rationale and source fields.
- README, report, and closeout documentation updates only where needed.

## Recommended Implementation Slices

### M2.1: Profile Comparison Report From Existing Baseline Traces

Generate a Markdown report that compares the three current profiles using `traces/scored/baseline_mock_run.jsonl`. Start with profile totals, category breakdowns, failure-mode distribution by profile, and notable profile differences.

### M2.2: Regression Snapshot File

Add a small project-local snapshot artifact that captures expected aggregate counts for the deterministic baseline. Keep it human-readable and stable, such as JSON with run ID, trace count, profile counts, category counts, pass/fail totals, and failure-mode counts.

### M2.3: Previous-Vs-Current Comparison Command

Add comparison logic that accepts two scored trace files or one snapshot plus one current trace. It should report new failures, resolved failures, changed scores, changed failure modes, and aggregate deltas.

### M2.4: Scorer Edge-Case Test Expansion

Add focused unit tests around approval phrasing, incomplete risk disclosure, false completion claims, hallucinated tool use, over-refusal, unsafe compliance, and uncertainty handling. These tests should protect the v0 scorer from accidental behavior drift without claiming the scorer is semantically complete.

### M2.5: Failure Inspection Helper

Add a small helper command that prints or writes concise failure details for review: case ID, profile, category, severity, failure modes, rationale, policy refs, user prompt, expected behavior, and model output.

### M2.6: README And Closeout Update

Update README and closeout documentation after the comparison layer is implemented. Keep documentation concise and clear about mock-vs-real status.

## Acceptance Criteria

- Existing Milestone 1 quality gate still passes.
- Baseline mock trace remains deterministic with 90 records.
- Profile comparison report can be regenerated from the existing baseline trace.
- Regression snapshot is deterministic and reviewable.
- Previous-vs-current comparison can detect changed pass/fail outcomes and aggregate deltas.
- Failure inspection helper exposes enough context for human review without requiring manual JSONL parsing.
- Scorer edge-case tests cover the highest-risk heuristic boundaries.
- Documentation accurately states that this is still a mock harness, not a real benchmark.

## Known Constraints

- Do not add real model APIs yet.
- Do not add live OpenClaw execution.
- Do not add external services.
- Do not add browser, email, or autonomous actions.
- Keep standard-library-only unless a strong reason is documented.
- Keep the lab general, not OpenClaw-only.
- Do not over-engineer the comparison layer before real adapter needs are known.

## What Should Not Be Added Yet

- Real LLM provider integrations.
- Live agent execution or tool-use orchestration.
- OpenClaw-specific assumptions in core evaluator code.
- Network calls, hosted dashboards, databases, queues, or external storage.
- Broad governance workflows beyond the current policy, cases, traces, and reports.
- Statistical benchmarking claims or leaderboard framing.
- Complex plugin architecture for adapters before the trace and comparison contracts stabilize.

## Suggested Next First Slice

Start with M2.1: generate a profile comparison report from `traces/scored/baseline_mock_run.jsonl`.

This slice is low risk because it uses the existing deterministic trace, requires no new runtime behavior, and immediately makes Milestone 1 results more useful. It also clarifies the aggregate shapes needed for M2.2 snapshots and M2.3 previous-vs-current comparisons.
