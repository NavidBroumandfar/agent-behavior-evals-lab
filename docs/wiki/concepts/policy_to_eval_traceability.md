# Policy-To-Eval Traceability

Policy-to-eval traceability means each testable behavior expectation can be traced from policy text to cases, scored traces, and reports.

## Trace Path

1. `policy/agent_behavior_policy.md` defines behavior expectations such as approval gating, refusals, and uncertainty handling.
2. `evals/cases/*.jsonl` turns those expectations into concrete prompts and expected behaviors.
3. `expected_failure_modes` links each case to `evals/failure_taxonomy.md`.
4. `src/scorers.py` applies deterministic v0 checks and records pass or fail.
5. `traces/scored/baseline_mock_run.jsonl` preserves the case fields, response, score, failure modes, and rationale.
6. `reports/baseline_report.md` aggregates the scored trace by profile, category, and failure mode.

## Why It Matters

Traceability keeps the evaluator reviewable. A failing report row should answer three questions without guesswork:

- What did the user ask?
- Which policy expectation applied?
- Which failure mode explains the miss?

## Current Limit

The current scorer is heuristic-based and intentionally simple. Traceability makes the result inspectable, but it does not make the score a ground-truth judgment or a real model benchmark.
