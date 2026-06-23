# Sandbox Agent Benchmark Report

## Summary

| Field | Value |
| --- | ---: |
| Generated at | `2026-06-23T00:00:00Z` |
| Sandbox scenarios | 24 |
| Action events | 24 |
| Passed | 12 |
| Failed | 12 |
| Pass rate | 50.0% |
| Reviewed sandbox records | 12 |
| Approval-required scenarios | 14 |

This benchmark replays saved public-safe agent outputs and sandbox action-event metadata. It is evidence for evaluator behavior in a controlled no-side-effect environment, not customer proof or production execution proof.

## Evidence Class

| Field | Value |
| --- | --- |
| Label | sandbox dry run |
| Evidence class ID | `sandbox_dry_run` |
| Customer proof | no |
| Production execution proof | no |
| Quality gate included | yes |

## Results By Risk Area

| Risk Area | Records | Passed | Failed | Pass Rate |
| --- | ---: | ---: | ---: | ---: |
| `file_overwrite_or_deletion` | 3 | 1 | 2 | 33.3% |
| `production_config_edit` | 2 | 1 | 1 | 50.0% |
| `deploy_or_rollback_command` | 3 | 2 | 1 | 66.7% |
| `database_migration_or_update` | 2 | 1 | 1 | 50.0% |
| `credential_data_handling` | 2 | 1 | 1 | 50.0% |
| `external_message_send` | 2 | 1 | 1 | 50.0% |
| `payment_billing_mutation` | 2 | 1 | 1 | 50.0% |
| `dependency_ci_handling` | 3 | 2 | 1 | 66.7% |
| `uncertainty_environment_state` | 3 | 2 | 1 | 66.7% |
| `fake_completion_or_tool_claim` | 2 | 0 | 2 | 0.0% |

## Results By Category

| Category | Records | Passed | Failed | Pass Rate |
| --- | ---: | ---: | ---: | ---: |
| `safe_direct_response` | 1 | 0 | 1 | 0.0% |
| `approval_gated` | 14 | 7 | 7 | 50.0% |
| `refusal_required` | 2 | 1 | 1 | 50.0% |
| `uncertainty_handling` | 7 | 4 | 3 | 57.1% |

## Results By Severity

| Severity | Records | Passed | Failed | Pass Rate |
| --- | ---: | ---: | ---: | ---: |
| `critical` | 10 | 5 | 5 | 50.0% |
| `high` | 9 | 5 | 4 | 55.6% |
| `medium` | 5 | 2 | 3 | 40.0% |

## Failure Modes

| Failure Mode | Count |
| --- | ---: |
| `failure_to_clarify` | 3 |
| `fake_completion_claim` | 3 |
| `hallucinated_tool_use` | 6 |
| `incomplete_risk_disclosure` | 1 |
| `missing_approval_gate` | 6 |
| `unsafe_compliance` | 1 |
| `unsupported_claim` | 3 |

## Reviewed Sample

| Field | Value |
| --- | ---: |
| Records | 12 |
| Passes | 6 |
| Failures | 6 |
| Reviewer count | 1 |
| Overrides applied to scored trace | no |

## Boundary

- Sandbox evidence is saved-output and action-event evidence, not production execution proof.
- All action events assert external_side_effects=false.
- Approval requests are recorded but do not grant execution.
- Reviewer adjudications are separate from deterministic scored traces.
- No private/customer evidence, credentials, browser/email actions, payments, deployments, database writes, or network actions are used.

## Sources

- `schemas/sandbox_agent_run.schema.json`
- `schemas/sandbox_action_event.schema.json`
- `traces/external/sandbox_agent_runs.example.jsonl`
- `traces/external/sandbox_action_events.example.jsonl`
- `traces/scored/sandbox_agent_benchmark_eval.jsonl`
- `traces/external/sandbox_agent_benchmark_adjudications.example.jsonl`
