# Milestone 81 - Execute Second Local Target Extended Run

Status: Complete / ignored raw run captured, publication blocked pending M82
Date: 2026-06-22

## Summary

M81 started the selected second local target path for `mistral:latest` using the
`ollama_text_only` adapter over the extended `local_public_v1` split. After
explicit M81 live-local opt-in was provided, the selected model was installed
locally and the full extended live-local run completed.

The run captured 210 raw local records with 210 succeeded, 0 failed, and 0
skipped. Raw outputs and run metadata remain ignored and local-only. M81 does
not review, normalize, score, ledger, or publish rankings from these records;
that remains M82 scope.

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

## Live Command

Explicit M81 live-local opt-in was provided before this command ran:

```bash
AGENT_EVALS_ENABLE_LIVE_LOCAL=1 /usr/bin/time -p caffeinate -dimsu python3 scripts/live_local.py --model mistral:latest --adapter ollama_text_only --split extended --live-local --max-failures 210 --run-id m81_mistral_latest_extended --output traces/raw/m81_mistral_latest_extended.local.jsonl --metadata-output traces/raw/m81_mistral_latest_extended.run_metadata.local.json
```

## Live Result

- Run id: `m81_mistral_latest_extended`.
- Status: `succeeded`.
- Model: `mistral:latest`.
- Adapter: `ollama_text_only`.
- Split: `extended`.
- Planned cases: 210.
- Attempted cases: 210.
- Succeeded: 210.
- Failed: 0.
- Skipped: 0.
- Started: `2026-06-22T10:54:01Z`.
- Completed: `2026-06-22T11:07:32Z`.
- Wall-clock runtime: 811.69 seconds.
- Raw output path: `traces/raw/m81_mistral_latest_extended.local.jsonl`.
- Run metadata path: `traces/raw/m81_mistral_latest_extended.run_metadata.local.json`.
- Review-required normalized output path reserved by metadata:
  `traces/external/m81_mistral_latest_extended.reviewed.jsonl`.

## Publication Boundary

The local/open-weight report remains blocked at one eligible reviewed
live-local ledger. `ranking_claim_allowed` remains `false`; the missing blocker
is still the absence of a second eligible reviewed extended ledger. M82 must
review, normalize, score, and ledger `mistral:latest` public-safe derivatives
before the second target can count toward the publication gate.

Raw outputs and run metadata remain ignored and local-only. No raw output,
private data, credentials, provider payloads, cloud-labelled targets,
smoke/control evidence, or live-local execution are added to the deterministic
quality gate.

## Validation

From the repository root:

```bash
python3 scripts/live_local.py --model mistral:latest --adapter ollama_text_only --split extended --plan-only --run-id m81_mistral_latest_extended --output traces/raw/m81_mistral_latest_extended.local.jsonl --metadata-output traces/raw/m81_mistral_latest_extended.run_metadata.local.json --plan-output traces/raw/m81_mistral_latest_extended.plan.local.json
AGENT_EVALS_ENABLE_LIVE_LOCAL=1 /usr/bin/time -p caffeinate -dimsu python3 scripts/live_local.py --model mistral:latest --adapter ollama_text_only --split extended --live-local --max-failures 210 --run-id m81_mistral_latest_extended --output traces/raw/m81_mistral_latest_extended.local.jsonl --metadata-output traces/raw/m81_mistral_latest_extended.run_metadata.local.json
wc -l traces/raw/m81_mistral_latest_extended.local.jsonl
git status --short --ignored traces/raw/m81_mistral_latest_extended.plan.local.json traces/raw/m81_mistral_latest_extended.local.jsonl traces/raw/m81_mistral_latest_extended.run_metadata.local.json
python3 scripts/dev.py check
```
