# Milestone 44 - Optional Non-Gated Runtime Trial

Date: 2026-06-20

Status: Complete / review-ready

Milestone 44 adds a validation-only optional runtime-trial plan for one prepared public-safe prompt.

M44 does not add live provider execution, local model execution, live Hermes or OpenClaw execution, CLI-agent execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, shell execution, autonomous actions, private runtime-log ingestion, scorer changes, gated LLM review, private output collection, runtime harness execution, raw-output promotion, or deterministic scoring of local runtime output.

## Completed Slices

- M44.1 Added `schemas/runtime_trial_plan.schema.json`.
- M44.2 Added `traces/external/non_gated_runtime_trial_plan.example.json`.
- M44.3 Added `traces/external/non_gated_runtime_trial_metadata.example.json`.
- M44.4 Added `src/validate_runtime_trial_plan.py`.
- M44.5 Added `tests/test_runtime_trial_plan_validation.py`.
- M44.6 Added `targets/adapters/non_gated_runtime_trial.md`.
- M44.7 Wired plan validation, metadata validation, schema coverage, and compile coverage into `scripts/check_all.py`.
- M44.8 Updated release notes, roadmap, wiki docs, and schema coverage documentation.

## Key Artifacts

Code and tests:

- `src/validate_runtime_trial_plan.py`
- `tests/test_runtime_trial_plan_validation.py`
- `tests/test_adapter_run_metadata_validation.py`
- `scripts/check_all.py`

Schemas, plans, and metadata:

- `schemas/runtime_trial_plan.schema.json`
- `traces/external/non_gated_runtime_trial_plan.example.json`
- `traces/external/non_gated_runtime_trial_metadata.example.json`
- `targets/adapters/non_gated_runtime_trial.md`

Docs:

- `docs/wiki/concepts/non_gated_runtime_trial.md`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/roadmap.md`
- `docs/wiki/index.md`

## Prepared Trial Shape

- Target runtime: `openclaw`
- Target profile: `openclaw_reference_agent`
- Prepared prompt count: 1
- Case ID: `APPROVAL-014`
- Raw output path if a future manual trial is approved: `traces/raw/m44_non_gated_runtime_trial.local.jsonl`
- Reviewed output candidate path: `traces/external/m44_non_gated_runtime_trial.reviewed.jsonl`
- Promotion format: adapter-output JSONL

The committed plan is public-safe metadata only. No raw output is committed.

## Closeout Decision

Decision: `defer_live_runtime_trial`

Runtime-native evidence needed: `false`

Current saved-output, saved-transcript, fixture, adjudication, calibration, and trend artifacts are enough for the evaluator-health goal. A live runtime trial is not required for M44.

## Promotion Path

If a future human-approved manual trial is run, raw output must stay local-only and disposable. A reviewed output candidate may be proposed only after sanitization and review, then validated with:

```bash
python3 src/validate_adapter_outputs.py traces/external/m44_non_gated_runtime_trial.reviewed.jsonl
```

If accepted, it can be imported and scored through the existing reviewed-output path:

```bash
python3 src/import_adapter_outputs.py traces/external/m44_non_gated_runtime_trial.reviewed.jsonl
```

Promotion would require separate fixture manifest updates, report regeneration, and quality-gate validation.

## Boundary

The deterministic quality gate validates the M44 plan and metadata. It does not run OpenClaw, Hermes, a CLI agent, a provider, a local model, shell, browser, email, network collection, or external actions.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

Proceed to M45 External Fixture Adjudication Coverage. The next useful phase is reviewed evidence depth for public-safe transcript and adapter-output fixture groups before any runtime-native collection.
