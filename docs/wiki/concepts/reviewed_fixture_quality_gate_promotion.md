# Reviewed Fixture Quality-Gate Promotion Checklist

Reviewed fixture promotion is the controlled path for moving public-safe saved outputs into deterministic quality-gate coverage.

Before setting a promoted fixture's `quality_gate_included` field to `true` in `traces/external/fixture_manifest.json`, verify each item below.

## Checklist

- The source fixture lives under `traces/external/` and does not use `.local.jsonl`, `.private.jsonl`, or `.reviewed.jsonl` as its committed filename.
- The source fixture validates with `src/validate_adapter_outputs.py` or the fixture-specific validator named in the manifest entry.
- The fixture has public-safe provenance: no live execution claims, no external actions, no private data, and no credentials required.
- The scored trace path under `traces/scored/` has been generated from the committed fixture with the intended importer or evaluator.
- `expected_record_count` and `expected_scored_count` match the committed JSONL line counts.
- `report_paths` includes every deterministic report that should summarize the fixture.
- `src/compare_external_fixtures.py` includes the fixture through the manifest-driven comparison, not through a hard-coded source list.
- Any reviewer adjudications that affect interpretation are captured in a committed adjudication fixture under `traces/external/`.
- The adjudication fixture is listed in `traces/external/adjudication_manifest.json` with the correct expected record count, source trace paths, quality-gate status, and public-safe safety assertions.
- The adjudication summary and adjudicated aggregate reports clearly separate heuristic results from reviewed results.
- `python3 scripts/check_all.py` passes after the fixture, scored trace, manifest, reports, and docs are updated.

## Test Coverage

`tests/test_promote_reviewed_outputs.py` exercises the promotion path with a temporary reviewed adapter-output fixture, writes the manifest-entry draft, adds the required scored trace and report artifact, and validates the temporary manifest with `src/validate_fixture_manifest.py`.

## Boundaries

Promotion does not prove live model or agent quality. It only admits a public-safe saved-output fixture into deterministic local validation and reporting.
