# Milestone 28 - Schema Coverage Helper Enforcement

Date: 2026-05-25

Status: Complete / review-ready

Milestone 28 hardens the schema coverage matrix so direct shared-helper validation remains visible and test-enforced for every committed schema.

M28 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M28.1 Extended `tests/test_schema_validation_coverage_docs.py` to parse every schema row in the coverage matrix.
- M28.2 Required every schema row to mention `src/schema_validation_utils.py`.
- M28.3 Rejected the old duplicated-local-validator wording in schema rows.
- M28.4 Updated the coverage rules to state direct shared-helper validation as the matrix standard.
- M28.5 Updated README and wiki milestone indexes.

## Key Artifacts

Tests and docs:

- `tests/test_schema_validation_coverage_docs.py`
- `docs/wiki/reference/schema_validation_coverage.md`
- `README.md`
- `docs/wiki/index.md`

## What The Repo Can Now Do

- Keep schema coverage documentation aligned with the shared-helper validation architecture.
- Catch future schema rows that omit direct `src/schema_validation_utils.py` validation.
- Preserve room for validators to keep non-schema semantics local after shared shape validation.

## What Remains Intentionally Blocked

- Live collection.
- Tool execution and external actions.
- Benchmark claims from generated reports or external fixtures.
- Replacing semantic validator checks with schema-only checks where local provenance, path, or safety context is required.

## Quality Gate

From the repository root:

```bash
python3 scripts/check_all.py
```

The gate runs the coverage-doc test with the rest of the local deterministic suite.

## Recommended Next Milestone

Milestone 29 should shift from schema-helper reuse to deterministic report/manifest governance. A useful candidate is strengthening `reports/comparisons/report_manifest.json` coverage so generated reports and snapshots are easier to audit without adding live execution or changing scoring semantics.
