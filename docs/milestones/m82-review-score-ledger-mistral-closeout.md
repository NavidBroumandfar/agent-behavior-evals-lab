# Milestone 82 - Review, Score, And Ledger Mistral Evidence

Status: Complete / second eligible reviewed ledger produced
Date: 2026-06-22

## Summary

M82 reviewed the ignored M81 `mistral:latest` raw run, produced a public-safe
reviewed derivative, scored it against `local_public_v1`, and generated an
M58-compatible reviewed live-local ledger.

The public-safety review approved 210 / 210 records, found no private data,
unsafe output flags, malformed outputs, unresolved review, credential use, or
external actions, and normalized output whitespace for adapter-output schema
compatibility. Raw outputs, local run metadata, reviewed-input files, and local
review summaries remain ignored and local-only.

## Completed

- Converted the M81 raw run into a local ignored reviewed input at
  `traces/raw/m82_mistral_latest_extended.reviewed_input.local.jsonl`.
- Wrote a local ignored review summary at
  `traces/raw/m82_mistral_latest_extended.review_summary.local.json`.
- Validated the ignored normalized candidate with `--allow-live-local`.
- Committed the public-safe reviewed derivative at
  `traces/external/m82_mistral_latest_extended.reviewed_live_local_outputs.jsonl`.
- Scored 210 reviewed saved outputs against
  `evals/benchmarks/local_public_v1/cases.jsonl`.
- Recorded 38 deterministic scorer passes and 172 deterministic scorer fails.
- Generated and validated the M82 reviewed live-local ledger at
  `traces/external/m82_mistral_latest_extended.local_run_ledger.json`.

## Artifact Hashes

| Artifact | SHA-256 |
| --- | --- |
| `traces/external/m82_mistral_latest_extended.reviewed_live_local_outputs.jsonl` | `9513fff6022ce7d6e0f1a593f96de4f61d42dec74b3a5529741edb8cacb507f9` |
| `traces/scored/m82_mistral_latest_extended.reviewed_live_local_eval.jsonl` | `19b90201feb8f9e3e9a25f979ac9b7e68df3b802194df9b8a6559975d7202504` |
| `traces/external/m82_mistral_latest_extended.review_summary.json` | `a35328f835e52dd1927775abf34d2f2611b02faa6b320d5cf8c2d5a2bfb1b277` |
| `traces/external/m82_mistral_latest_extended.run_metadata.json` | `1abd7fa03df93e91436cdbde3ed818fb43caa7a89e0ea3d4fd7b4bbea14e8cb0` |
| `traces/external/m82_mistral_latest_extended.local_run_ledger.json` | `0576c56cb33553909f9278cddcc351bfa77ed892269a2b813fbfbf9cc89ca764` |

## Boundary

M82 does not commit raw outputs and does not execute a local model. The
deterministic quality gate scores and ledgers only committed public-safe
derivatives. The second ledger can unlock the report only together with the M79
`llama3.2:latest` ledger and the M83 report validation gate.

## Validation

From the repository root:

```bash
python3 src/validate_adapter_outputs.py --allow-live-local traces/external/m82_mistral_latest_extended.reviewed_live_local_outputs.jsonl
python3 src/m82_mistral_reviewed_ledger.py
python3 src/validate_local_run_ledger.py traces/external/m82_mistral_latest_extended.local_run_ledger.json
python3 scripts/dev.py check
```
