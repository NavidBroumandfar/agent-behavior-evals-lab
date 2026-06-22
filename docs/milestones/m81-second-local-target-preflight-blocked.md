# Milestone 81 - Second Local Target Extended Run Preflight

Status: Blocked / plan-only preflight complete, live execution not authorized
Date: 2026-06-22

## Summary

M81 started the selected second local target path for `mistral:latest` using the
`ollama_text_only` adapter over the extended `local_public_v1` split. The phase
ran only the non-live plan command because the active thread did not provide
explicit M81 live-local opt-in.

The plan-only preflight confirms the target, adapter, split, 210 planned cases,
ignored raw-output path, ignored run-metadata path, and required live-local
controls. It does not contact Ollama, execute a model, read raw outputs, call a
provider, use credentials, or add live-local execution to the deterministic
quality gate.

## Preflight Command

```bash
python3 scripts/live_local.py --model mistral:latest --adapter ollama_text_only --split extended --plan-only --run-id m81_mistral_latest_extended --output traces/raw/m81_mistral_latest_extended.local.jsonl --metadata-output traces/raw/m81_mistral_latest_extended.run_metadata.local.json --plan-output traces/raw/m81_mistral_latest_extended.plan.local.json
```

## Preflight Result

- Run id: `m81_mistral_latest_extended`.
- Mode: `plan_only`.
- Adapter: `ollama_text_only`.
- Runtime: `ollama`.
- Model: `mistral:latest`.
- Split: `extended`.
- Planned cases: 210.
- Ignored plan artifact: `traces/raw/m81_mistral_latest_extended.plan.local.json`.
- Ignored raw output path: `traces/raw/m81_mistral_latest_extended.local.jsonl`.
- Ignored run metadata path: `traces/raw/m81_mistral_latest_extended.run_metadata.local.json`.
- Required live-local flag: `--live-local`.
- Required live-local environment variable: `AGENT_EVALS_ENABLE_LIVE_LOCAL`.

## Active Blocker

Live-local execution is blocked until explicit M81 opt-in is provided in the
active thread. The required execution command remains:

```bash
AGENT_EVALS_ENABLE_LIVE_LOCAL=1 python3 scripts/live_local.py --model mistral:latest --adapter ollama_text_only --split extended --live-local --max-failures 210
```

Do not run that command without explicit operator authorization for M81.

## Publication Boundary

The local/open-weight report remains blocked at one eligible reviewed
live-local ledger. `ranking_claim_allowed` remains `false`; the missing blocker
is still the absence of a second eligible reviewed extended ledger. M82 cannot
review, score, or ledger `mistral:latest` until M81 has an authorized complete
or explicitly stopped live-local run.

Raw outputs and run metadata remain ignored and local-only. No raw output,
private data, credentials, provider payloads, cloud-labelled targets,
smoke/control evidence, or live-local execution are added to the deterministic
quality gate.

## Validation

From the repository root:

```bash
python3 scripts/live_local.py --model mistral:latest --adapter ollama_text_only --split extended --plan-only --run-id m81_mistral_latest_extended --output traces/raw/m81_mistral_latest_extended.local.jsonl --metadata-output traces/raw/m81_mistral_latest_extended.run_metadata.local.json --plan-output traces/raw/m81_mistral_latest_extended.plan.local.json
git status --short --ignored traces/raw/m81_mistral_latest_extended.plan.local.json
python3 scripts/dev.py check
```
