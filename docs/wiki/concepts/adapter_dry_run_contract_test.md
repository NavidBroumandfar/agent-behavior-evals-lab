# Adapter Dry-Run Contract Test

The adapter dry-run contract test is a deterministic fixture producer for the normalized adapter-output path. It proves that an adapter-like component can emit records matching `schemas/adapter_output.schema.json`, then pass through validation and import into scored traces.

`src/dry_run_adapter.py` is not a real model adapter. It does not call provider APIs, run local models, execute OpenClaw, use browser or email tools, call the network, run subprocesses, use credentials, or inspect private runtime state. It only writes `traces/external/dry_run_adapter_outputs.jsonl`.

## What It Emits

The dry-run adapter writes a small public-safe JSONL fixture with:

- `source_type`: `dry_run_adapter_output`
- `adapter_name`: `deterministic_dry_run_adapter`
- `adapter_version`: `0.1.0`
- `created_at`: `2026-05-10T00:00:00Z`
- `provenance.public_safe`: `true`
- `provenance.live_execution`: `false`
- `provenance.external_actions`: `false`
- `provenance.contains_private_data`: `false`
- `provenance_details.source_origin`: `dry_run_contract`
- `provenance_details.execution_mode`: `dry_run_only`
- `provenance_details.data_classification`: `public_synthetic`
- `provenance_details.action_evidence`: `none_required`

The records map to existing eval case IDs and include deterministic final `output_text`. Some outputs pass and some fail under the existing scorer; the point is to test the contract path, not to optimize scores.

## Contract Flow

Run the full dry-run path from the repository root:

```bash
python3 src/dry_run_adapter.py
python3 src/validate_adapter_outputs.py traces/external/dry_run_adapter_outputs.jsonl
python3 src/import_adapter_outputs.py traces/external/dry_run_adapter_outputs.jsonl traces/scored/dry_run_adapter_output_import.jsonl
```

Validation proves the dry-run records satisfy the normalized adapter-output contract. Import proves those validated records can join to existing eval cases, use the existing scorer unchanged, and produce scored traces compatible with `schemas/trace.schema.json`.

## Not A Real Adapter

The dry-run adapter is intentionally static and local. It does not collect outputs from a target system. It does not execute prompts against a provider, model, CLI agent, or OpenClaw runtime. It exists only to lock down the file contract and quality-gate path that future adapters must satisfy.

## Comparison Report

M4.4 includes the dry-run scored trace in `src/compare_external_fixtures.py`. The external fixture comparison report can therefore show the dry-run contract test beside manual outputs, sanitized OpenClaw-style samples, saved transcript replay, and normalized adapter-output import.

## Preparing Later Adapter Design

A later provider-agnostic adapter interface can use this dry-run path as its acceptance test. Future adapter-like producers should be able to emit normalized records, pass validation, import into scored traces, and appear in comparison reports before any live execution is considered.
