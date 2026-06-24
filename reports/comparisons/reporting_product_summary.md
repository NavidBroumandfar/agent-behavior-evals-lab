# Reporting Product Summary

## Executive View

| Field | Value |
| --- | --- |
| Generated at | `2026-06-21T00:00:00Z` |
| Baseline result | 108 passed, 18 failed (85.7% pass rate) |
| External fixture records | 76 scored records across 11 groups |
| Sandbox dry-run records | 24 scored records at 50.0% pass rate |
| Review status | 190 adjudication records; 0 need discussion |
| Harness status | defer_harness_integration for openclaw; harness execution remains outside the quality gate |
| Evidence status | 24 sandbox scenarios, 28 transcript-shaped records, 5 reviewed local/open-weight ledgers |

This report is generated from committed local artifacts. It is a product-oriented summary for repeated development decisions, not a live model benchmark.

## Dashboard KPIs

| Metric | Value | Detail |
| --- | ---: | --- |
| Baseline Pass Rate | `85.7%` | 108 passed of 126 scored records |
| External Fixture Pass Rate | `57.9%` | 44 passed of 76 scored fixture records |
| Sandbox Dry-Run Pass Rate | `50.0%` | 24 sandbox scenarios scored with no external side effects |
| Evidence Class Coverage | `5` | 24 sandbox, 28 transcript-shaped, 5 reviewed local/open-weight ledgers |
| Review Records Needing Discussion | `0` | Reviewer decisions still marked needs_discussion |
| Harness Bridge Decision | `defer_harness_integration` | Runtime-native state required: false |

## Baseline By Profile

| Profile | Total | Passed | Failed | Pass Rate |
| --- | ---: | ---: | ---: | ---: |
| `generic_assistant` | 42 | 28 | 14 | 66.7% |
| `openclaw_reference_agent` | 42 | 42 | 0 | 100.0% |
| `strict_approval_agent` | 42 | 38 | 4 | 90.5% |

## Baseline By Category

| Category | Total | Passed | Failed | Pass Rate |
| --- | ---: | ---: | ---: | ---: |
| `safe_direct_response` | 36 | 32 | 4 | 88.9% |
| `approval_gated` | 42 | 28 | 14 | 66.7% |
| `refusal_required` | 24 | 24 | 0 | 100.0% |
| `uncertainty_handling` | 24 | 24 | 0 | 100.0% |

## External Fixture Groups

| Fixture Group | Records | Passed | Failed | Pass Rate | Quality Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| `manual_outputs` | 4 | 2 | 2 | 50.0% | yes |
| `sanitized_openclaw_style_manual_samples` | 6 | 4 | 2 | 66.7% | yes |
| `focused_scorer_evidence` | 10 | 4 | 6 | 40.0% | yes |
| `saved_transcript_replay` | 5 | 3 | 2 | 60.0% | yes |
| `openclaw_saved_transcript_pilot` | 3 | 3 | 0 | 100.0% | yes |
| `public_safe_transcript_expansion` | 8 | 4 | 4 | 50.0% | yes |
| `hermes_long_running_agent` | 2 | 2 | 0 | 100.0% | yes |
| `production_policy_scenarios` | 6 | 6 | 0 | 100.0% | yes |
| `sandbox_agent_benchmark` | 24 | 12 | 12 | 50.0% | yes |
| `normalized_adapter_outputs` | 4 | 2 | 2 | 50.0% | yes |
| `dry_run_adapter_outputs` | 4 | 2 | 2 | 50.0% | yes |

## Evidence Class Coverage

| Evidence Class | Count | Reviewed | Boundary |
| --- | ---: | ---: | --- |
| `hand_authored_fixture` | 52 | n/a | Synthetic and saved public-safe fixtures for evaluator coverage. |
| `real_format_saved_transcript` | 28 | n/a | Saved transcript or adapter-shaped evidence; not live production proof. |
| `sandbox_dry_run` | 24 | 12 | No-side-effect saved agent outputs with action-event metadata. |
| `local_open_weight_run_ledger` | 5 | 630 | Reviewed local/open-weight ledgers; not broad model rankings outside the claim process. |
| `human_reviewed_adjudication` | 190 | 190 | Reviewer decisions remain separate from deterministic scored traces. |

## Engineering View

- Primary baseline failure modes: `incomplete_risk_disclosure`=7, `missing_approval_gate`=7, `over_refusal`=4.
- Adjudication changed result count: 1.
- Harness bridge decision: `defer_harness_integration` for `openclaw`.

## Boundaries

- Reads already-scored traces, manifests, snapshots, and decision plans.
- Does not collect outputs, rescore records, run providers, run local models, execute agents, use network access, or perform external actions.
- All source paths are listed in the JSON snapshot at `reports/comparisons/reporting_product_summary.json`.
