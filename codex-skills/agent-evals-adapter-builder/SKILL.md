---
name: agent-evals-adapter-builder
description: Use when building or reviewing Agent Behavior Evals Lab adapters, saved-output importers, transcript bridges, or local harness integrations.
---

# Agent Evals Adapter Builder

Use this workflow for target-system bridges.

## Boundary

Adapters collect or normalize target outputs. The evaluator owns cases,
scoring, traces, reports, ledgers, and claim boundaries.

## Adapter Rules

- Emit normalized public-safe adapter-output records.
- Keep raw outputs local and ignored until reviewed.
- Include provenance, source, model/runtime, and execution-mode metadata.
- Do not include credentials, private traces, private memory, hidden prompts, or
  customer data in committed fixtures.
- Live local or provider execution must be opt-in and outside the deterministic
  quality gate.

## Validation

Use existing validators before scoring:

```bash
python3 src/validate_adapter_outputs.py <path>
python3 src/import_adapter_outputs.py <path>
```

For reviewed live-local evidence, use the explicit live-local opt-in flags
already required by the validator/importer.
