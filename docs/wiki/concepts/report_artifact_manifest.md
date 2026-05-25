# Report Artifact Manifest

The report artifact manifest at `reports/comparisons/report_manifest.json` indexes generated local reports and regression snapshots.

The manifest contract is defined by `schemas/report_manifest.schema.json` and checked by:

```bash
python3 src/validate_report_manifest.py
```

The validator runs after report generation in `scripts/check_all.py`, once every indexed artifact should already exist.

## Top-Level Fields

- `manifest_id`: must be `report_manifest`.
- `version`: non-empty manifest version string.
- `generated_at`: UTC timestamp in `YYYY-MM-DDTHH:MM:SSZ` format.
- `purpose`: non-empty description of the manifest role.
- `scope`: non-empty list of included local artifact scopes.
- `non_goals`: non-empty list of explicitly blocked behaviors.
- `report_artifacts`: non-empty list of generated report or snapshot artifacts.

## Artifact Fields

Each artifact entry declares:

- `artifact_id` and `label`.
- `path`, which must be a repository-relative existing artifact path.
- `artifact_type`, either `markdown_report` or `json_snapshot`.
- `generated_by`, which must point to an existing local Python script.
- `input_paths`, a non-empty list of existing local inputs used to generate or validate the artifact.
- `snapshot_dependency_paths`, which must point to indexed `json_snapshot` artifacts when present.
- `quality_gate_included`, showing whether the artifact is part of the deterministic local gate.
- `notes`, a short public-safe description.
- `safety_assertions`, which must be public-safe and must not require live execution, external actions, private data, or credentials.

The validator checks path existence, duplicate artifact IDs, duplicate artifact paths, expected file suffixes, non-empty Markdown reports, parseable JSON snapshots, generator script paths, input paths, snapshot dependency membership, and safety assertions.

M20 moves the shared JSON Schema subset mechanics used by this validator into `src/schema_validation_utils.py`. Report-specific artifact provenance checks remain in `src/validate_report_manifest.py`.

## Boundaries

Report manifest validation does not regenerate reports, rescore traces, rewrite JSONL files, collect outputs, execute target systems, call provider APIs, use network access, or apply adjudications back to source traces.
