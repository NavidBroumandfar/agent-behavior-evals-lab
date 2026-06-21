# Milestone 57 - Opt-In Local Text-Only Model Harness

Date: 2026-06-21

Status: Complete / review-ready

Milestone 57 adds an opt-in local text-only model harness for the frozen
`local_public_v1` corpus and M56 local adapter registry. It enables Ollama and
local OpenAI-compatible runs while preserving the deterministic quality-gate
boundary.

M57 does not add provider credentials, hosted provider calls, private logs,
browser/email actions, messaging, purchases, shell or file actions as a system
under test, external actions, live Hermes or OpenClaw execution, gated LLM
review, model ranking, scorer behavior changes, or live local execution inside
`scripts/dev.py check` or `scripts/check_all.py`.

## Completed Slices

- M57.1 Added `scripts/live_local.py` for opt-in local text-only runs.
- M57.2 Added `src/live_local_harness.py` with Ollama and local OpenAI-compatible loopback clients.
- M57.3 Required both `--live-local` and `AGENT_EVALS_ENABLE_LIVE_LOCAL` before live execution.
- M57.4 Added timeout, availability-check, retry, and max-failure abort controls.
- M57.5 Added local raw output records under ignored `.local.jsonl` paths and ignored run metadata under `.local.json`.
- M57.6 Added `schemas/live_local_run.schema.json`, `src/validate_live_local_run.py`, and `traces/external/live_local_run_plan.example.json`.
- M57.7 Extended adapter-output validation/import for reviewed live-local outputs behind explicit `--allow-live-local`.
- M57.8 Extended reviewed-output conversion to preserve live-local provenance only for successful approved records.
- M57.9 Added fake-client unit tests; no unit test calls Ollama or a local server.
- M57.10 Updated roadmap, wiki, schema coverage, release-note, and manifest inputs.

## Key Artifacts

Harness and validation:

- `scripts/live_local.py`
- `src/live_local_harness.py`
- `schemas/live_local_run.schema.json`
- `src/validate_live_local_run.py`
- `traces/external/live_local_run_plan.example.json`

Review and scoring path:

- `src/review_text_only_outputs.py`
- `src/validate_adapter_outputs.py`
- `src/import_adapter_outputs.py`
- `tests/test_live_local_harness.py`
- `tests/test_live_local_run_validation.py`
- `tests/test_adapter_output_conformance.py`
- `tests/test_text_only_output_workflow.py`

Documentation:

- `docs/wiki/concepts/live_local_text_only_harness.md`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/live_benchmark_roadmap.md`
- `docs/roadmap.md`

## Opt-In Run Boundary

Planning is non-live:

```bash
python3 scripts/live_local.py --plan-only --adapter ollama_text_only --model example-local-model --split smoke
```

Live local execution requires both controls:

```bash
AGENT_EVALS_ENABLE_LIVE_LOCAL=1 python3 scripts/live_local.py --live-local --adapter ollama_text_only --model <local-model> --split smoke
```

Raw outputs remain local-only and ignored. Reviewed live-local outputs require explicit validation/import:

```bash
python3 src/validate_adapter_outputs.py --allow-live-local traces/external/example.reviewed.jsonl
python3 src/import_adapter_outputs.py traces/external/example.reviewed.jsonl traces/scored/example.local.jsonl --allow-live-local --case-path evals/benchmarks/local_public_v1/cases.jsonl
```

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate validates the dry-run plan and fake-client behavior only. It remains
deterministic, local, credential-free, public-safe, and does not call local
models.

## Recommended Next Milestone

Proceed to M58 Reproducible Local Run Ledger. The next useful phase is making
reviewed local model evidence auditable with hashes for the case set, prompt
template, adapter version, normalized output file, and scorer version.
