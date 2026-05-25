# Milestone 25 - Adapter Output Schema Helper Reuse

Date: 2026-05-25

Status: Complete / review-ready

Milestone 25 moves normalized adapter-output record-shape validation onto the shared local schema helper.

M25 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M25.1 Reused `src/schema_validation_utils.py` from `src/validate_adapter_outputs.py`.
- M25.2 Loaded `schemas/adapter_output.schema.json` once per adapter-output JSONL file and used it for line-aware record validation.
- M25.3 Tightened the adapter-output schema to reject blank or whitespace-only required identifiers and output text.
- M25.4 Kept adapter-output-specific checks local: UTC date validity, explicit public-safe provenance values, and future-only provenance detail blocks.
- M25.5 Updated schema coverage documentation to mark adapter outputs as direct schema-helper validation.
- M25.6 Added focused tests for schema-level unexpected-field/source-type failures and local future-only provenance rejections.

## Key Artifacts

Code and schema:

- `src/validate_adapter_outputs.py`
- `schemas/adapter_output.schema.json`

Tests and docs:

- `tests/test_adapter_output_conformance.py`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/wiki/concepts/normalized_adapter_outputs.md`
- `README.md`
- `docs/wiki/index.md`

## What The Repo Can Now Do

- Validate normalized adapter-output record shape through the same shared schema-subset helper used by eval cases, traces, manifests, target registry, and saved transcripts.
- Preserve line-numbered errors for adapter-output JSONL records.
- Keep provenance safety and future-only execution/data blocks explicit in the adapter-output validator.

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

The gate exercises adapter-output validation directly, through dry-run adapter outputs, and through adapter-output import flows.

## Recommended Next Milestone

Milestone 26 should consider the next deterministic schema-helper reuse candidate. `src/validate_adjudications.py` is a possible target only if source-trace consistency, reviewer-decision semantics, and line-numbered JSONL errors remain clear and local.
