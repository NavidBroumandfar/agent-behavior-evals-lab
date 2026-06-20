# Controlled Adapter Sandbox

The controlled adapter sandbox is the M6 bridge between deterministic fixture evaluation and future real adapter experiments.

It does not add live execution. It defines where live-output experiments belong, what metadata they need, and why they must stay outside the deterministic quality gate.

## Boundary

The evaluator remains deterministic:

- Cases, scoring, traces, reports, validators, and committed fixtures are quality-gated.
- Live provider calls, local model runs, CLI agents, credentials, and external actions are not quality-gated.
- Raw live outputs stay in local-only paths and are not committed.
- Reviewed public-safe outputs can later be normalized and imported through the existing adapter-output path.

## New M6 Artifacts

- Sandbox policy and approval checklist: `targets/adapters/controlled_adapter_sandbox.md`
- Adapter run metadata schema: `schemas/adapter_run_metadata.schema.json`
- Public-safe metadata example: `traces/external/adapter_run_metadata.example.json`
- Metadata validator: `src/validate_adapter_run_metadata.py`
- Metadata tests: `tests/test_adapter_run_metadata_validation.py`

M27 loads the metadata schema through `src/schema_validation_utils.py` for object shape, required fields, enum values, and primitive types while keeping timestamp validity, target registry lookup, case ID checks, path boundaries, and public-safe provenance expectations local.

## M36 Local Agent Sandbox Pilot

M36 adds `src/controlled_live_agent_sandbox.py` and `traces/external/controlled_live_agent_sandbox_metadata.example.json`.

The runner is manual and non-gated. It uses the committed metadata to select `APPROVAL-014`, `REFUSAL-007`, and `UNCERTAINTY-008` for the `openclaw_reference_agent` profile, then writes pending-review raw records to an ignored `.local.jsonl` path under `traces/raw/`.

The runner refuses metadata that enables manual network collection, credentials, external actions, or unblocked tool execution. The deterministic quality gate validates the metadata and compiles the runner, but it does not run the sandbox or promote raw outputs.

Any later promotion must pass through the existing review, adapter-output validation, import, scoring, and reporting path. Raw sandbox outputs are not committable.

## Why This Matters

Without this boundary, the project could accidentally turn a deterministic evaluator into an unreliable live runner. M6 keeps the evaluator stable while making the first real adapter experiment reviewable.

The intended sequence is:

1. Plan the adapter run with metadata.
2. Collect raw output locally outside the quality gate.
3. Review and sanitize the output.
4. Normalize it into adapter-output JSONL.
5. Validate, import, score, and report with the existing evaluator.

## Agentic Readiness

The project is ready to evaluate saved outputs from agentic systems. It is not ready to let agentic systems perform live external actions inside the quality gate.

The first agentic step should be transcript capture with tools disabled or no-op, followed by saved-output review. Tool execution, browser actions, email actions, purchases, file mutation, and autonomous CLI actions require later governance.
