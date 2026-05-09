# Eval Case Anatomy

An eval case is one JSON object in `evals/cases/*.jsonl`. It describes a prompt, the expected behavior, and the policy and scoring context needed to judge a response.

## Required Fields

- `case_id`: stable identifier used in traces and reports.
- `category`: one of `safe_direct_response`, `approval_gated`, `refusal_required`, or `uncertainty_handling`.
- `user_prompt`: the input being tested.
- `expected_behavior`: the desired assistant behavior in plain language.
- `policy_refs`: references into `policy/agent_behavior_policy.md`.
- `expected_failure_modes`: likely failure labels from `evals/failure_taxonomy.md`.
- `severity`: expected consequence level: `low`, `medium`, `high`, or `critical`.
- `scoring_notes`: case-specific interpretation guidance.

The required contract is captured in `schemas/eval_case.schema.json` and checked by `src/validate_schemas.py`.

## How Cases Flow Through The Harness

`src/run_eval.py` loads all configured case files, passes each case to each mock profile in `src/model_clients.py`, scores each response with `src/scorers.py`, and writes scored records to `traces/scored/baseline_mock_run.jsonl`.

The scored trace keeps the original prompt, expected behavior, policy refs, expected failure modes, severity, and scoring notes. That makes each report row auditable back to the source case.

## Current Scope

Milestone 1 has 30 cases across four categories. These cases validate evaluator mechanics against deterministic mock outputs; they are not yet a live benchmark of real models or agents.
