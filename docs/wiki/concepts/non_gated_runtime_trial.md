# Non-Gated Runtime Trial

M44 defines an optional runtime-trial path without adding runtime execution to the deterministic quality gate.

Generated or committed planning artifacts:

- Plan schema: `schemas/runtime_trial_plan.schema.json`
- Plan validator: `src/validate_runtime_trial_plan.py`
- Plan example: `traces/external/non_gated_runtime_trial_plan.example.json`
- Adapter metadata: `traces/external/non_gated_runtime_trial_metadata.example.json`
- Procedure: `targets/adapters/non_gated_runtime_trial.md`

## Current Decision

The current decision is `defer_live_runtime_trial`.

Runtime-native evidence is not needed yet. The lab should continue to prefer saved outputs, saved transcripts, normalized adapter outputs, adjudications, calibration, and trend snapshots before collecting runtime-native evidence.

## Trial Boundary

A future trial must be:

- Manual.
- Non-gated.
- Disposable.
- One prepared public-safe prompt.
- Tools disabled.
- Network, shell, browser, email, messaging, purchase, deployment, and file-mutation actions blocked.
- Reviewed and sanitized before promotion.

The quality gate validates the plan and metadata only. It does not run OpenClaw, Hermes, a CLI agent, provider, local model, shell, browser, email, network collection, or external actions.

## Promotion Path

Raw runtime output must stay under ignored local paths such as `traces/raw/*.local.jsonl`.

Reviewed output may only be proposed through an existing fixture format:

- Adapter-output JSONL validated by `src/validate_adapter_outputs.py`.
- Imported for scoring by `src/import_adapter_outputs.py`.
- Manifested and reported only after public-safe review.

Until that promotion happens, the runtime trial is not deterministic scored evidence and is not a benchmark claim.
