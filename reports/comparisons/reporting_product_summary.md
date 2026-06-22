# Reporting Product Summary

## Executive View

| Field | Value |
| --- | --- |
| Generated at | `2026-06-21T00:00:00Z` |
| Baseline result | 115 passed, 11 failed (91.3% pass rate) |
| External fixture records | 48 scored records across 10 groups |
| Review status | 120 adjudication records; 0 need discussion |
| Harness status | defer_harness_integration for openclaw; harness execution remains outside the quality gate |

This report is generated from committed local artifacts. It is a product-oriented summary for repeated development decisions, not a live model benchmark.

## Dashboard KPIs

| Metric | Value | Detail |
| --- | ---: | --- |
| Baseline Pass Rate | `91.3%` | 115 passed of 126 scored records |
| External Fixture Pass Rate | `64.6%` | 31 passed of 48 scored fixture records |
| Review Records Needing Discussion | `0` | Reviewer decisions still marked needs_discussion |
| Harness Bridge Decision | `defer_harness_integration` | Runtime-native state required: false |

## Baseline By Profile

| Profile | Total | Passed | Failed | Pass Rate |
| --- | ---: | ---: | ---: | ---: |
| `generic_assistant` | 42 | 35 | 7 | 83.3% |
| `openclaw_reference_agent` | 42 | 42 | 0 | 100.0% |
| `strict_approval_agent` | 42 | 38 | 4 | 90.5% |

## Baseline By Category

| Category | Total | Passed | Failed | Pass Rate |
| --- | ---: | ---: | ---: | ---: |
| `safe_direct_response` | 36 | 32 | 4 | 88.9% |
| `approval_gated` | 42 | 35 | 7 | 83.3% |
| `refusal_required` | 24 | 24 | 0 | 100.0% |
| `uncertainty_handling` | 24 | 24 | 0 | 100.0% |

## External Fixture Groups

| Fixture Group | Records | Passed | Failed | Pass Rate | Quality Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| `manual_outputs` | 4 | 2 | 2 | 50.0% | yes |
| `sanitized_openclaw_style_manual_samples` | 6 | 4 | 2 | 66.7% | yes |
| `focused_scorer_evidence` | 6 | 4 | 2 | 66.7% | yes |
| `saved_transcript_replay` | 5 | 3 | 2 | 60.0% | yes |
| `openclaw_saved_transcript_pilot` | 3 | 3 | 0 | 100.0% | yes |
| `public_safe_transcript_expansion` | 8 | 4 | 4 | 50.0% | yes |
| `hermes_long_running_agent` | 2 | 2 | 0 | 100.0% | yes |
| `production_policy_scenarios` | 6 | 6 | 0 | 100.0% | yes |
| `normalized_adapter_outputs` | 4 | 1 | 3 | 25.0% | yes |
| `dry_run_adapter_outputs` | 4 | 2 | 2 | 50.0% | yes |

## Engineering View

- Primary baseline failure modes: `missing_approval_gate`=7, `over_refusal`=4.
- Adjudication changed result count: 9.
- Harness bridge decision: `defer_harness_integration` for `openclaw`.

## Boundaries

- Reads already-scored traces, manifests, snapshots, and decision plans.
- Does not collect outputs, rescore records, run providers, run local models, execute agents, use network access, or perform external actions.
- All source paths are listed in the JSON snapshot at `reports/comparisons/reporting_product_summary.json`.
