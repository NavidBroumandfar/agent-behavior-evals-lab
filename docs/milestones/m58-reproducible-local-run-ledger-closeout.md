# Milestone 58 - Reproducible Local Run Ledger

Date: 2026-06-21

Status: Complete / review-ready

Milestone 58 adds a reproducible local run ledger for auditing future
local/open-weight benchmark evidence around the M57 opt-in local text-only
harness, M56 local adapter registry, and M55 `local_public_v1` corpus.

M58 does not add provider credentials, hosted provider calls, private logs,
browser/email actions, messaging, purchases, shell or file actions as a system
under test, external actions, live Hermes or OpenClaw execution, gated LLM
review, model ranking, scorer behavior changes, or live local execution inside
`scripts/dev.py check` or `scripts/check_all.py`.

## Completed Slices

- M58.1 Added `targets/prompts/local_text_only_v1.md` so the M57 prompt template is hashable.
- M58.2 Extended the M57 dry-run plan schema and example to include the prompt template path.
- M58.3 Added `schemas/local_run_ledger.schema.json`.
- M58.4 Added `src/local_run_ledger.py` to generate a deterministic public-safe fake ledger example.
- M58.5 Added `src/validate_local_run_ledger.py` to validate ledger schema, hashes, adapter registry metadata, case membership, prompt template hash, normalized output provenance, scored trace replay, scorer artifact hash, and run metadata.
- M58.6 Added committed dry-run example artifacts under `traces/external/` and `traces/scored/`.
- M58.7 Added unit tests for the ledger happy path, hash mismatches, split membership, quality-gate execution boundary, record counts, and raw-output exclusion.
- M58.8 Wired local run ledger generation, validation, and compile coverage into `scripts/check_all.py`.
- M58.9 Updated roadmap, wiki, schema coverage, release-note, and manifest inputs.

## Key Artifacts

Ledger and validation:

- `schemas/local_run_ledger.schema.json`
- `src/local_run_ledger.py`
- `src/validate_local_run_ledger.py`
- `tests/test_local_run_ledger.py`

Public-safe dry-run example:

- `traces/external/local_run_ledger.example.json`
- `traces/external/local_run_ledger_metadata.example.json`
- `traces/external/local_run_ledger_outputs.example.jsonl`
- `traces/scored/local_run_ledger_outputs.example.jsonl`

Prompt template:

- `targets/prompts/local_text_only_v1.md`
- `traces/external/live_local_run_plan.example.json`

Documentation:

- `docs/wiki/concepts/local_run_ledger.md`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/live_benchmark_roadmap.md`
- `docs/roadmap.md`

## Ledger Outcome

- Ledger ID: `m58_reproducible_local_run_ledger_example`
- Ledger kind: `dry_run_public_safe_example`
- Entries: 1
- Normalized output records: 4
- Scored trace records: 4
- Evidence class: `evaluator_health`
- Ranking eligible: false
- Live execution in committed example: false
- Raw outputs included: false

The ledger pins SHA-256 hashes for the `local_public_v1` case file and
manifest, M56 local adapter registry, selected adapter version, M57 prompt
template, normalized output file, scored trace file, deterministic scorer
artifact, and public-safe run metadata.

## Reproducibility Boundary

The validator replays the scored trace from saved normalized outputs and the
current deterministic scorer. This proves that saved-output replay does not
require Ollama, a local OpenAI-compatible server, or any live model runtime.

The committed M58 example is not local model evidence and cannot support a
ranking. A future reviewed live-local ledger can use the same schema with
`evidence_class: local_public_benchmark` after real opt-in local execution,
reviewed public-safe normalized outputs, and ranking methodology exist.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic, local, credential-free, public-safe, and does
not call local models.

## Recommended Next Milestone

Proceed to M59 Local Ranking Methodology. The next useful phase is defining
ranking metrics, uncertainty, tie policy, partial-run policy, and review
requirements before publishing local/open-weight benchmark rankings.
