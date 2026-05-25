# Milestone 22 - Schema Validation Coverage Matrix

Date: 2026-05-25

Status: Complete / review-ready

Milestone 22 documents the repository's schema validation surface after the shared validation helper consolidation.

M22 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M22.1 Added `docs/wiki/reference/schema_validation_coverage.md`.
- M22.2 Mapped every committed `schemas/*.schema.json` file to its owning validator.
- M22.3 Documented whether each validator is covered by `scripts/check_all.py`.
- M22.4 Documented the default input files each schema/validator covers.
- M22.5 Distinguished direct schema-file loading from local code implementations that mirror the documented schema contract.
- M22.6 Added `tests/test_schema_validation_coverage_docs.py` so new schema files must be added to the coverage matrix.

## Key Artifacts

Coverage reference:

- `docs/wiki/reference/schema_validation_coverage.md`

Drift test:

- `tests/test_schema_validation_coverage_docs.py`

Index updates:

- `README.md`
- `docs/wiki/index.md`

## What The Repo Can Now Do

- Show which validator owns each committed schema.
- Show which schemas are reached by the deterministic local quality gate.
- Preserve the distinction between JSON Schema files loaded by shared helper code and schema contracts enforced by local validator code.
- Catch future schema/documentation drift through unit tests.

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

The gate now includes a unit test that compares `schemas/*.schema.json` against the schema coverage reference page.

## Recommended Next Milestone

Milestone 23 should harden whichever schema contract still relies only on local mirror validation where shared helper reuse would improve clarity. Start with low-risk candidates, and keep provenance, source-reference, and public-safety semantics in the owning validators.
