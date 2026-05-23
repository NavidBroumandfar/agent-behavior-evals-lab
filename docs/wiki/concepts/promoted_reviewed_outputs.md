# Promoted Reviewed Outputs

Promoted reviewed outputs are reviewed `.reviewed.jsonl` adapter-output candidates that a maintainer intentionally copies into a stable fixture path under `traces/external/`.

Promotion is explicit. It does not run live collection, score records, or update the fixture manifest automatically.

## Promotion Command

Use `src/promote_reviewed_outputs.py` after a reviewed candidate has passed adapter-output validation and a maintainer wants to prepare it as a committed fixture.

The command:

- Requires input ending in `.reviewed.jsonl`.
- Requires output under `traces/external/`.
- Rejects output filenames ending in `.local.jsonl`, `.private.jsonl`, or `.reviewed.jsonl`.
- Refuses to overwrite existing fixtures unless `--force` is provided.
- Validates the promoted output with `src/validate_adapter_outputs.py`.
- Can write a `.manifest_entry.local.json` draft for manual review.

## Manifest Entry Draft

The manifest entry draft is intentionally local-only. It helps a maintainer update `traces/external/fixture_manifest.json`, but it is not inserted automatically because fixture promotion should remain a reviewed repository change.

Promoted entries default to `quality_gate_included: false` in the draft. A maintainer can later decide whether the fixture should enter the deterministic quality gate after adding scored traces, reports, and expected counts.

## Trace Provenance

M8 also adds optional first-class adapter provenance fields to scored traces:

- `source_record_id`
- `source_type`
- `adapter_name`
- `adapter_version`
- `adapter_provenance`
- `adapter_provenance_details`
- `adapter_metadata`

These fields let reports and future comparison tools read adapter context without parsing `mock_behavior_notes`.
