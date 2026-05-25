# Milestone 20 - Shared Schema Validation Helpers

Date: 2026-05-25

Status: Complete / review-ready

Milestone 20 extracts duplicated local JSON Schema subset validation into a shared helper module.

M20 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M20.1 Added `src/schema_validation_utils.py` for shared local JSON object loading and JSON Schema subset validation.
- M20.2 Updated `src/validate_adjudication_manifest.py` to use the shared helper for schema-level validation.
- M20.3 Updated `src/validate_report_manifest.py` to use the shared helper for schema-level validation.
- M20.4 Kept adjudication-specific fixture/source-trace/threshold semantic checks in the adjudication manifest validator.
- M20.5 Kept report-specific artifact path/generator/input/snapshot semantic checks in the report manifest validator.
- M20.6 Added focused tests for the shared helper's custom error type, `additionalProperties`, and JSON object loading behavior.

## Key Artifacts

Shared validation:

- `src/schema_validation_utils.py`

Validators:

- `src/validate_adjudication_manifest.py`
- `src/validate_report_manifest.py`

Tests and docs:

- `tests/test_schema_validation_utils.py`
- `docs/wiki/concepts/adjudication_manifest_contract.md`
- `docs/wiki/concepts/report_artifact_manifest.md`

## What The Repo Can Now Do

- Reuse one implementation for manifest schema-level validation.
- Preserve validator-specific public error types and messages.
- Support the schema features used by the local manifest contracts: required fields, no additional properties, typed additional property maps, primitive types, arrays, string lengths, patterns, enums, constants, and numeric bounds.
- Keep domain-specific semantic validation close to each manifest owner.

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

The gate now compiles the shared schema validation helper and exercises it through unit tests plus adjudication/report manifest validation.

## Recommended Next Milestone

Milestone 21 should consider extending shared validation only where it removes real duplication:

1. Compare `src/validate_schemas.py` with `src/schema_validation_utils.py`.
2. Decide whether JSONL record validation can reuse the shared helper without reducing clarity.
3. Keep file-specific validation summaries and semantic checks in their owning validators.
4. Continue blocking live execution from deterministic quality-gate paths.
