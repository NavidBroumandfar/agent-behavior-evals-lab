# Reproducible Local Run Ledger

M58 adds a reproducible run ledger for local/open-weight benchmark evidence.
The ledger is the audit layer between the M57 opt-in local text-only harness,
the M56 local adapter registry, the M55 `local_public_v1` corpus, reviewed
normalized outputs, scored traces, and the deterministic v0 scorer.

Primary artifacts:

- `schemas/local_run_ledger.schema.json`
- `src/local_run_ledger.py`
- `src/validate_local_run_ledger.py`
- `traces/external/local_run_ledger.example.json`
- `traces/external/local_run_ledger_metadata.example.json`
- `traces/external/local_run_ledger_outputs.example.jsonl`
- `traces/scored/local_run_ledger_outputs.example.jsonl`
- `targets/prompts/local_text_only_v1.md`

## What The Ledger Pins

Each ledger entry records repository-local paths and SHA-256 hashes for:

- The `local_public_v1` case file and manifest.
- The local adapter registry and selected adapter version.
- The exact local text-only prompt template file.
- The reviewed normalized output file.
- The scored trace file generated from saved outputs.
- The deterministic scorer artifact and scorer version label.
- Public-safe run metadata.

This means a reader can verify that scored local outputs map back to a specific
case set, prompt template, adapter version, normalized output file, scorer, and
metadata bundle without needing the local model runtime.

## Committed Example

The committed M58 ledger is a dry-run public-safe example. It uses fake
normalized outputs over four `local_public_v1` smoke cases and is marked
`ranking_eligible: false`.

The deterministic gate regenerates and validates this example:

```bash
python3 src/local_run_ledger.py
python3 src/validate_local_run_ledger.py
```

The validator replays the scored trace from saved normalized outputs and the
current deterministic scorer. It does not call Ollama, local OpenAI-compatible
servers, providers, agents, networks, tools, credentials, private logs, or
external actions.

## Boundary

The ledger can describe reviewed live-local runs later, but the committed M58
example is not local model evidence and is not ranking evidence. Raw local
outputs stay ignored. Ledger entries must not include secrets, private prompts,
private evidence, raw runtime logs, provider credentials, browser/email actions,
shell or file actions as a system under test, or gated LLM review.
