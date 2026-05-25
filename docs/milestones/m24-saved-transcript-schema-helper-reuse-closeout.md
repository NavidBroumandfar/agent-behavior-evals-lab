# Milestone 24 - Saved Transcript Schema Helper Reuse

Date: 2026-05-25

Status: Complete / review-ready

Milestone 24 moves saved transcript replay record-shape validation onto the shared local schema helper.

M24 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M24.1 Reused `src/schema_validation_utils.py` from `src/replay_saved_transcripts.py`.
- M24.2 Loaded `schemas/saved_transcript.schema.json` once per replay input load and used it for line-aware JSONL record validation.
- M24.3 Tightened the saved transcript schema to reject blank or whitespace-only required identifiers and selected turn content.
- M24.4 Kept replay-specific semantic checks local: duplicate transcript IDs, case references, target profiles, assistant-turn index bounds, and selected assistant role.
- M24.5 Updated schema coverage documentation to mark saved transcripts as direct schema-helper validation.
- M24.6 Added focused saved transcript replay validation tests for schema-level and replay-semantic failures.

## Key Artifacts

Code and schema:

- `src/replay_saved_transcripts.py`
- `schemas/saved_transcript.schema.json`

Tests and docs:

- `tests/test_saved_transcript_replay.py`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/wiki/concepts/saved_transcript_replay.md`
- `README.md`
- `docs/wiki/index.md`

## What The Repo Can Now Do

- Validate saved transcript record shape through the same shared schema-subset helper used by eval cases, traces, manifests, and the target registry.
- Preserve line-numbered errors for saved transcript JSONL records.
- Keep transcript replay semantics separate from schema-level shape validation.

## What Remains Intentionally Blocked

- Automatic scorer overrides.
- Automatic trace rewriting from adjudications.
- Live collection.
- Tool execution and external actions.
- Benchmark claims from generated reports or external fixtures.

## Quality Gate

From the repository root:

```bash
python3 scripts/check_all.py
```

The gate exercises saved transcript replay directly and includes focused tests for schema-helper validation and replay-specific semantics.

## Recommended Next Milestone

Milestone 25 should consider the next deterministic schema-helper reuse candidate. `src/validate_adapter_outputs.py` is the next likely target if provenance safety checks, blocked future execution modes, and line-numbered JSONL errors can remain explicit and local.
