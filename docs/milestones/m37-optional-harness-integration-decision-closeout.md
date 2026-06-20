# Milestone 37 - Optional Harness Integration Decision

Date: 2026-06-20

Status: Complete / review-ready

Milestone 37 adds a local decision gate for deeper Hermes, OpenClaw, CLI-agent, or future runtime harness integration.

M37 does not add live provider execution, local model execution, live Hermes or OpenClaw execution, CLI-agent execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, shell execution, autonomous actions, private runtime-log ingestion, or harness execution inside the deterministic quality gate.

## Completed Slices

- M37.1 Added `schemas/harness_bridge_plan.schema.json` for optional harness-integration decision plans.
- M37.2 Added `traces/external/harness_bridge_plan.example.json` as the committed M37 decision plan.
- M37.3 Added `src/validate_harness_bridge_plan.py` for schema-backed local plan validation.
- M37.4 Added `tests/test_harness_bridge_plan_validation.py` for decision-rule, evidence-path, quality-gate, safety, and blocked-capability checks.
- M37.5 Added `targets/adapters/harness_bridge_contract.md` for future bridge boundaries.
- M37.6 Wired plan validation and `py_compile` coverage into `scripts/check_all.py`.
- M37.7 Updated roadmap, wiki docs, schema coverage reference, and adapter documentation.

## Current Decision

The committed M37 plan says:

- Target runtime: `openclaw`
- Decision: `defer_harness_integration`
- Runtime-native state required: `false`

Reason: the current saved transcript replay path, normalized adapter-output import path, and M36 controlled local sandbox controls are enough for the current evidence goals. A deeper harness bridge should be reconsidered only when runtime-native state is necessary and cannot be represented by saved transcripts or normalized adapter outputs.

## Key Artifacts

Code and tests:

- `src/validate_harness_bridge_plan.py`
- `tests/test_harness_bridge_plan_validation.py`
- `scripts/check_all.py`

Schemas, plans, and docs:

- `schemas/harness_bridge_plan.schema.json`
- `traces/external/harness_bridge_plan.example.json`
- `targets/adapters/harness_bridge_contract.md`
- `targets/adapters/provider_agnostic_adapter_interface.md`
- `targets/adapters/future_adapter_types.md`
- `docs/wiki/concepts/harness_bridge_decision_gate.md`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/roadmap.md`
- `docs/wiki/index.md`

## Boundary

The deterministic quality gate validates the M37 decision plan. It does not run a runtime harness.

Any future bridge must start non-gated and may only emit:

- Public-safe saved transcript fixtures.
- Reviewed normalized adapter-output records.
- Ignored local raw pending-review JSONL under `traces/raw/*.local.jsonl`.

Raw outputs must remain ignored. Reviewed outputs must pass normal review, sanitization, validation, import, scoring, and documentation before promotion.

## What Remains Intentionally Blocked

- Live Hermes, OpenClaw, hosted-model, local-model, or CLI-agent execution.
- Deep harness execution inside `python3 scripts/check_all.py`.
- Private runtime logs, hidden prompts, private memory, private workspace paths, credentials, secrets, or account identifiers.
- Browser, email, messaging, purchase, deployment, file mutation, shell execution, network collection, or other external actions.
- Treating a future bridge plan as benchmark evidence.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

Milestone 38 should start the reporting product layer: trend summaries, dashboard-ready JSON, run comparison summaries, or release-oriented report templates. It should continue to read already-scored traces and manifests rather than collecting live outputs.
