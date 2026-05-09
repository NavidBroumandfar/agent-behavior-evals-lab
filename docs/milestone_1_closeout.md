# Milestone 1 Closeout

## Milestone Name

Milestone 1: v0 deterministic mock evaluation harness.

## Completion Status

Complete for the local deterministic mock harness. The repository has enough policy, case, target, scoring, trace, reporting, schema, rubric, and test coverage to validate the evaluator pipeline end to end before real model adapters are introduced.

This milestone is not a real model benchmark. No live OpenClaw execution happened, and no real model adapters are active yet.

## Artifacts Completed

- Behavior policy: `policy/agent_behavior_policy.md`
- Failure taxonomy: `evals/failure_taxonomy.md`
- Eval cases: 30 JSONL cases across four categories in `evals/cases/`
- Human review rubrics: `evals/rubrics/*.yaml`
- Target profiles: `targets/profiles/*.md`
- Target prompts: `targets/prompts/*.md`
- Schema contracts: `schemas/eval_case.schema.json` and `schemas/trace.schema.json`
- Mock model client: `src/model_clients.py`
- Rule-based v0 scorer: `src/scorers.py`
- Eval runner and trace writer: `src/run_eval.py` and `src/trace_writer.py`
- Report generator: `src/report_generator.py`
- Schema validator: `src/validate_schemas.py`
- Unit tests: `tests/`
- Local quality gate: `scripts/check_all.py`
- Baseline trace: `traces/scored/baseline_mock_run.jsonl`
- Baseline report: `reports/baseline_report.md`

## What The Harness Currently Evaluates

The v0 harness evaluates assistant outputs against four behavior categories:

- `safe_direct_response`: direct answers to safe informational, writing, summarization, planning, explanation, and reasoning tasks.
- `approval_gated`: consequential actions that require explicit approval and risk/scope disclosure before proceeding.
- `refusal_required`: harmful, deceptive, unauthorized, privacy-invasive, or unsafe requests that should be refused.
- `uncertainty_handling`: missing artifacts, data, source context, prior discussion, or decision constraints where the assistant should not invent facts.

Each case links behavior expectations to `policy_refs`, `expected_failure_modes`, `severity`, and `scoring_notes`.

## How To Run The Quality Gate

From the repository root:

```bash
python3 scripts/check_all.py
```

The quality gate runs unit tests, schema validation, mock eval generation, trace count verification, baseline report generation, and Python compile checks. It uses only local deterministic code and does not call real model APIs, use the network, execute OpenClaw, or perform external actions.

## Baseline Mock Run Summary

Current baseline run:

- Run ID: `baseline_mock_run`
- Eval cases loaded: 30
- Profiles evaluated: 3
- Scored trace records: 90
- Output trace: `traces/scored/baseline_mock_run.jsonl`
- Report: `reports/baseline_report.md`
- Passed: 82
- Failed: 8
- Pass rate: 91.1%

Profile-level summary from the baseline report:

- `generic_assistant`: 25 passed, 5 failed
- `openclaw_reference_agent`: 30 passed, 0 failed
- `strict_approval_agent`: 27 passed, 3 failed

The failures are intentional mock-profile signals: the generic assistant misses some approval gates, and the strict approval profile over-gates some safe tasks.

## What This Milestone Proves

Milestone 1 proves that the lab can:

- Load policy-mapped JSONL eval cases.
- Simulate multiple target profiles deterministically.
- Score responses with a transparent v0 rule-based scorer.
- Preserve traceability from case fields into scored traces.
- Generate a Markdown baseline report from scored JSONL.
- Validate current case and trace schemas without external dependencies.
- Run local tests and quality checks with one command.

This establishes the evaluator pipeline mechanics, not real assistant quality.

## Known Limitations

- The mock client is deterministic and deliberately simplified.
- The scorer is v0 heuristic-based and intentionally simple.
- Results should not be interpreted as real model performance.
- No real model adapters are active yet.
- No saved transcript replay exists yet.
- No live OpenClaw execution happened.
- The current report reflects one generated mock trace, not a benchmark suite.
- Schema validation covers the repository's current contract subset, not a full JSON Schema engine.

## Next Recommended Improvements

- Add configurable run inputs and output paths.
- Expand unit tests around scorer false positives and false negatives.
- Add comparison reports across multiple runs, profiles, and future adapters.
- Add saved transcript replay for evaluating recorded assistant outputs.
- Add real model adapters after the mock harness stays stable.
- Add a controlled OpenClaw adapter later as one system under test.
- Keep rubrics and policy refs synchronized as the case set expands.
