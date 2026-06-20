# Harness Bridge Decision Gate

The harness bridge decision gate is the M37 rule for deciding whether deeper Hermes, OpenClaw, CLI-agent, or future runtime integration is justified.

The current answer is no: the committed M37 plan defers harness integration because runtime-native state is not yet required. Saved transcript replay, normalized adapter-output import, reviewed saved outputs, and the M36 controlled local sandbox are enough for the current evidence goals.

## Artifacts

- Plan schema: `schemas/harness_bridge_plan.schema.json`
- Plan example: `traces/external/harness_bridge_plan.example.json`
- Validator: `src/validate_harness_bridge_plan.py`
- Adapter contract: `targets/adapters/harness_bridge_contract.md`

## Quality Gate Boundary

The deterministic quality gate validates the plan. It does not execute any harness, runtime, provider, local model, CLI agent, browser/email tool, shell command, network collector, or external action.

## Decision Rule

Use the lowest-risk evidence path that answers the evaluation question:

1. Prefer saved transcript replay when selected assistant turns and public-safe metadata are enough.
2. Prefer normalized adapter outputs when final text is enough.
3. Use the controlled local sandbox for non-gated raw-output collection drills.
4. Consider a harness bridge only when runtime-native state is necessary and cannot be represented by the previous paths.

## Promotion Boundary

Any future bridge output starts as ignored local raw output. It must be reviewed, sanitized, normalized, validated, imported, scored, and documented before promotion. Raw runtime logs, private memory, credentials, private workspace paths, hidden prompts, and external-action evidence stay out of committed fixtures.
