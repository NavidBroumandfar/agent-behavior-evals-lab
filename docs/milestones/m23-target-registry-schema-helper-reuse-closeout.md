# Milestone 23 - Target Registry Schema Helper Reuse

Date: 2026-05-25

Status: Complete / review-ready

Milestone 23 moves target registry schema-level validation onto the shared local schema helper.

M23 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M23.1 Reused `src/schema_validation_utils.py` from `src/target_registry.py`.
- M23.2 Loaded `schemas/target_registry.schema.json` during target registry validation.
- M23.3 Removed duplicate local shape, enum, boolean, and timestamp-pattern checks now covered by the schema helper.
- M23.4 Kept registry-specific semantic checks local: target profile uniqueness, repository-relative profile/prompt path existence, and quality-gate profile eligibility.
- M23.5 Updated schema coverage documentation to mark the target registry as direct schema-helper validation.
- M23.6 Added tests for schema-level target-kind and unexpected-field failures plus semantic duplicate/path/quality-gate failures.

## Key Artifacts

Code:

- `src/target_registry.py`

Tests and docs:

- `tests/test_target_registry.py`
- `docs/wiki/reference/schema_validation_coverage.md`
- `README.md`
- `docs/wiki/index.md`

## What The Repo Can Now Do

- Validate target registry object shape through the same shared schema-subset helper used by eval cases, scored traces, and manifest validators.
- Preserve target registry semantic checks that are outside the JSON Schema subset.
- Keep the schema validation coverage matrix current after validator implementation changes.

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

The gate exercises target registry validation directly and through downstream flows that read registered target profiles.

## Recommended Next Milestone

Milestone 24 should consider the next low-risk schema-helper reuse candidate. `src/replay_saved_transcripts.py` is a reasonable candidate if JSONL line-numbered errors can stay clear while transcript-specific assistant-turn, case-reference, and target-profile checks remain local.
