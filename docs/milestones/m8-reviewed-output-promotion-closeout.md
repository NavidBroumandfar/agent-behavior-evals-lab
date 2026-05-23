# Milestone 8 - Reviewed Output Promotion & Trace Provenance

Date: 2026-05-23

Status: Complete / tag-ready

Milestone 8 adds the promotion layer between reviewed text-only candidates and committed fixtures. It also expands scored traces with optional first-class adapter provenance fields so imported adapter outputs no longer rely only on `mock_behavior_notes` for source context.

M8 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, file mutation, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M8.1 Optional adapter provenance fields in scored traces.
- M8.2 Adapter-output importer preservation of source record IDs, adapter names, provenance, provenance details, and metadata.
- M8.3 Reviewed-output promotion helper.
- M8.4 Manifest-entry draft generation for promoted fixtures.
- M8.5 Promotion and trace-provenance tests.
- M8.6 Quality-gate compile coverage for promotion tooling.

## Key Artifacts

Trace provenance:

- `schemas/trace.schema.json`
- `src/run_eval.py`
- `src/import_adapter_outputs.py`
- `tests/test_validate_schemas.py`
- `tests/test_adapter_output_conformance.py`

Promotion:

- `src/promote_reviewed_outputs.py`
- `tests/test_promote_reviewed_outputs.py`
- `docs/wiki/concepts/promoted_reviewed_outputs.md`

## What The Repo Can Now Do

- Preserve adapter provenance as structured scored-trace fields.
- Promote reviewed `.reviewed.jsonl` candidates into stable fixture JSONL.
- Reject unsafe or incorrectly named promotion paths.
- Refuse accidental fixture overwrite unless forced.
- Generate local manifest-entry drafts for manual fixture manifest updates.
- Keep promotion separate from live collection and scoring.

## What Remains Intentionally Blocked

- Automatic manifest mutation.
- Automatic fixture promotion into quality-gate inclusion.
- Live adapter execution.
- Provider, local model, or CLI agent calls.
- Tool execution and external actions.
- Raw output commits.
- Benchmark claims from reviewed or promoted text-only samples.

## Quality Gate

From the repository root:

```bash
python3 scripts/check_all.py
```

The gate tests promotion behavior with temporary files and validates imported adapter traces with structured provenance. It does not promote real local candidates or run live collection.

## Recommended Next Milestone

Milestone 9 should add human adjudication and arbitrary trace comparison:

1. Reviewer adjudication schema for scorer overrides or notes.
2. Adjudication-aware failure inspection.
3. Previous-vs-current comparison for arbitrary scored trace files.
4. Optional manifest-driven external fixture comparison.
5. Promotion checklist for adding a reviewed fixture to the deterministic gate.

Keep live tool execution blocked until the reviewed-output and adjudication workflow is stable.

## Tag Readiness

After the closeout commit and a clean quality gate, the repository is ready for:

`v0.8.0-reviewed-output-promotion`
