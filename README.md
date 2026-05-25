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

See `docs/milestone_1_closeout.md` for the Milestone 1 closeout summary, `docs/milestone_2_closeout.md` for the regression and comparison layer closeout, `docs/milestones/m3-controlled-real-output-prep-closeout.md` for the controlled real-output preparation closeout, `docs/milestones/m4-adapter-readiness-closeout.md` for the adapter readiness closeout, `docs/milestones/m5-adapter-contract-hardening-closeout.md` for the adapter contract hardening closeout, `docs/milestones/m6-controlled-adapter-sandbox-closeout.md` for the controlled adapter sandbox closeout, `docs/milestones/m7-text-only-saved-output-collector-closeout.md` for the text-only saved-output workflow closeout, `docs/milestones/m8-reviewed-output-promotion-closeout.md` for the reviewed output promotion closeout, `docs/milestones/m9-adjudication-and-trace-comparison-closeout.md` for the adjudication and trace comparison closeout, `docs/milestones/m10-adjudication-aware-reporting-closeout.md` for the adjudication-aware reporting closeout, `docs/milestones/m11-reporting-regression-hardening-closeout.md` for the reporting regression hardening closeout, `docs/milestones/m12-reviewed-adjudication-coverage-closeout.md` for the reviewed adjudication coverage closeout, `docs/milestones/m13-multiple-adjudication-fixtures-closeout.md` for the multiple adjudication fixture families closeout, `docs/milestones/m14-adjudication-fixture-status-governance-closeout.md` for the adjudication fixture status governance closeout, `docs/milestones/m15-status-aware-adjudication-thresholds-closeout.md` for the status-aware adjudication thresholds closeout, `docs/milestones/m16-manifest-quality-gate-thresholds-closeout.md` for the manifest-declared adjudication quality-gate thresholds closeout, `docs/milestones/m17-adjudication-manifest-schema-hardening-closeout.md` for the adjudication manifest schema hardening closeout, `docs/milestones/m18-manifest-validator-report-loader-integration-closeout.md` for the manifest validator/report loader integration closeout, `docs/milestones/m19-report-artifact-manifest-closeout.md` for the report artifact manifest closeout, `docs/milestones/m20-shared-schema-validation-helpers-closeout.md` for the shared schema validation helpers closeout, `docs/milestones/m21-schema-validator-helper-reuse-closeout.md` for the schema validator helper reuse closeout, `docs/milestones/m22-schema-validation-coverage-matrix-closeout.md` for the schema validation coverage matrix closeout, `docs/milestones/m23-target-registry-schema-helper-reuse-closeout.md` for the target registry schema helper reuse closeout, `docs/milestones/m24-saved-transcript-schema-helper-reuse-closeout.md` for the saved transcript schema helper reuse closeout, `docs/milestones/m25-adapter-output-schema-helper-reuse-closeout.md` for the adapter-output schema helper reuse closeout, `docs/milestones/m26-adjudication-schema-helper-reuse-closeout.md` for the adjudication schema helper reuse closeout, `docs/milestones/m27-adapter-run-metadata-schema-helper-reuse-closeout.md` for the adapter-run metadata schema helper reuse closeout, `docs/milestones/m28-schema-coverage-helper-enforcement-closeout.md` for the schema coverage helper enforcement closeout, and `docs/wiki/index.md` for the project-local evaluator wiki.

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

## Normalized Adapter Output Validation And Import

Normalized adapter outputs are saved target-side records validated before an importer or scorer consumes them. The example fixture is `traces/external/adapter_outputs.example.jsonl`, the documented contract is `schemas/adapter_output.schema.json`, and the validator/importer are standard-library only.

M5.2 adds optional `provenance_details` to clarify fixture origin, execution mode, data classification, and action evidence while keeping the required public-safe provenance booleans unchanged. The importer preserves those details in scored trace `mock_behavior_notes`; scoring still uses the existing `output_text` path only. See `docs/wiki/concepts/adapter_output_provenance.md`.

From the repository root:

```bash
python3 src/validate_adapter_outputs.py traces/external/adapter_outputs.example.jsonl
python3 src/import_adapter_outputs.py traces/external/adapter_outputs.example.jsonl
```

Validation writes nothing. Import writes deterministic scored traces to `traces/scored/adapter_output_fixture_import.jsonl` using the existing cases and scorer. Neither command calls real APIs, runs local models, executes OpenClaw, uses browser/email/external tools, creates a real adapter, or reads private runtime state.

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

This runs the local unit tests, schema validation, target registry validation, adapter-output fixture validation/import, dry-run adapter generation/validation/import, mock eval generation, baseline report generation, profile comparison report generation, regression snapshot checking, manifest-backed failure inspection report generation, manual output eval generation, OpenClaw-style manual eval generation, saved transcript replay generation, external fixture comparison report generation, fixture manifest validation, adapter run metadata validation, both adjudication fixture validations, manifest-backed adjudication-aware report generation, adjudication regression snapshot and threshold checking, baseline self trace comparison, report manifest validation, Python compile checks, and trace count verification for `traces/scored/adapter_output_fixture_import.jsonl`, `traces/scored/dry_run_adapter_output_import.jsonl`, `traces/scored/baseline_mock_run.jsonl`, `traces/scored/manual_output_eval.jsonl`, `traces/scored/openclaw_manual_eval.jsonl`, and `traces/scored/saved_transcript_replay_eval.jsonl`.

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
- Move review threshold policy into the adjudication manifest instead of keeping gate thresholds only in CLI arguments.
- Add controlled agent transcript capture later as one possible system under test, without making the lab OpenClaw-specific.
