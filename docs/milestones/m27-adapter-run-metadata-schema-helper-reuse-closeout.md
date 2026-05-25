# Milestone 27 - Adapter Run Metadata Schema Helper Reuse

Date: 2026-05-25

Status: Complete / review-ready

Milestone 27 moves adapter-run metadata object-shape validation onto the shared local schema helper.

M27 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M27.1 Reused `src/schema_validation_utils.py` from `src/validate_adapter_run_metadata.py`.
- M27.2 Loaded `schemas/adapter_run_metadata.schema.json` for metadata object validation before local semantic checks.
- M27.3 Expanded the adapter-run metadata schema to cover nested required fields, unexpected fields, nonblank strings, enum values, arrays, integers, and primitive boolean types.
- M27.4 Kept metadata-specific checks local: UTC timestamp date validity, target registry lookup, repository path boundaries, case ID consistency, quality-gate booleans, and public-safe provenance expectations.
- M27.5 Updated schema coverage documentation to mark adapter-run metadata as direct schema-helper validation.
- M27.6 Added focused tests for schema-level enum, nested-field, blank-text, array, timestamp-shape, and boolean-type failures plus local semantic rejection paths.

## Key Artifacts

Code and schema:

- `src/validate_adapter_run_metadata.py`
- `schemas/adapter_run_metadata.schema.json`

Tests and docs:

- `tests/test_adapter_run_metadata_validation.py`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/wiki/concepts/controlled_adapter_sandbox.md`
- `README.md`
- `docs/wiki/index.md`

## What The Repo Can Now Do

- Validate adapter-run metadata shape through the same shared schema-subset helper used by all other committed schema contracts.
- Keep local-only adapter-run planning boundaries explicit after schema validation.
- Preserve deterministic quality-gate coverage without executing the adapter described by the metadata.

## What Remains Intentionally Blocked

- Live adapter runs inside the quality gate.
- Provider calls, local model runs, CLI agent execution, browser/email actions, credentials, or external actions.
- Committing raw local outputs.
- Benchmark claims from generated reports or external fixtures.

## Quality Gate

From the repository root:

```bash
python3 scripts/check_all.py
```

The gate validates the committed adapter-run metadata example and exercises the schema coverage documentation tests.

## Recommended Next Milestone

Milestone 28 should harden the schema coverage matrix now that every committed schema has direct shared-helper validation. A deterministic option is to extend `tests/test_schema_validation_coverage_docs.py` so the matrix must mention `src/schema_validation_utils.py` for every schema row and cannot silently regress to duplicated local record-shape validation.
