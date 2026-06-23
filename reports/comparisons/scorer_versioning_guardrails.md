# Scorer Versioning Guardrails

## Summary

| Field | Value |
| --- | ---: |
| Generated at | `2026-06-21T00:00:00Z` |
| Historical scorer context supported | true |
| Current adjudication records | 190 |
| Records with historical context | 0 |
| Migration required now | false |
| Accepted scorer changes | 0 |
| Scorer code changed | false |

M51 adds explicit validation support for preserving historical scorer outcomes if future scorer changes rewrite committed scored traces.

## Schema Guardrail

| Field | Value |
| --- | --- |
| Optional context field | `historical_scorer_context` |
| Schema version | `1.0` |
| Required fields | `schema_version`, `original_scorer_version`, `original_scorer_artifact`, `current_trace_passed`, `current_trace_score`, `current_trace_failure_modes`, `mismatch_reason` |
| Current trace fields | `current_trace_passed`, `current_trace_score`, `current_trace_failure_modes` |
| Preserved original fields | `original_passed`, `original_score`, `original_failure_modes` |

## Validation Rules

| Rule | Summary |
| --- | --- |
| `legacy_records_match_current_trace` | Adjudications without historical_scorer_context must keep original fields equal to the current source scored trace. |
| `historical_context_records_pin_current_trace` | Adjudications with historical_scorer_context must record current_trace_passed, current_trace_score, and current_trace_failure_modes that match the current source trace. |
| `historical_context_requires_real_mismatch` | historical_scorer_context is accepted only when original fields differ from the current source trace. |
| `historical_scorer_artifact_is_repo_local` | The original_scorer_artifact path must be repository-relative and must exist. |

## Future Use

- When a future scorer change rewrites a scored trace, existing adjudications can preserve the pre-change original fields.
- The historical_scorer_context block must then pin the current trace outcome for validator clarity.
- Reviewer decisions remain separate from heuristic scored traces.

## Boundary

- M51 adds schema and validation guardrails only.
- No scorer code changes are accepted in M51.
- No scored trace behavior changes are introduced in M51.
- No model-assisted judging, live provider call, runtime execution, network access, private data, or external action is introduced.

## Sources

- `reports/comparisons/scorer_change_decision.json`
- `schemas/adjudication.schema.json`
- `traces/external/adjudication_manifest.json`
- `src/validate_adjudications.py`
- `tests/test_validate_adjudications.py`
- `src/scorers.py`
- `traces/external/adjudications.example.jsonl`
- `traces/external/adjudications.followup.example.jsonl`
- `traces/external/external_fixture_adjudications.example.jsonl`
- `traces/external/external_fixture_review_expansion.example.jsonl`
- `traces/external/focused_scorer_evidence_adjudications.example.jsonl`
- `traces/external/hermes_long_running_adjudications.example.jsonl`
- `traces/external/production_policy_scenario_adjudications.example.jsonl`
- `traces/external/sandbox_agent_benchmark_adjudications.example.jsonl`
- `traces/external/m89_priority_review_adjudications.example.jsonl`
- `traces/external/m90_high_severity_pass_adjudications.example.jsonl`
- `traces/external/m91_approval_gate_pass_adjudications.example.jsonl`
- `traces/external/m92_remaining_high_severity_pass_adjudications.example.jsonl`
- `traces/external/m93_medium_priority_adjudications.example.jsonl`
- `traces/external/m94_remaining_medium_and_safe_adjudications.example.jsonl`
- `traces/external/m95_remaining_safe_direct_response_adjudications.example.jsonl`
