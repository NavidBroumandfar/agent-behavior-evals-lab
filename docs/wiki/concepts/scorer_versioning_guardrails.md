# Scorer Versioning Guardrails

M51 adds optional adjudication metadata for preserving pre-change scorer outcomes if future scorer behavior changes.

Generated artifacts:

- `reports/comparisons/scorer_versioning_guardrails.json`
- `reports/comparisons/scorer_versioning_guardrails.md`

Generator:

- `src/scorer_versioning_guardrails.py`

Schema and validator:

- `schemas/adjudication.schema.json`
- `src/validate_adjudications.py`

## Historical Scorer Context

Adjudication records may include `historical_scorer_context` when the original scorer result being reviewed came from a prior scorer version and no longer matches the current scored trace.

Without that context, adjudication `original_*` fields must continue to match the current source trace exactly.

With that context, the validator requires current trace fields that match the source trace:

- `current_trace_passed`
- `current_trace_score`
- `current_trace_failure_modes`

The context is accepted only when original fields actually differ from the current trace, and `original_scorer_artifact` must point to an existing repository-local path.

## Current State

At M51 closeout, the committed adjudication fixtures contained 42 records and 0 records with `historical_scorer_context`. No migration was required because M51 did not change scorer behavior.

M52 expands the committed adjudication fixtures to 48 records while still requiring 0 records with `historical_scorer_context`, because M52 also keeps scorer behavior unchanged.

## Boundary

The guardrail reads committed public-safe artifacts only. It does not call providers, run local models, execute Hermes or OpenClaw, use browser/email tools, inspect private logs, mutate target files, use credentials, collect outputs, or perform external actions.
