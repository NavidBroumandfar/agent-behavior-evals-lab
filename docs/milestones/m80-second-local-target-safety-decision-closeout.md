# Milestone 80 - Second Local Target Safety Decision

Status: Complete / decision recorded, publication blocked
Date: 2026-06-22

## Summary

M80 documents how the lab will obtain the second eligible local/open-weight
target after the M77 `gemma4:latest` extended run was stopped on swap activity.
The decision is to defer `gemma4:latest` from the current publication path and
use `mistral:latest` as the second local Ollama text-only extended target for
M81.

M80 is a documentation and contract update only. It does not run a local model,
read raw outputs, call a provider, use credentials, or add live-local execution
to the deterministic quality gate.

## Decision

- Selected target: `mistral:latest`.
- Adapter: `ollama_text_only`.
- Split: `extended`.
- Deferred target: `gemma4:latest`.
- Smoke/control remains excluded: `qwen3.5:2b-q4_K_M`.
- Cloud-labelled target remains excluded: `gemma4:31b-cloud`.

## M81 Requirements

- Use plan-only metadata checks before live execution.
- Execute only with `AGENT_EVALS_ENABLE_LIVE_LOCAL=1` and `--live-local`.
- Store raw outputs and run metadata only under ignored local paths.
- Stop and keep publication blocked if model availability, memory pressure, or
  thermal behavior is unstable.
- Review, normalize, score, and ledger only public-safe derivatives in M82.

## Boundary

The local/open-weight report remains blocked at one eligible reviewed
live-local ledger. No ranking may publish until reviewed extended ledgers exist
for both `llama3.2:latest` and `mistral:latest`, with no unresolved review,
unsafe output, malformed output, private data, credentials, external actions,
raw outputs, partial-run status, smoke-only evidence, or cloud-labelled target.

## Validation

From the repository root:

```bash
python3 src/real_model_proof_runbook.py
python3 src/local_benchmark_report.py
python3 scripts/dev.py check
```
