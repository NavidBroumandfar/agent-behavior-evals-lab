# Agent Behavior Evals Lab

Agent Behavior Evals Lab is a local evaluation harness for testing AI assistants and agentic systems against policy-defined behavior expectations. The lab is the evaluator: it defines policies, cases, target profiles, scoring rules, traces, and reports that can be reused across mock clients, real model adapters, local models, saved transcripts, and future agent integrations.

OpenClaw is only one possible future system under test. This repository is intentionally not an OpenClaw-only test folder, and the current milestone does not execute OpenClaw.

## Milestone 1 Status

Milestone 1 establishes a deterministic baseline pipeline:

- 1 behavior policy: `policy/agent_behavior_policy.md`
- 1 failure taxonomy: `evals/failure_taxonomy.md`
- 30 JSONL eval cases across 4 categories
- 3 target profiles and 3 corresponding system prompts
- 1 deterministic mock model client
- 1 rule-based deterministic scorer
- 1 end-to-end mock eval runner
- JSONL scored traces
- 1 generated Markdown baseline report

The current run is a deterministic mock evaluation. It is not a real model benchmark and should not be interpreted as evidence of production model or agent performance. The mock client exists to validate the evaluator pipeline before real adapters are added.

See `docs/milestone_1_closeout.md` for the Milestone 1 closeout summary and `docs/wiki/index.md` for the project-local evaluator wiki.

## Repository Structure

```text
policy/
  agent_behavior_policy.md      # Behavior expectations and policy references

evals/
  failure_taxonomy.md           # Reusable failure-mode labels
  cases/
    safe_task_cases.jsonl       # Safe direct-response cases
    approval_gate_cases.jsonl   # Approval-gated action cases
    refusal_cases.jsonl         # Refusal-required harm cases
    uncertainty_cases.jsonl     # Missing-context and ambiguity cases

targets/
  profiles/                     # Target behavior profiles
  prompts/                      # System prompts derived from profiles
  adapters/                     # Future adapter contract area

src/
  model_clients.py              # Deterministic MockModelClient
  scorers.py                    # Rule-based v0 scorer
  run_eval.py                   # End-to-end mock eval runner
  trace_writer.py               # JSONL trace writer
  report_generator.py           # Markdown report generator
  comparison_report.py          # Profile comparison report generator

traces/scored/
  baseline_mock_run.jsonl       # Generated scored trace records

reports/
  baseline_report.md            # Generated baseline report
  comparisons/
    profile_comparison_report.md # Generated profile comparison report

schemas/
  eval_case.schema.json         # Planned schema validation support
  trace.schema.json             # Planned trace schema support
```

## Eval Categories

The first milestone covers four behavior categories:

- `safe_direct_response`: safe informational, writing, summarization, planning, code explanation, and reasoning tasks where the assistant should answer directly.
- `approval_gated`: consequential actions where the assistant should pause, explain action scope and risk, and ask for explicit approval before proceeding.
- `refusal_required`: harmful, deceptive, unauthorized, privacy-invasive, or otherwise unsafe requests where the assistant should refuse and redirect when possible.
- `uncertainty_handling`: ambiguous or underspecified requests where the assistant should not invent missing facts and should ask a focused clarifying question or state what is missing.

## Policy-To-Eval Traceability

Each eval case is a JSONL object designed to connect user-facing behavior back to policy expectations and scoring.

Key fields:

- `category`: maps the case to one of the four behavior areas.
- `policy_refs`: links the case to policy items in `policy/agent_behavior_policy.md`.
- `expected_failure_modes`: lists relevant taxonomy failures from `evals/failure_taxonomy.md`.
- `severity`: records the expected consequence level for scoring and reporting.
- `scoring_notes`: gives case-specific guidance for interpreting pass and fail behavior.

This makes each case auditable: the user prompt, expected behavior, policy references, failure modes, severity, and scoring notes travel into the scored trace and final report.

## Target Profiles And Prompts

Milestone 1 includes three simulated target profiles:

- `generic_assistant`: a normal helpful assistant baseline that may be weaker on strict approval gates.
- `openclaw_reference_agent`: an OpenClaw-inspired reference profile emphasizing local-first behavior, approval gates, traceability, no fake completion claims, no fabricated tool use, safe stopping, and explicit escalation. It does not depend on live OpenClaw execution.
- `strict_approval_agent`: a conservative approval-focused profile that is strong on consequential-action gating but may over-gate safe tasks.

The corresponding prompts in `targets/prompts/` are concise system prompts that can later be used by mock model clients, real LLM adapters, local models, or transcript replay.

## Running The Baseline

From the repository root:

```bash
python3 src/run_eval.py
python3 src/report_generator.py
python3 src/comparison_report.py
```

Expected baseline output:

- 30 cases loaded
- 3 profiles evaluated
- 90 scored records written
- scored traces at `traces/scored/baseline_mock_run.jsonl`
- Markdown report at `reports/baseline_report.md`
- profile comparison report at `reports/comparisons/profile_comparison_report.md`

The runner uses `MockModelClient` and `score_response`; it does not call a real LLM, use the network, execute tools, send messages, delete files, or run OpenClaw.

## Local Quality Gate

From the repository root:

```bash
python3 scripts/check_all.py
```

This runs the local unit tests, schema validation, mock eval generation, baseline report generation, profile comparison report generation, Python compile checks, and trace count verification for `traces/scored/baseline_mock_run.jsonl`.

## Current Interpretation

The generated baseline report is useful for validating pipeline mechanics:

- case loading
- deterministic mock generation
- rule-based scoring
- trace writing
- aggregate reporting
- profile and category comparisons

The profile comparison is simulated. For example, the generic profile intentionally misses some approval gates, while the strict approval profile intentionally over-gates some safe tasks. That makes the current report useful for checking scorer and reporting behavior, but not for claiming real assistant quality.

## Roadmap

Near-term improvements:

- Add schema validation for eval cases and scored traces.
- Add unit tests for case loading, scoring, trace writing, and report aggregation.
- Improve scorer heuristics and document known false positives and false negatives.
- Add comparison reports across runs, profiles, and future adapters.
- Add real model adapters after the mock harness remains stable.
- Add saved transcript replay for evaluating recorded assistant outputs.
- Add a controlled OpenClaw adapter later as one system under test, without making the lab OpenClaw-specific.
