# Milestone 21 - Schema Validator Helper Reuse

Date: 2026-05-25

Status: Complete / review-ready

Milestone 21 reuses the shared local JSON Schema subset validator for eval-case and scored-trace JSONL record validation.

M21 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M21.1 Compared `src/validate_schemas.py` with `src/schema_validation_utils.py`.
- M21.2 Reused `validate_schema_value` for eval-case and scored-trace record validation.
- M21.3 Kept JSONL file parsing, schema file loading, record counting, and `path:line` error ownership in `src/validate_schemas.py`.
- M21.4 Extended the shared helper to accept error factories, allowing line-aware validation errors without introducing a second schema implementation.
- M21.5 Added tests that preserve missing-field, unexpected-field, numeric-bound, and array-item line context.

## Key Artifacts

Schema validation:

- `src/schema_validation_utils.py`
- `src/validate_schemas.py`

Tests and docs:

- `tests/test_validate_schemas.py`
- `tests/test_schema_validation_utils.py`
- `docs/wiki/concepts/eval_case_anatomy.md`

## What The Repo Can Now Do

- Validate manifest JSON objects and JSONL records through one shared schema-subset implementation.
- Preserve caller-specific public error types.
- Preserve eval-case and scored-trace validation messages with source file and line-number context.
- Keep file reading and record counting close to the JSONL validator.

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

The gate exercises the shared schema helper through unit tests, JSONL schema validation, adjudication manifest validation, and report manifest validation.

## Recommended Next Milestone

Milestone 22 should keep expanding deterministic governance before live execution:

1. Add a small schema-validation coverage matrix that lists which schema files are gated and which validator owns them.
2. Confirm every quality-gate schema validator is documented in the wiki.
3. Avoid adding live adapters or provider calls until the deterministic contracts remain clear after the validator consolidation.
