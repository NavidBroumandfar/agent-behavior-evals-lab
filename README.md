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

See `docs/milestone_1_closeout.md` for the Milestone 1 closeout summary, `docs/milestone_2_closeout.md` for the regression and comparison layer closeout, `docs/milestones/m3-controlled-real-output-prep-closeout.md` for the controlled real-output preparation closeout, and `docs/wiki/index.md` for the project-local evaluator wiki.

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
  adapters/                     # Public adapter contracts for future target systems

src/
  model_clients.py              # Deterministic MockModelClient
  scorers.py                    # Rule-based v0 scorer
  run_eval.py                   # End-to-end mock eval runner
  evaluate_manual_outputs.py    # Manual saved-output eval runner
  replay_saved_transcripts.py   # Saved transcript replay runner
  validate_adapter_outputs.py   # Normalized adapter-output fixture validator
  trace_writer.py               # JSONL trace writer
  report_generator.py           # Markdown report generator
  comparison_report.py          # Profile comparison report generator
  regression_check.py           # Baseline regression snapshot checker
  inspect_failures.py           # Failure inspection report generator

traces/
  external/
    manual_outputs.example.jsonl # Public-safe manual output fixture
    openclaw_manual_samples.example.jsonl # Public-safe OpenClaw-style fixture
    saved_transcripts.example.jsonl # Public-safe saved transcript fixture
    adapter_outputs.example.jsonl # Public-safe normalized adapter-output fixture
  scored/
    baseline_mock_run.jsonl     # Generated scored trace records
    manual_output_eval.jsonl    # Generated manual-output scored traces
    openclaw_manual_eval.jsonl  # Generated OpenClaw-style manual traces
    saved_transcript_replay_eval.jsonl # Generated transcript replay traces

reports/
  baseline_report.md            # Generated baseline report
  comparisons/
    profile_comparison_report.md # Generated profile comparison report
    baseline_regression_snapshot.json # Saved deterministic regression snapshot
    failure_inspection.md       # Generated failure inspection report
    manual_output_report.md     # Generated manual-output report
    openclaw_manual_eval_report.md # Generated OpenClaw-style manual report
    saved_transcript_replay_report.md # Generated transcript replay report

schemas/
  eval_case.schema.json         # Planned schema validation support
  trace.schema.json             # Planned trace schema support
  saved_transcript.schema.json  # Saved transcript replay input contract
  adapter_output.schema.json    # Normalized adapter-output input contract
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

Adapter expectations are documented in `targets/adapters/adapter_contract.md`. The contract keeps target-side output collection separate from evaluator-side scoring, trace writing, reporting, and deterministic quality gates.

Future real model adapter design is documented in `targets/adapters/real_model_adapter_design.md`; it is a design note only and does not add live provider calls.

## Running The Baseline

From the repository root:

```bash
python3 src/run_eval.py
python3 src/report_generator.py
python3 src/comparison_report.py
python3 src/regression_check.py
python3 src/inspect_failures.py
```

Expected baseline output:

- 30 cases loaded
- 3 profiles evaluated
- 90 scored records written
- scored traces at `traces/scored/baseline_mock_run.jsonl`
- Markdown report at `reports/baseline_report.md`
- profile comparison report at `reports/comparisons/profile_comparison_report.md`
- regression snapshot check against `reports/comparisons/baseline_regression_snapshot.json`
- failure inspection report at `reports/comparisons/failure_inspection.md`

The runner uses `MockModelClient` and `score_response`; it does not call a real LLM, use the network, execute tools, send messages, delete files, or run OpenClaw.

## Manual Output Mode

Manual output mode evaluates assistant or model text saved in local JSONL. Each input record must include `case_id`, `target_profile`, and `model_output`; optional public-safe fields are `source_label` and `notes`.

From the repository root:

```bash
python3 src/evaluate_manual_outputs.py
```

Default input is `traces/external/manual_outputs.example.jsonl`. The command writes scored traces to `traces/scored/manual_output_eval.jsonl` and a report to `reports/comparisons/manual_output_report.md`. It reuses the local cases and deterministic scorer; it does not call real APIs, run live adapters, execute OpenClaw, or use browser/email/external tools.

The public OpenClaw-style sample uses the same evaluator with custom paths:

```bash
python3 src/evaluate_manual_outputs.py \
  --input traces/external/openclaw_manual_samples.example.jsonl \
  --output traces/scored/openclaw_manual_eval.jsonl \
  --report reports/comparisons/openclaw_manual_eval_report.md \
  --run-id openclaw_manual_eval_example \
  --report-title "Public OpenClaw-Style Manual Evaluation Report" \
  --report-context "This public-safe sample treats sanitized OpenClaw-inspired outputs as one system under test. The records are fictional examples based on behavior principles such as approval gates, safe stopping, uncertainty handling, refusal boundaries, no fabricated tool use, and no fake completion claims; no live execution or private runtime data is used."
```

## Saved Transcript Replay

Saved transcript replay scores a selected assistant turn from each static transcript fixture. Each input record includes `transcript_id`, `case_id`, `target_profile`, `turns`, and zero-based `assistant_turn_index`.

From the repository root:

```bash
python3 src/replay_saved_transcripts.py
```

Default input is `traces/external/saved_transcripts.example.jsonl`. The command writes scored traces to `traces/scored/saved_transcript_replay_eval.jsonl` and a report to `reports/comparisons/saved_transcript_replay_report.md`.

## Normalized Adapter Output Validation

Normalized adapter outputs are saved target-side records validated before any future importer or scorer consumes them. The example fixture is `traces/external/adapter_outputs.example.jsonl`, the documented contract is `schemas/adapter_output.schema.json`, and the validator is standard-library only.

From the repository root:

```bash
python3 src/validate_adapter_outputs.py traces/external/adapter_outputs.example.jsonl
```

This validation does not call real APIs, run local models, execute OpenClaw, use browser/email/external tools, import records, score records, or write generated artifacts.

## Local Quality Gate

From the repository root:

```bash
python3 scripts/check_all.py
```

This runs the local unit tests, schema validation, adapter-output fixture validation, mock eval generation, baseline report generation, profile comparison report generation, regression snapshot checking, failure inspection report generation, manual output eval generation, OpenClaw-style manual eval generation, saved transcript replay generation, Python compile checks, and trace count verification for `traces/scored/baseline_mock_run.jsonl`, `traces/scored/manual_output_eval.jsonl`, `traces/scored/openclaw_manual_eval.jsonl`, and `traces/scored/saved_transcript_replay_eval.jsonl`.

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
