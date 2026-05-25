# Schema Validation Coverage

This page maps every committed schema file to the local validator that owns it.
It is a deterministic quality-gate reference, not a live benchmark or execution
plan.

All validators listed here run local files only. They do not call provider APIs,
run local models, execute OpenClaw, perform browser/email actions, collect live
outputs, read credentials, or perform external actions.

## Coverage Matrix

| Schema | Owning validator | Quality gate coverage | Validated inputs | Validation mode |
| --- | --- | --- | --- | --- |
| `schemas/adapter_output.schema.json` | `src/validate_adapter_outputs.py` | Yes: `adapter output fixture validation` and `dry-run adapter output validation` in `scripts/check_all.py` | `traces/external/adapter_outputs.example.jsonl`; generated `traces/external/dry_run_adapter_outputs.jsonl` | Contract implemented in local validator code; schema is the documented JSONL record contract. |
| `schemas/adapter_run_metadata.schema.json` | `src/validate_adapter_run_metadata.py` | Yes: `adapter run metadata validation` in `scripts/check_all.py` | `traces/external/adapter_run_metadata.example.json` | Contract implemented in local validator code; schema is the documented metadata contract. |
| `schemas/adjudication.schema.json` | `src/validate_adjudications.py` | Yes: `adjudication validation` and `followup adjudication validation` in `scripts/check_all.py` | `traces/external/adjudications.example.jsonl`; `traces/external/adjudications.followup.example.jsonl` | Contract implemented in local validator code with source-trace consistency checks; schema is the documented adjudication record contract. |
| `schemas/adjudication_manifest.schema.json` | `src/validate_adjudication_manifest.py` | Yes: `adjudication manifest validation`; also preflighted by adjudication report and regression checks | `traces/external/adjudication_manifest.json` | Schema file is loaded and checked with `src/schema_validation_utils.py`, then manifest-specific fixture, source-trace, status, safety, and threshold-key checks run. |
| `schemas/eval_case.schema.json` | `src/validate_schemas.py` | Yes: `schema validation` in `scripts/check_all.py` | `evals/cases/safe_task_cases.jsonl`; `evals/cases/approval_gate_cases.jsonl`; `evals/cases/refusal_cases.jsonl`; `evals/cases/uncertainty_cases.jsonl` | Schema file is loaded and checked per JSONL record with `src/schema_validation_utils.py`; JSONL parsing and line-numbered errors remain local. |
| `schemas/report_manifest.schema.json` | `src/validate_report_manifest.py` | Yes: `report manifest validation` in `scripts/check_all.py` | `reports/comparisons/report_manifest.json` | Schema file is loaded and checked with `src/schema_validation_utils.py`, then report-specific path, generator, input, snapshot dependency, and safety checks run. |
| `schemas/saved_transcript.schema.json` | `src/replay_saved_transcripts.py` | Yes: `saved transcript replay generation` in `scripts/check_all.py` | `traces/external/saved_transcripts.example.jsonl` | Schema file is loaded and checked per JSONL record with `src/schema_validation_utils.py`, then replay-specific case, target-profile, transcript ID, and selected assistant-turn checks run. |
| `schemas/target_registry.schema.json` | `src/target_registry.py` | Yes: `target registry validation` in `scripts/check_all.py` | `targets/target_registry.json` | Schema file is loaded and checked with `src/schema_validation_utils.py`, then registry-specific path, duplicate-profile, and quality-gate profile checks run. |
| `schemas/trace.schema.json` | `src/validate_schemas.py` | Yes: `schema validation`; generated scored traces are also checked by import/evaluation/replay flows before write or comparison | `traces/scored/baseline_mock_run.jsonl`; generated scored traces from adapter import, manual-output evaluation, saved transcript replay, adjudication validation, and fixture comparison paths | Schema file is loaded and checked per JSONL record with `src/schema_validation_utils.py`; producer-specific scripts keep their own provenance and consistency checks. |

## Coverage Rules

- Every file matching `schemas/*.schema.json` must appear in this matrix.
- A schema can be directly loaded by its validator or mirrored by a local
  standard-library validator, but the matrix must state which mode applies.
- A quality-gate-covered validator must be reachable from `scripts/check_all.py`.
- Generated artifacts may be checked as part of their producer flow, but the
  producer remains responsible for non-schema semantics such as provenance,
  source references, counts, and public-safety assertions.

## Boundaries

Schema validation does not regenerate reports by itself, rescore traces, rewrite
JSONL records, promote adjudications, collect outputs, run models, execute
agents, call provider APIs, use network access, or apply external actions.
