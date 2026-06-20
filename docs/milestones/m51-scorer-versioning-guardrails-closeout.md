# Milestone 51 - Scorer Versioning Guardrails

Date: 2026-06-21

Status: Complete / review-ready

Milestone 51 adds explicit adjudication guardrails for preserving historical scorer outcomes if future scorer behavior changes.

M51 does not add live provider execution, local model execution, live Hermes or OpenClaw execution, CLI-agent execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, shell execution, autonomous actions, private runtime-log ingestion, gated LLM review, private output collection, runtime harness execution, raw-output promotion, scored trace rewrites, or scorer behavior changes.

## Completed Slices

- M51.1 Added optional `historical_scorer_context` support to `schemas/adjudication.schema.json`.
- M51.2 Updated `src/validate_adjudications.py` to distinguish legacy current-trace matching from explicit historical scorer context.
- M51.3 Added validator tests for accepted historical context, wrong current-trace context, unnecessary context, and non-local scorer artifacts.
- M51.4 Added `src/scorer_versioning_guardrails.py`.
- M51.5 Added `reports/comparisons/scorer_versioning_guardrails.json`.
- M51.6 Added `reports/comparisons/scorer_versioning_guardrails.md`.
- M51.7 Indexed the new artifacts in `reports/comparisons/report_manifest.json`.
- M51.8 Updated evidence audit, trend snapshots, release notes, roadmap, wiki, and tests.

## Guardrail Outcome

- Historical scorer context supported: true
- Current adjudication records: 42
- Records with historical scorer context: 0
- Migration required now: false
- Accepted scorer changes: 0
- Scorer code changed: false
- Scored trace behavior changed: false

## Validation Behavior

Adjudications without `historical_scorer_context` keep the existing rule: `original_passed`, `original_score`, and `original_failure_modes` must match the current source scored trace.

Adjudications with `historical_scorer_context` may preserve pre-change original scorer fields only when the context also records current trace fields that match the source trace. The context is accepted only when original fields actually differ from the current trace, and its `original_scorer_artifact` must be a repository-local existing path.

## Key Artifacts

Code and tests:

- `src/validate_adjudications.py`
- `src/scorer_versioning_guardrails.py`
- `tests/test_validate_adjudications.py`
- `tests/test_scorer_versioning_guardrails.py`

Schema and generated artifacts:

- `schemas/adjudication.schema.json`
- `reports/comparisons/scorer_versioning_guardrails.json`
- `reports/comparisons/scorer_versioning_guardrails.md`

Updated downstream artifacts:

- `reports/comparisons/report_manifest.json`
- `reports/comparisons/evidence_quality_audit.json`
- `reports/comparisons/evidence_quality_audit.md`
- `reports/comparisons/historical_trend_snapshot.json`
- `reports/comparisons/historical_trend_report.md`
- `reports/comparisons/release_notes_latest.json`
- `reports/comparisons/release_notes_latest.md`

## Boundary

M51 adds schema and validation support only. It does not modify `src/scorers.py`, regenerate traces due to scorer behavior changes, apply reviewer decisions back into scored traces, or accept model-assisted judging.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

Proceed to M52 Focused Scorer Evidence Expansion. The next useful phase is adding public-safe adjudicated controls that can use the M51 guardrails if a later scorer change rewrites trace behavior.
