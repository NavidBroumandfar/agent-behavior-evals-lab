# Milestone 26 - Adjudication Schema Helper Reuse

Date: 2026-05-25

Status: Complete / review-ready

Milestone 26 moves human-adjudication JSONL record-shape validation onto the shared local schema helper.

M26 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M26.1 Reused `src/schema_validation_utils.py` from `src/validate_adjudications.py`.
- M26.2 Loaded `schemas/adjudication.schema.json` once per adjudication JSONL file and used it for line-aware record validation.
- M26.3 Tightened the adjudication schema to reject blank required text, invalid reviewer decisions, invalid UTC review timestamp shape, and non-true `public_safe` values.
- M26.4 Kept adjudication-specific checks local: duplicate `adjudication_id`, repository-relative source trace existence, source-trace field consistency, and reviewer-decision result semantics.
- M26.5 Updated schema coverage documentation to mark adjudications as direct schema-helper validation.
- M26.6 Added focused tests for schema-level unexpected-field, reviewer-decision, blank-text, and timestamp failures plus local semantic rejection paths.

## Key Artifacts

Code and schema:

- `src/validate_adjudications.py`
- `schemas/adjudication.schema.json`

Tests and docs:

- `tests/test_validate_adjudications.py`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/wiki/concepts/human_adjudications.md`
- `README.md`
- `docs/wiki/index.md`

## What The Repo Can Now Do

- Validate committed human-adjudication record shape through the same shared schema-subset helper used by eval cases, traces, manifests, target registry, saved transcripts, and adapter outputs.
- Preserve line-numbered errors for adjudication JSONL records.
- Keep reviewer decision semantics and source trace consistency explicit in the adjudication validator.

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

The gate exercises both committed adjudication fixture families directly and through manifest-backed report and regression flows.

## Recommended Next Milestone

Milestone 27 should consider `src/validate_adapter_run_metadata.py` for shared schema-helper reuse only if adapter-run provenance checks, target profile checks, path safety, timestamp validity, and existing error clarity remain local and deterministic.
