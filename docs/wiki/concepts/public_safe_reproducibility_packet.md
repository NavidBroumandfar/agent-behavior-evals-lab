# Public-Safe Reproducibility Packet

M84 defines the public-safe reproducibility packet for the first published
local/open-weight ranking. The packet lives at
`docs/milestones/m84-public-safe-reproducibility-packet-closeout.md`.

The packet is documentation and provenance metadata. It records:

- committed artifact paths and SHA-256 hashes,
- model tags and ledger entry IDs,
- harness, adapter, prompt, methodology, and scorer versions,
- command templates for future opt-in local runs,
- non-live validation commands for the committed ranking,
- raw/local-only exclusion rules,
- explicit claim boundaries.

## What It Supports

The packet supports deterministic verification of committed public-safe
derivatives: ledgers, review summaries, scored traces, benchmark report
snapshots, schemas, methodology, adapter registry, prompt template, and scorer
source.

It also makes the claim surface easier to audit. A reader can confirm that the
ranking is ledger-backed, uses the frozen `local_public_v1` extended split, and
does not rely on private evidence, raw outputs, hosted-provider evidence, or
production-system traces.

## What It Does Not Support

The packet does not claim third-party output regeneration. The current local
runs record Ollama model tags such as `llama3.2:latest` and `mistral:latest`,
but tags alone do not pin immutable model weights, binary runtime behavior,
hardware, thermal state, or local scheduling. Those details require later
runtime-stability and model-disclosure metadata.

The packet also does not support cloud rankings, production-safety proof,
hosted-provider comparisons, private-audit proof, or claims from smoke/control
targets.

## Operational Boundary

M84 does not execute live models. Future live-local command templates require
both `--live-local` and `AGENT_EVALS_ENABLE_LIVE_LOCAL=1`, and they must remain
outside `python3 scripts/dev.py check`.
