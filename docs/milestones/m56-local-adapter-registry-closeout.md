# Milestone 56 - Ollama And Local OpenAI-Compatible Adapter Registry

Date: 2026-06-21

Status: Complete / review-ready

Milestone 56 adds a machine-checked registry for future zero-cost local text-only adapter classes. It prepares the lab for Ollama and local OpenAI-compatible model runs without executing local models in the deterministic quality gate.

M56 does not add live provider execution, local model execution, live Ollama calls, live local OpenAI-compatible calls, live Hermes or OpenClaw execution, CLI-agent execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, shell execution as a system under test, autonomous actions, private runtime-log ingestion, gated LLM review, private output collection, runtime harness execution, raw-output promotion, model ranking, scorer behavior changes, or scored trace rewrites.

## Completed Slices

- M56.1 Added `targets/adapters/local_adapter_registry.json`.
- M56.2 Added `schemas/local_adapter_registry.schema.json`.
- M56.3 Added `src/validate_local_adapter_registry.py`.
- M56.4 Registered adapter classes for Ollama, local OpenAI-compatible servers, and manual saved outputs.
- M56.5 Tied the registry to `local_public_v1` and `text_only_adapter_candidate`.
- M56.6 Enforced `--live-local` and `AGENT_EVALS_ENABLE_LIVE_LOCAL` as future live-local controls.
- M56.7 Added deterministic tests for registry validation and failure cases.
- M56.8 Wired registry validation and compile coverage into `scripts/check_all.py`.
- M56.9 Updated schema coverage, wiki, roadmap, and release-note rollups.

## Key Artifacts

Registry:

- `targets/adapters/local_adapter_registry.json`
- `schemas/local_adapter_registry.schema.json`
- `src/validate_local_adapter_registry.py`
- `tests/test_local_adapter_registry.py`

Documentation:

- `docs/wiki/concepts/local_adapter_registry.md`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/live_benchmark_roadmap.md`
- `docs/roadmap.md`

## Registry Outcome

- Adapter classes: 3
- Adapters: `ollama_text_only`, `local_openai_compatible_text_only`, `manual_saved_output`
- Future live-local adapters: `ollama_text_only`, `local_openai_compatible_text_only`
- Live-local flag: `--live-local`
- Live-local enable environment variable: `AGENT_EVALS_ENABLE_LIVE_LOCAL`
- Quality-gate live execution: false
- Credentials required: false
- Tools enabled: false
- External actions allowed: false
- Case set: `local_public_v1`

## Boundary

M56 defines adapter metadata and guardrails only. It does not implement the M57 runner, call local endpoints, check model availability, or write raw outputs.

The manual saved-output adapter remains a bridge for reviewed public-safe final text. It is not a substitute for automated local model evidence and is not ranking-eligible by default under the M54 claim charter.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic, local, credential-free, and public-safe.

## Recommended Next Milestone

Proceed to M57 Opt-In Local Text-Only Model Harness. The next useful phase is adding the explicit local runner around the M56 registry, with live-local execution disabled by default and outside the deterministic gate.
