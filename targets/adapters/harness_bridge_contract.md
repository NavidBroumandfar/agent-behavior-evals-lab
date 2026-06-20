# Optional Harness Bridge Contract

M37 defines the decision gate for deeper Hermes, OpenClaw, CLI-agent, or future runtime integration.

The default decision is to defer harness integration when saved transcripts, reviewed saved outputs, normalized adapter-output import, or the controlled local sandbox provide enough evidence. A runtime-native bridge should be considered only when those paths cannot preserve required approval state, tool summaries, or other runtime-native evidence.

## Current M37 Decision

The committed decision plan is `traces/external/harness_bridge_plan.example.json`.

Current decision:

- Target runtime: `openclaw`
- Decision: `defer_harness_integration`
- Runtime-native state required: `false`

The deterministic quality gate validates this plan with `src/validate_harness_bridge_plan.py`, but it does not run a harness.

## Allowed Future Bridge Shape

A future non-gated bridge may only emit:

- Public-safe saved transcript fixtures for `src/replay_saved_transcripts.py`.
- Reviewed normalized adapter-output records for `src/validate_adapter_outputs.py` and `src/import_adapter_outputs.py`.
- Local raw pending-review JSONL under `traces/raw/*.local.jsonl`.

Raw outputs must remain ignored. Reviewed outputs must pass the normal review, sanitization, validation, import, scoring, and reporting path before any promotion.

## Blocked By Default

A harness bridge must not use or commit:

- Provider APIs, SDKs, or credentials.
- Private runtime logs, hidden prompts, private memory, or private workspace paths.
- Browser, email, messaging, purchase, deployment, shell, file-mutation, network, or external actions.
- Live harness execution inside `python3 scripts/check_all.py`.

## Reconsideration Trigger

Reconsider a non-gated bridge only when saved transcripts and normalized adapter outputs cannot preserve the evidence needed for a specific evaluation question. The bridge must remain outside the quality gate until a later milestone explicitly changes that governance.
