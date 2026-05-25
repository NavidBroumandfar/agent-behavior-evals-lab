# Adjudication Manifest Contract

The adjudication manifest at `traces/external/adjudication_manifest.json` indexes committed public-safe adjudication fixture families and their quality-gate threshold policy.

The manifest contract is defined by `schemas/adjudication_manifest.schema.json` and checked independently by:

```bash
python3 src/validate_adjudication_manifest.py
```

The validator runs before adjudication report generation in `scripts/check_all.py`.

## Top-Level Fields

- `manifest_id`: must be `adjudication_manifest`.
- `version`: non-empty manifest version string.
- `generated_at`: UTC timestamp in `YYYY-MM-DDTHH:MM:SSZ` format.
- `purpose`: non-empty description of the manifest role.
- `scope`: non-empty list of included local fixture scopes.
- `non_goals`: non-empty list of explicitly blocked behaviors.
- `quality_gate_thresholds`: optional committed threshold policy.
- `adjudication_fixtures`: non-empty list of fixture family entries.

## Fixture Fields

Each fixture entry declares:

- `fixture_id`, `label`, `path`, and `description`.
- `expected_record_count`, checked against non-empty JSONL lines for fixture files.
- `quality_gate_included` and `review_status`.
- `owner`, `status_notes`, and `last_reviewed_at`.
- `source_trace_paths`, which must be repository-relative existing paths.
- `safety_assertions`, which must be public-safe and must not require live execution, external actions, private data, or credentials.

Fixtures included in the quality gate may use `reviewed` or `needs_discussion` status. They may not use `draft` or `blocked`.

## Threshold Fields

`quality_gate_thresholds` supports:

- `min_review_coverage`: minimum source-trace review coverage percentage.
- `max_needs_discussion`: maximum global unresolved discussion count.
- `min_profile_review_coverage`: profile-specific coverage percentages.
- `min_category_review_coverage`: category-specific coverage percentages.
- `max_fixture_needs_discussion`: fixture-specific unresolved discussion caps.

Percent thresholds must be finite numbers from 0 through 100. Count thresholds must be non-negative integers.

Threshold map keys are checked against the manifest's fixture IDs and the profile/category labels found in referenced local scored traces. This catches typoed threshold keys before report-time regression checks run.

## Boundaries

Manifest validation does not rescore traces, rewrite JSONL files, collect outputs, execute target systems, call provider APIs, use network access, or apply adjudications back to source traces.
