# Milestone 77 - Controlled Live-Local Technical Proof Run

Milestone 77 executed the first controlled live-local proof attempt against the
installed Ollama runtime. It remains a technical proof, not a publishable
benchmark ranking.

M77 used explicit live-local opt-in and kept raw evidence under ignored local
paths. No raw model output, private data, credentials, provider payloads, or
cloud evidence is committed.

## Execution Summary

- Runtime: local Ollama loopback at `http://127.0.0.1:11434/api/chat`.
- Case set: `local_public_v1`.
- Harness: `scripts/live_local.py` / `live_local_text_only_harness`.
- Opt-in controls: `AGENT_EVALS_ENABLE_LIVE_LOCAL=1` and `--live-local`.
- Deterministic quality gate: live-local execution remained excluded.
- Model order: qwen smoke/control, `llama3.2:latest` extended, then attempted
  `gemma4:latest` extended only after the laptop remained stable.

## Results

| Target | Split | Planned | Recorded | Succeeded | Failed | Status | Publication handling |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| `qwen3.5:2b-q4_K_M` | smoke | 21 | 21 | 1 | 20 | partial | control only, ranking-excluded |
| `llama3.2:latest` | smoke cap | 3 | 3 | 3 | 0 | succeeded | smoke only, ranking-excluded until review/ledger gates |
| `llama3.2:latest` | extended | 210 | 210 | 210 | 0 | succeeded | waiting for review, not publishable yet |
| `gemma4:latest` | extended | 210 | 0 | n/a | n/a | deferred | stopped after swap activity; no raw run artifact written |

The qwen control run passed model availability but returned empty
`message.content` for 20 of 21 generations. The `llama3.2:latest` smoke cap and
extended run completed successfully, demonstrating the live-local collection
path against a real installed local model.

The `gemma4:latest` extended run was interrupted after macOS reported swapouts
during the heavier pass. The interrupted harness did not write a raw JSONL or
metadata file for gemma4; only the ignored plan artifact was retained.

## Local Artifact Hashes

These hashes identify ignored local artifacts without committing their content.

| Artifact | SHA-256 |
| --- | --- |
| `traces/raw/m77_qwen3_5_2b_q4_k_m_smoke.local.jsonl` | `880ff1a6750f3f5532144960ef5d434fe47563dbef44adeb8593caac7625297d` |
| `traces/raw/m77_qwen3_5_2b_q4_k_m_smoke.metadata.local.json` | `bb834d10eac93a117367e8b4b37a5afc2f93c6cd98446505efacf98ef2a0e23a` |
| `traces/raw/m77_llama3_2_latest_smoke3.local.jsonl` | `5fedcc655a9d47e732c6c9906bc1da1c1db61e5437e2ddd09e0ae5dbea836620` |
| `traces/raw/m77_llama3_2_latest_smoke3.metadata.local.json` | `84b9dcc50af717dafc44caca813e1930b1ee4398db324ea6f84cdd42f93544c5` |
| `traces/raw/m77_llama3_2_latest_extended.local.jsonl` | `1231c215cab8a17089e5f69186228964629824d409e15375de380e859085e8f4` |
| `traces/raw/m77_llama3_2_latest_extended.metadata.local.json` | `7c1afb934aee0dbf8b22dd1b684e04009112c52645f9d2651658c821a9e83887` |
| `traces/raw/m77_gemma4_latest_extended.plan.local.json` | `79334de647dcc08eb051b1c157ef1862958a4f1660e26f7abf627f58bf358ea7` |

## Review And Publication Gate

The `llama3.2:latest` extended run leaves 210 raw records waiting for review.
They are not normalized, scored, ledgered, or ranking-eligible until review
marks public-safe records, `src/review_text_only_outputs.py` writes reviewed
normalized output, `src/import_adapter_outputs.py` scores the reviewed output,
and an M58-compatible ledger validates against the reviewed evidence.

Publication remains blocked because:

- there are zero eligible reviewed live-local ledgers,
- only one primary target completed an extended run,
- the completed extended run is still raw and review-pending,
- the heavier `gemma4:latest` run was deferred on swap activity,
- no two-model M70-M76 review and ledger gate has passed.

M77 can claim that the live-local pipeline executed against a real installed
local model and produced traceable ignored technical evidence. It must not claim
a final local/open-weight benchmark ranking, cloud benchmark, production-safety
proof, private-audit proof, or third-party reproducibility proof.
