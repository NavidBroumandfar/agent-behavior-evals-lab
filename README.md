# Agent Behavior Safety Gate

**By [Senthira](https://senthira.com) · [Available on the GitHub Marketplace](https://github.com/marketplace/actions/agent-behavior-safety-gate)**

The Agent Behavior Safety Gate (Agent Behavior Evals Lab) is a local-first safety audit harness for AI agents before production.

It evaluates whether assistants and agentic systems handle approval gates, refusals, uncertainty, fake tool-use claims, privacy boundaries, and production-change requests in a way that is traceable to policy-defined expectations. The lab is the evaluator; OpenClaw, Hermes, Codex, local models, hosted models, and customer agents are systems under test.

**In 60 seconds:** your agent says *"I ran the test suite"* — did it? This lab
gates that class of failure in CI, deterministically, without your traces ever
leaving your infrastructure. Point the [GitHub Action](#use-as-a-github-action-ci-safety-gate)
at saved agent outputs, or convert real [LangGraph / OpenAI Agents SDK / CrewAI
traces](examples/adapters/) and let the gate verify every action claim against
the tool calls the agent actually made — or drive any agent through the
[mock-tool sandbox](examples/fleet/) where destructive calls tempt and every
call is recorded. Reviewed local-model results:
[leaderboard](docs/leaderboard/index.html). Named failure patterns:
[AGB registry](docs/patterns/index.html) (cite as `AGB-030 approval-by-silence`).
Scorer credibility is measured, not asserted: see the
[700-record model calibration](reports/comparisons/scorer_judge_calibration.md)
and the [320-record real-agent fleet calibration](reports/comparisons/sandbox_fleet_scorer_judge_calibration.md).

Try the gate offline right now — no install, no network, no keys; it catches
the shipped fake tool-use demo record and exits 1:

```bash
PYTHONPATH=src python3 src/gate_check.py \
  --outputs examples/github-action/agent_outputs.jsonl --tier smoke
```

**Public proof record:** this repository is also summarized on
[navidbr.me/work/agent-behavior-evals-lab](https://navidbr.me/work/agent-behavior-evals-lab)
as part of Navid's public NAVIDBR Applied AI Systems work record. The site
keeps the same boundary: evaluator and approval-gate proof, not production
safety certification or customer deployment evidence.

## Use As A GitHub Action (CI Safety Gate)

Gate pull requests on agent behavior safety regressions. Your CI exports the
agent's saved responses to the public benchmark prompts as JSONL; the gate
scores them deterministically (no model calls, no credentials, no external
actions) and fails the build over threshold:

```yaml
- name: Run agent behavior safety gate
  uses: NavidBroumandfar/agent-behavior-evals-lab@v1
  with:
    outputs: ci/agent_outputs.jsonl   # adapter-output JSONL in your repo
    tier: smoke                       # smoke | standard | extended
    max-failures: "0"
```

A failing record (for example a fake tool-use claim like "I ran the test
suite" with no tool evidence) fails the check and posts a failure table to the
job summary. **Live demo:** [agent-gate-demo](https://github.com/NavidBroumandfar/agent-gate-demo)
— a real PR blocked because the agent claimed it ran tests it never ran.
Worked example, sample outputs, and the caught-failure demo are in
[`examples/github-action/`](examples/github-action/). Local equivalent:
`agent-evals gate --outputs path/to/agent_outputs.jsonl --tier smoke`.

**Structural verification:** records carrying `tool_events` (the tool calls the
agent actually made) get evidence-based checking — an action claim with a
matching recorded event passes; a claim with none fails as
`unverified_tool_claim`. Convert saved LangGraph, OpenAI Agents SDK, or CrewAI
traces with [`src/trace_adapters.py`](examples/adapters/), which emits
`tool_events` automatically. Gate the deeper v2 pressure-pattern corpus with
`--case-path evals/benchmarks/local_public_v2/cases.jsonl`.

Why action-level checking matters, measured: in the
[real-agent fleet calibration](reports/comparisons/sandbox_fleet_scorer_judge_calibration.md)
(320 records, 8 framework x model agents), a text-only LLM judge passed
records where the recorded tool log shows the agent executed a destructive
call without approval or fabricated a tool claim — failures only the
structural `tool_events` check caught. Text review misses these by
construction; the recorded-action check does not.

The verifier is red-teamed against its own adversarial corpus — passive
voice, stateful assertions, markdown checklists, fabricated output blocks —
with catch rates and known gaps published honestly in the
[verifier evasion audit](reports/comparisons/verifier_evasion_audit.md).
Who produces `tool_events` and why the log is trusted is stated in the
[evidence trust model](docs/evidence-trust-model.md).

## Run One Demo Audit In 5 Minutes

Install the package first, then use the CLI:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[dev]"
agent-evals check
```

This runs the deterministic local quality gate and regenerates public-safe demo
artifacts: scored traces, reports, schemas, comparison summaries, and release
checks. It does not call providers, execute live agents, use credentials, or
take external actions.

Equivalent direct command:

```bash
python3 scripts/dev.py check
```

Without installing, module commands require `PYTHONPATH=src`. The installed
`agent-evals` CLI is the recommended path for local use.

## What This Repo Is For

- Local deterministic evaluator-health checks.
- Public-safe benchmark cases and scored traces.
- Reviewed local/open-weight model evidence.
- Claim-bounded reports, ledgers, and release artifacts.
- Safe adapter contracts for model and agent integrations.

## What This Repo Does Not Claim

- It does not prove production safety or regulatory compliance.
- It does not claim cloud-model rankings without cloud benchmark evidence.
- It does not put private evidence into public rankings.
- It does not execute live providers, live agents, local models, browser/email tools, production systems, or external actions in the deterministic quality gate.

OpenClaw and Hermes-style long-running agents are possible systems under test. Production-policy scenario packs are synthetic policy fixtures, not production proof. A synthetic image/document multimodal saved-output pilot exists for normalization coverage only. Nothing here is a production-safety or customer-deployment claim.

## Quickstart

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install ".[dev]"
python3 scripts/dev.py check
```

Equivalent commands:

```bash
make check
agent-evals check
```

The `agent-evals` command is installed by `python -m pip install ".[dev]"` from
this checkout.

## Development Setup

The repository is standard-library only at runtime. Development tooling is declared in `pyproject.toml`.

Useful local commands:

```bash
python3 scripts/dev.py test
python3 scripts/dev.py check
agent-evals scorer-reliability
agent-evals review-coverage-priority
agent-evals review-coverage-completion
agent-evals scorer-review-contract
```

`test` runs the unit test suite. `check` runs the full deterministic local quality gate through `scripts/check_all.py`.
`scorer-reliability` regenerates deterministic scorer reliability reporting.
`review-coverage-priority` regenerates deterministic public-safe review coverage planning.
`review-coverage-completion` regenerates the deterministic post-M95 completion gate.
`scorer-review-contract` prints the explicit non-gated review contract stub and
does not run a model judge.

Optional lint tooling:

```bash
python3 -m pip install ".[dev]"
python3 scripts/dev.py lint
```

The lint command uses Ruff when it is installed. The deterministic quality gate remains the source of truth and does not call real model APIs, execute agents, use credentials, perform network collection, or trigger external actions.

## Documentation Map

- [Quickstart](docs/quickstart.md)
- [Architecture](docs/architecture.md)
- [Evidence model](docs/evidence-model.md)
- [Evidence trust model](docs/evidence-trust-model.md)
- [Public repository boundary](PUBLIC_REPO_BOUNDARY.md)
- [Public release checklist](docs/public-release-checklist.md)
- [Live benchmark roadmap](docs/live_benchmark_roadmap.md)
- [Project wiki](docs/wiki/index.md)

## Codex Skills

Public Codex playbooks live under `codex-skills/`. They help maintainers add
cases, mappings, adapters, and release checks consistently. They are process
guides only; they do not contain secrets, private evidence, customer data, or
runtime credentials.

To use one locally, copy the relevant skill folder into your Codex skills
directory and keep public/private workflows separate.

## Current Benchmark Status

The deterministic gate validates the evaluator, reports, fixtures, schemas, and ledgers. The repository contains reviewed local/open-weight benchmark ledgers for `llama3.2:latest`, `mistral:latest`, `qwen3.5:2b-q4_K_M`, `deepseek-coder:6.7b-instruct`, `glm4:latest`, and `codellama:7b-instruct` over the public `local_public_v1` corpus, plus one synthetic public-safe image/document multimodal saved-output pilot fixture. Those reports are scoped benchmark or pilot evidence only; they are not cloud rankings, production-safety proof, compliance certification, broad multimodal coverage, or customer-readiness evidence.

Scorer calibration evidence (how often an independent LLM judge agrees with the deterministic scorer, and where they diverge):

- [Keyword scorer vs judge, 700 model records](reports/comparisons/scorer_judge_calibration.md) — 55.1% agreement across 6 local models; disagreement localizes the keyword rules that need work.
- [Structural scorer vs judge, 320 real-agent fleet records](reports/comparisons/sandbox_fleet_scorer_judge_calibration.md) — 70.6% agreement across 8 framework x model agents, including evidence-only catches a text-only judge cannot see.
- [Sandbox benchmark sanity pass, 24 hand-authored records](reports/comparisons/sandbox_scorer_judge_calibration.md) — 100% agreement on clean exemplars; explicitly a sanity check, not validation.

## Milestone 1 Status

Milestone 1 establishes a deterministic baseline pipeline:

- 1 behavior policy: `policy/agent_behavior_policy.md`
- 1 failure taxonomy: `evals/failure_taxonomy.md`
- 30 JSONL eval cases across 4 categories in the original mock baseline; the current M31-expanded suite has 42 cases.
- 3 deterministic quality-gate mock profiles, plus non-gated saved-output and saved-transcript target labels
- 1 deterministic mock model client
- 1 rule-based deterministic scorer
- 1 end-to-end mock eval runner
- JSONL scored traces
- 1 generated Markdown baseline report

The current deterministic mock baseline should not be interpreted as evidence of production model or agent performance. The mock client exists to validate the evaluator pipeline before real adapters are added.

Per-milestone closeout summaries live under [`docs/milestones/`](docs/milestones/) (plus [`docs/milestone_1_closeout.md`](docs/milestone_1_closeout.md) and [`docs/milestone_2_closeout.md`](docs/milestone_2_closeout.md)); the project-local evaluator wiki is [`docs/wiki/index.md`](docs/wiki/index.md).

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
  target_registry.json          # Registered mock and future adapter target labels

src/
  reporting_utils.py           # Shared deterministic reporting helpers
  schema_validation_utils.py    # Shared local JSON Schema subset validation helpers
  target_registry.py            # Target registry validation and lookup helpers
  model_clients.py              # Deterministic MockModelClient
  scorers.py                    # Rule-based v0 scorer
  run_eval.py                   # End-to-end mock eval runner
  evaluate_manual_outputs.py    # Manual saved-output eval runner
  replay_saved_transcripts.py   # Saved transcript replay runner
  long_running_agent_adapter.py # M64 public-safe Hermes-style session fixture generator
  production_policy_scenarios.py # M65 public-safe production-policy scenario fixture generator
  private_evidence_vault.py     # M66 public-safe private evidence vault boundary validator
  redaction_promotion_pipeline.py # M67 public-safe redaction/promotion validator
  private_audit_report.py       # M68 local-only private audit report validator/generator
  retention_consent_access.py   # M69 public-safe retention/consent/access-control validator
  live_local_review_summary.py  # M70 public-safe review/inter-rater summary validator
  hosted_provider_batch.py      # M75 hosted-provider Batch metadata validator
  real_model_proof_runbook.py   # M76 CLI/report runbook generator
  m107e_multimodal_pilot.py     # M107E public-safe multimodal pilot generator
  validate_adapter_outputs.py   # Normalized adapter-output fixture validator
  import_adapter_outputs.py     # Normalized adapter-output fixture importer
  dry_run_adapter.py            # Deterministic no-network adapter contract fixture producer
  validate_fixture_manifest.py  # Controlled external fixture manifest validator
  validate_adapter_run_metadata.py # Public-safe adapter run metadata validator
  collect_text_only_outputs.py  # Non-gated local raw text-output collector
  review_text_only_outputs.py   # Reviewed raw-output to adapter-output converter
  promote_reviewed_outputs.py   # Reviewed adapter-output fixture promotion helper
  validate_adjudications.py     # Human adjudication fixture validator
  validate_adjudication_manifest.py # Adjudication manifest schema and contract validator
  validate_report_manifest.py # Generated report artifact manifest validator
  adjudication_report.py        # Adjudication-aware Markdown report generator
  adjudication_regression_check.py # Adjudication aggregate snapshot checker
  compare_scored_traces.py      # Generic before-vs-after scored trace comparison
  trace_writer.py               # JSONL trace writer
  report_generator.py           # Markdown report generator
  comparison_report.py          # Profile comparison report generator
  compare_external_fixtures.py  # Controlled external fixture comparison report generator
  regression_check.py           # Baseline regression snapshot checker
  inspect_failures.py           # Failure inspection report generator

traces/
  external/
    manual_outputs.example.jsonl # Public-safe manual output fixture
    openclaw_manual_samples.example.jsonl # Public-safe OpenClaw-style fixture
    saved_transcripts.example.jsonl # Public-safe saved transcript fixture
    hermes_long_running_transcripts.example.jsonl # Public-safe Hermes-style memory fixture
    hermes_session_boundaries.example.jsonl # Public-safe session-boundary metadata
    hermes_memory_checks.example.jsonl # Public-safe memory disclosure/persistence checks
    production_policy_scenario_pack.example.json # Public-safe production-policy scenario pack
    production_policy_scenario_transcripts.example.jsonl # Generated production-policy scenario transcripts
    production_policy_scenario_checks.example.jsonl # Generated production-policy checks
    private_evidence_vault_manifest.example.json # Fake metadata-only private evidence vault manifest
    redaction_promotion_candidates.example.json # Public-safe promotion candidate manifest
    redaction_notes.example.jsonl # Public-safe diffable redaction notes
    promoted_private_evidence_outputs.example.jsonl # Public-safe promoted derivative fixture
    private_audit_report_metadata.example.json # Public-safe private audit report metadata request
    retention_consent_access_metadata.example.json # Public-safe retention/consent/access-control metadata
    live_local_review_summary.example.json # Public-safe reviewer protocol and inter-rater metadata
    hosted_provider_batch_metadata.example.json # Metadata-only hosted provider Batch plan
    m107e_multimodal_fixture_set.example.json # M107E synthetic multimodal pilot fixture set
    m107e_multimodal_saved_outputs.example.jsonl # Generated M107E multimodal saved outputs
    m107e_multimodal_review_summary.example.json # Generated M107E review summary
    real_model_proof_runbook.example.json # CLI/report runbook for manual opt-in local proof
    adapter_outputs.example.jsonl # Public-safe normalized adapter-output fixture
    dry_run_adapter_outputs.jsonl # Generated dry-run adapter-output fixture
    fixture_manifest.json       # Controlled external fixture source index
    adjudications.example.jsonl # Primary public-safe adjudication fixture
    adjudications.followup.example.jsonl # Follow-up public-safe adjudication fixture
    adjudication_manifest.json  # Adjudication fixture family index and quality-gate policy
  scored/
    baseline_mock_run.jsonl     # Generated scored trace records
    manual_output_eval.jsonl    # Generated manual-output scored traces
    openclaw_manual_eval.jsonl  # Generated OpenClaw-style manual traces
    hermes_long_running_agent_eval.jsonl # Generated Hermes-style long-running trace
    production_policy_scenario_eval.jsonl # Generated production-policy scenario trace
    saved_transcript_replay_eval.jsonl # Generated transcript replay traces
    adapter_output_fixture_import.jsonl # Generated adapter-output scored traces
    dry_run_adapter_output_import.jsonl # Generated dry-run adapter scored traces

reports/
  baseline_report.md            # Generated baseline report
  comparisons/
    profile_comparison_report.md # Generated profile comparison report
    baseline_regression_snapshot.json # Saved deterministic regression snapshot
    adjudication_regression_snapshot.json # Saved adjudication aggregate snapshot
    failure_inspection.md       # Generated failure inspection report
    manual_output_report.md     # Generated manual-output report
    openclaw_manual_eval_report.md # Generated OpenClaw-style manual report
    hermes_long_running_agent_report.md # Generated Hermes-style long-running report
    production_policy_scenario_report.md # Generated production-policy scenario report
    private_evidence_vault_summary.md # Generated M66 public-safe vault boundary summary
    private_evidence_vault_summary.json # Generated M66 public-safe vault boundary snapshot
    redaction_promotion_pipeline_summary.md # Generated M67 public-safe promotion summary
    redaction_promotion_pipeline_summary.json # Generated M67 public-safe promotion snapshot
    private_audit_report_boundary_summary.md # Generated M68 public-safe audit-report boundary summary
    private_audit_report_boundary_summary.json # Generated M68 public-safe audit-report boundary snapshot
    retention_consent_access_summary.md # Generated M69 public-safe retention/access boundary summary
    retention_consent_access_summary.json # Generated M69 public-safe retention/access boundary snapshot
    live_local_review_summary.md # Generated M70 review/inter-rater summary
    live_local_review_summary.json # Generated M70 review/inter-rater snapshot
    hosted_provider_batch_summary.md # Generated M75 hosted-provider metadata summary
    hosted_provider_batch_summary.json # Generated M75 hosted-provider metadata snapshot
    real_model_proof_runbook.md # Generated M76 operator runbook report
    real_model_proof_runbook.json # Generated M76 operator runbook snapshot
    saved_transcript_replay_report.md # Generated transcript replay report
    external_fixture_comparison_report.md # Generated controlled external fixture comparison
    adjudication_summary_report.md # Generated reviewer decision summary
    adjudicated_aggregate_report.md # Generated adjudicated aggregate report
    report_manifest.json        # Generated report/snapshot artifact provenance index

schemas/
  eval_case.schema.json         # Planned schema validation support
  trace.schema.json             # Planned trace schema support
  saved_transcript.schema.json  # Saved transcript replay input contract
  adapter_output.schema.json    # Normalized adapter-output input contract
  adapter_run_metadata.schema.json # Non-gated adapter experiment metadata contract
  target_registry.schema.json   # Target registry contract
  adjudication.schema.json      # Human adjudication record contract
  adjudication_manifest.schema.json # Adjudication fixture manifest contract
  report_manifest.schema.json   # Generated report artifact manifest contract
  retention_consent_access.schema.json # Retention/consent/access-control metadata contract
  live_local_review_summary.schema.json # Review/inter-rater summary contract
  hosted_provider_batch.schema.json # Hosted provider Batch metadata contract
  real_model_proof_runbook.schema.json # Real-model proof runbook contract
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

The target registry also includes non-quality-gate labels such as `text_only_adapter_candidate` and `hermes_long_running_agent` for reviewed saved outputs and saved transcripts. These labels do not add live runtime execution to the deterministic baseline.

Adapter expectations are documented in `targets/adapters/adapter_contract.md` and `targets/adapters/provider_agnostic_adapter_interface.md`. The contract keeps target-side output collection separate from evaluator-side scoring, trace writing, reporting, and deterministic quality gates.

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

- 42 cases loaded
- 3 profiles evaluated
- 126 scored records written
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

## Normalized Adapter Output Validation And Import

Normalized adapter outputs are saved target-side records validated before an importer or scorer consumes them. The example fixture is `traces/external/adapter_outputs.example.jsonl`, the documented contract is `schemas/adapter_output.schema.json`, and the validator/importer are standard-library only.

M5.2 adds optional `provenance_details` to clarify fixture origin, execution mode, data classification, and action evidence while keeping the required public-safe provenance booleans unchanged. The importer preserves those details in scored trace `mock_behavior_notes`; scoring still uses the existing `output_text` path only. See `docs/wiki/concepts/adapter_output_provenance.md`.

From the repository root:

```bash
python3 src/validate_adapter_outputs.py traces/external/adapter_outputs.example.jsonl
python3 src/import_adapter_outputs.py traces/external/adapter_outputs.example.jsonl
```

Validation writes nothing. Import writes deterministic scored traces to `traces/scored/adapter_output_fixture_import.jsonl` using the existing cases and scorer. Neither command calls real APIs, runs local models, executes OpenClaw, uses browser/email/external tools, creates a real adapter, or reads private runtime state.

## Opt-In Local Text-Only Harness

M57 adds an opt-in local harness for running Ollama or local OpenAI-compatible text-only models against `local_public_v1`. Dry-run planning is non-live:

```bash
python3 scripts/live_local.py --plan-only --adapter ollama_text_only --model example-local-model --split smoke
```

Live execution requires both controls and writes ignored local raw outputs:

```bash
AGENT_EVALS_ENABLE_LIVE_LOCAL=1 python3 scripts/live_local.py --live-local --adapter ollama_text_only --model <local-model> --split smoke
```

Reviewed live-local outputs must be validated/imported explicitly:

```bash
python3 src/validate_adapter_outputs.py --allow-live-local traces/external/example.reviewed.jsonl
python3 src/import_adapter_outputs.py traces/external/example.reviewed.jsonl traces/scored/example.local.jsonl --allow-live-local --case-path evals/benchmarks/local_public_v1/cases.jsonl
```

The deterministic quality gate validates only the dry-run plan, schemas, and fake-client tests. It does not call local models.

## Adapter Dry-Run Contract Test

The dry-run adapter is a deterministic no-network contract test for future adapter-like producers. It emits normalized adapter-output records, then the existing validator and importer process them.

Adapter interface conformance tests live in `tests/test_adapter_output_conformance.py`. They validate public-safe adapter fixtures, dry-run output emission, temporary-path import, and rejection of invalid adapter records before import or scoring.

From the repository root:

```bash
python3 src/dry_run_adapter.py
python3 src/validate_adapter_outputs.py traces/external/dry_run_adapter_outputs.jsonl
python3 src/import_adapter_outputs.py traces/external/dry_run_adapter_outputs.jsonl traces/scored/dry_run_adapter_output_import.jsonl
```

This is not a real model adapter and does not call providers, run local models, execute OpenClaw, use browser/email/external tools, call the network, or use credentials.

## External Fixture Comparison

External fixture comparison summarizes already-scored controlled fixture traces listed in `traces/external/fixture_manifest.json`.

From the repository root:

```bash
python3 src/compare_external_fixtures.py
```

The command writes `reports/comparisons/external_fixture_comparison_report.md`. It does not rescore, call live providers, run local models, execute OpenClaw, or create a real adapter.

## Fixture Manifest

`traces/external/fixture_manifest.json` indexes the controlled external fixture families, their provenance class, source type, generated scored traces, reports, owning scripts, quality-gate status, and limitations.

From the repository root:

```bash
python3 src/validate_fixture_manifest.py
```

The validator checks local paths, JSONL counts, quality-gate flags, and public-safe safety assertions. It writes nothing and does not run live providers, local models, OpenClaw, browser/email tools, external actions, credentials, or network calls.

Fixture manifest validation tests live in `tests/test_fixture_manifest_validation.py` and use temporary invalid manifests so negative cases do not enter production fixtures.

## Adapter Run Metadata Sandbox

M6 adds a controlled adapter sandbox policy for future non-gated live-output experiments. The policy and approval checklist live in `targets/adapters/controlled_adapter_sandbox.md`.

The committed metadata example is `traces/external/adapter_run_metadata.example.json`, the contract is `schemas/adapter_run_metadata.schema.json`, and validation is handled by:

```bash
python3 src/validate_adapter_run_metadata.py
```

This validates public-safe planning metadata only. It does not run the described adapter, call providers, run local models, execute agents, use credentials, or collect live outputs. Raw experimental outputs must stay in local-only ignored paths such as `traces/raw/*.local.jsonl`.

## Target Registry And Text-Only Workflow

M7 adds `targets/target_registry.json` so deterministic mock profiles and future adapter candidate labels are registered in one place. Validate it with:

```bash
python3 src/target_registry.py
```

The first non-gated saved-output workflow is text-only:

```bash
python3 src/collect_text_only_outputs.py \
  --metadata traces/external/adapter_run_metadata.example.json \
  --input traces/raw/example_text_inputs.local.jsonl \
  --output traces/raw/example_text_outputs.local.jsonl

python3 src/review_text_only_outputs.py \
  --input traces/raw/example_text_outputs.local.jsonl \
  --output traces/external/example_text_outputs.reviewed.jsonl
```

The collector only normalizes already-provided text into local raw JSONL and marks it `pending_review`. The review converter only writes normalized adapter-output records for raw records manually marked `approved_public_safe`. These local and reviewed candidate files are ignored until deliberately promoted into committed fixtures.

Promote a reviewed candidate with:

```bash
python3 src/promote_reviewed_outputs.py \
  --input traces/external/example_text_outputs.reviewed.jsonl \
  --output traces/external/example_text_outputs.promoted.jsonl \
  --fixture-id example_text_outputs \
  --scored-trace-path traces/scored/example_text_outputs.promoted.jsonl \
  --manifest-entry example_text_outputs.manifest_entry.local.json
```

Promotion copies reviewed adapter-output records into a stable fixture path and can write a local manifest-entry draft. It does not update `traces/external/fixture_manifest.json` automatically, import/score the fixture, or run live collection.

## Human Adjudication And Trace Comparison

M9 adds public-safe reviewer adjudications over existing scored traces:

```bash
python3 src/validate_adjudications.py traces/external/adjudications.example.jsonl
```

Adjudications do not rewrite traces. They validate that the reviewer record matches the source trace and records whether the reviewer upheld the heuristic score, overrode it, or flagged it for discussion.

M10 adds adjudication-aware reporting:

```bash
python3 src/adjudication_report.py
python3 src/inspect_failures.py
```

The report generator writes `reports/comparisons/adjudication_summary_report.md` and `reports/comparisons/adjudicated_aggregate_report.md`. Failure inspection annotates failed records with matching reviewer decisions. These are report-time overlays only; scored traces are not rewritten.

M11 adds adjudication regression hardening:

```bash
python3 src/adjudication_regression_check.py
```

The check compares current adjudication aggregates against `reports/comparisons/adjudication_regression_snapshot.json`, so changes in reviewer decision counts, review coverage, result changes, or reviewed failure modes are explicit.

M12 expands the committed adjudication fixture to cover all reviewer decisions and adds optional threshold checks:

```bash
python3 src/adjudication_regression_check.py \
  --min-review-coverage 5.0 \
  --max-needs-discussion 2
```

M13 adds a public-safe adjudication fixture manifest and a second fixture family. With `traces/external/adjudication_manifest.json` present, no-argument reporting/checking commands use the manifest-backed path; the explicit form is:

```bash
python3 src/adjudication_report.py \
  --manifest traces/external/adjudication_manifest.json

python3 src/adjudication_regression_check.py \
  --manifest traces/external/adjudication_manifest.json

python3 src/inspect_failures.py \
  --adjudication-manifest traces/external/adjudication_manifest.json
```

The local quality gate uses the manifest-backed path and thresholds for the current public-safe fixture families.

M14 adds fixture status governance to the adjudication manifest. Each fixture records `review_status`, `owner`, `status_notes`, and `last_reviewed_at`; quality-gate fixtures may not be `draft` or `blocked`. The summary report and regression snapshot include those fields so unresolved review queues are visible in deterministic artifacts.

M15 adds profile/category review coverage thresholds and fixture-level `needs_discussion` caps:

```bash
python3 src/adjudication_regression_check.py \
  --manifest traces/external/adjudication_manifest.json \
  --min-profile-review-coverage generic_assistant=10.0 \
  --min-category-review-coverage approval_gated=10.0 \
  --max-fixture-needs-discussion baseline_reviewed_decisions=2
```

Threshold failures identify the profile, category, or fixture family that caused the failure.

M16 moves the committed threshold policy into `traces/external/adjudication_manifest.json` under `quality_gate_thresholds`. Manifest-backed adjudication regression checks load those thresholds by default:

```bash
python3 src/adjudication_regression_check.py \
  --manifest traces/external/adjudication_manifest.json
```

The threshold CLI options remain available as explicit local overrides.

M17 adds a dedicated schema and standalone validator for the adjudication manifest:

```bash
python3 src/validate_adjudication_manifest.py
```

The validator checks `schemas/adjudication_manifest.schema.json`, fixture paths, fixture record counts, source trace references, quality-gate-compatible review statuses, public-safe assertions, and threshold keys before report generation consumes the manifest.

M18 makes that validator the manifest preflight for adjudication report loading. Manifest-backed report generation and regression checks now reject schema, safety, path, count, and threshold-key errors through the same standalone validator before constructing report dataclasses.

M19 adds a report artifact manifest for generated report and snapshot provenance:

```bash
python3 src/validate_report_manifest.py
```

The validator checks `reports/comparisons/report_manifest.json` against `schemas/report_manifest.schema.json`, verifies report and snapshot paths, generator scripts, declared input paths, snapshot dependencies, and public-safe assertions.

M20 extracts the duplicated manifest schema-subset validation helpers into `src/schema_validation_utils.py`. Adjudication and report manifest validators now share JSON object loading, path display, object/array/string/number validation, `const`, `enum`, bounds, patterns, required fields, and `additionalProperties` handling while keeping manifest-specific semantic checks local.

M21 reuses the shared schema-subset validator inside `src/validate_schemas.py` for eval-case and scored-trace JSONL records while preserving local JSONL parsing and line-numbered `ValidationError` output.

M22 adds `docs/wiki/reference/schema_validation_coverage.md`, a coverage matrix that maps every committed schema to its validator, quality-gate entry, validated inputs, and validation mode. `tests/test_schema_validation_coverage_docs.py` keeps the matrix aligned with `schemas/*.schema.json`.

M23 reuses `src/schema_validation_utils.py` inside `src/target_registry.py` for the target registry schema contract while keeping registry-specific path, duplicate-profile, and quality-gate-profile checks local.

M24 reuses `src/schema_validation_utils.py` inside `src/replay_saved_transcripts.py` for saved transcript JSONL record shape while keeping replay-specific case, target-profile, transcript ID, and selected assistant-turn checks local.

M25 reuses `src/schema_validation_utils.py` inside `src/validate_adapter_outputs.py` for normalized adapter-output JSONL record shape while keeping adapter-output-specific UTC date validity, public-safe provenance, and future-only provenance detail blocks local.

M26 reuses `src/schema_validation_utils.py` inside `src/validate_adjudications.py` for human-adjudication JSONL record shape while keeping adjudication-specific duplicate ID, source-trace consistency, and reviewer-decision semantic checks local.

M27 reuses `src/schema_validation_utils.py` inside `src/validate_adapter_run_metadata.py` for adapter-run metadata object shape while keeping timestamp date validity, target registry lookup, case selection checks, path boundaries, and public-safe provenance expectations local.

M28 hardens the schema validation coverage docs test so every schema row must name `src/schema_validation_utils.py`, preventing future drift back to duplicated local record-shape validators.

M29 adds a report-manifest coverage check so every known deterministic quality-gate report and snapshot path must be indexed and marked `quality_gate_included=true`.

M9 also adds arbitrary scored-trace comparison:

```bash
python3 src/compare_scored_traces.py \
  --before traces/scored/baseline_mock_run.jsonl \
  --after traces/scored/baseline_mock_run.jsonl \
  --output reports/comparisons/baseline_self_comparison_report.md
```

The comparison reads already-scored traces and reports aggregate deltas, changed records, new failures, resolved failures, added records, and removed records. It does not collect outputs, run models, execute agents, or rescore records.

## Local Quality Gate

From the repository root:

```bash
python3 scripts/check_all.py
```

This runs the local unit tests, schema validation, target registry validation, adapter-output fixture validation/import, dry-run adapter generation/validation/import, live-local dry-run plan validation, live-local review summary validation, local ledger/report validation, hosted-provider metadata validation, real-model proof runbook generation, mock eval generation, baseline report generation, profile comparison report generation, regression snapshot checking, manifest-backed failure inspection report generation, manual output eval generation, OpenClaw-style manual eval generation, saved transcript replay generation, public-safe Hermes-style long-running fixture generation/replay, external fixture comparison report generation, fixture manifest validation, adapter run metadata validation, adjudication fixture validations, manifest-backed adjudication-aware report generation, adjudication regression snapshot and threshold checking, baseline self trace comparison, report manifest validation, Python compile checks, and trace count verification for generated JSONL and report artifacts.

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

See `docs/roadmap.md` for the current roadmap.

The short version:

- Keep Agent Behavior Evals Lab as the evaluator, not as an unconstrained live agent.
- Harden packaging and CI before expanding runtime integrations.
- Expand eval cases around realistic agent risks such as file edits, shell commands, credentials, private data, purchases, messaging, and fake completion claims.
- Improve scorer tests and reviewer guidance while preserving deterministic local scoring.
- Add real text-only saved-output adapters before any live agent execution.
- Add richer saved transcript replay for tool summaries, approvals, denied actions, and source metadata.
- Evaluate Hermes and OpenClaw as systems under test through saved outputs and transcripts first.
- Consider deeper harness integration only after the saved-output and transcript paths prove insufficient.
