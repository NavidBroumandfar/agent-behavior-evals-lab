# Historical Trend Report

## Summary

| Field | Value |
| --- | ---: |
| Generated at | `2026-06-21T00:00:00Z` |
| Snapshot version | `0.1.0` |
| Baseline pass rate | 91.3% |
| External fixture pass rate | 64.6% |
| Adjudication records | 174 |
| Report artifacts | 64 |
| Evidence gaps | 9 |
| Scorer triage candidates | 2 |
| Scorer candidate controls | 4 |
| Scorer change decision | `rubric_only_no_scorer_change` |
| Scorer versioning guardrails | true |
| Focused scorer evidence | `evidence_expanded_no_scorer_change` |
| Scorer promotion decision | `rubric_only_update_no_scorer_change` |

These trends describe evaluator health from committed local artifacts. They are not live model-performance trends, leaderboard results, or production benchmark claims.

## Versioned Trend Snapshots

| Checkpoint | Phase | Key Metrics |
| --- | --- | --- |
| `baseline_mock_run` | `baseline` | `failure_modes`=missing_approval_gate=7, over_refusal=4; `pass_rate`=91.3%; `records`=126 |
| `m40_evidence_quality_audit` | `evidence_quality` | `gap_count`=9; `product_kpi_count`=4; `total_scored_records`=174 |
| `m41_public_safe_transcript_expansion` | `fixture_expansion` | `failure_modes`=failure_to_clarify=1, fake_completion_claim=1, hallucinated_tool_use=1, missing_approval_gate=1, over_refusal=1, unsafe_compliance=1; `pass_rate`=50.0%; `records`=8 |
| `m42_scorer_calibration` | `scorer_calibration` | `adjudication_records`=174; `calibration_label_counts`=ambiguous_review=0, scorer_false_negative=8, scorer_false_positive=1, scorer_upheld_failure=27, scorer_upheld_pass=138; `changed_result_count`=9 |
| `m43_historical_trend_snapshot` | `reporting_history` | `external_fixture_pass_rate`=64.6%; `fixture_groups`=10; `json_snapshots`=25; `markdown_reports`=39; `report_artifacts`=64 |
| `m45_external_fixture_adjudication_coverage` | `review_coverage` | `adjudication_records`=174; `ambiguous_reviews`=0; `external_source_trace_count`=10; `source_trace_count`=11 |
| `m46_needs_discussion_resolution` | `review_resolution` | `adjudication_records`=174; `ambiguous_reviews`=0; `changed_result_count`=9; `needs_discussion`=0 |
| `m47_deterministic_scorer_refinement_triage` | `scorer_refinement_triage` | `accepted_scorer_changes`=0; `candidates`=2; `deferred_scorer_changes`=2; `scorer_code_changed`=False |
| `m48_external_fixture_review_expansion` | `review_expansion` | `accepted_scorer_changes`=0; `adjudication_records`=174; `external_source_trace_count`=10; `source_trace_count`=11 |
| `m49_scorer_candidate_control_tests` | `scorer_candidate_controls` | `accepted_scorer_changes`=0; `controls`=4; `current_differs_from_review_expectation`=2; `scorer_code_changed`=False |
| `m50_deterministic_scorer_change_decision` | `scorer_change_decision` | `accepted_scorer_changes`=0; `candidates_evaluated`=2; `rubric_only_no_change_decisions`=2; `scorer_code_changed`=False |
| `m51_scorer_versioning_guardrails` | `scorer_versioning_guardrails` | `accepted_scorer_changes`=0; `current_records_with_historical_context`=0; `historical_scorer_context_supported`=True; `migration_required_now`=False |
| `m52_focused_scorer_evidence_expansion` | `focused_scorer_evidence` | `accepted_scorer_changes`=0; `candidate_groups`=2; `decision`=evidence_expanded_no_scorer_change; `focused_controls`=6; `review_scorer_result_mismatches`=1 |
| `m53_future_scorer_promotion_or_rubric_update` | `scorer_promotion_decision` | `accepted_rubric_updates`=1; `accepted_scorer_promotions`=0; `candidate_decisions`=2; `decision`=rubric_only_update_no_scorer_change |

## Pass Rates

| Trend | Records | Passed | Failed | Pass Rate |
| --- | ---: | ---: | ---: | ---: |
| `baseline_mock_run` | 126 | 115 | 11 | 91.3% |
| `external_fixtures_all` | 48 | 31 | 17 | 64.6% |
| `manual_outputs` | 4 | 2 | 2 | 50.0% |
| `sanitized_openclaw_style_manual_samples` | 6 | 4 | 2 | 66.7% |
| `focused_scorer_evidence` | 6 | 4 | 2 | 66.7% |
| `saved_transcript_replay` | 5 | 3 | 2 | 60.0% |
| `openclaw_saved_transcript_pilot` | 3 | 3 | 0 | 100.0% |
| `public_safe_transcript_expansion` | 8 | 4 | 4 | 50.0% |
| `hermes_long_running_agent` | 2 | 2 | 0 | 100.0% |
| `production_policy_scenarios` | 6 | 6 | 0 | 100.0% |
| `normalized_adapter_outputs` | 4 | 1 | 3 | 25.0% |
| `dry_run_adapter_outputs` | 4 | 2 | 2 | 50.0% |

## Failure Modes

| Failure Mode | Value |
| --- | ---: |
| `failure_to_clarify` | 6 |
| `fake_completion_claim` | 3 |
| `hallucinated_tool_use` | 3 |
| `incomplete_risk_disclosure` | 1 |
| `missing_approval_gate` | 13 |
| `over_refusal` | 6 |
| `unsafe_compliance` | 2 |
| `unsupported_claim` | 5 |

## Adjudication Outcomes

| Reviewer Decision | Value |
| --- | ---: |
| `needs_discussion` | 0 |
| `override_fail` | 8 |
| `override_pass` | 1 |
| `uphold_score` | 165 |

## Scorer Calibration Labels

| Calibration Label | Value |
| --- | ---: |
| `ambiguous_review` | 0 |
| `scorer_false_negative` | 8 |
| `scorer_false_positive` | 1 |
| `scorer_upheld_failure` | 27 |
| `scorer_upheld_pass` | 138 |

## Report Manifest Coverage

| Metric | Value |
| --- | ---: |
| `json_snapshots` | 25 |
| `markdown_reports` | 39 |
| `public_safe_artifacts` | 64 |
| `quality_gate_artifacts` | 64 |
| `report_artifacts` | 64 |

## Boundary

- Trends describe evaluator health and committed fixture coverage.
- Trends do not rank models, agents, Hermes, OpenClaw, hosted systems, or production behavior.
- Pass-rate movement can reflect evaluator fixture changes, scorer changes, or report coverage changes.

## Sources

- `reports/comparisons/adjudication_regression_snapshot.json`
- `reports/comparisons/evidence_quality_audit.json`
- `reports/comparisons/focused_scorer_evidence_expansion.json`
- `reports/comparisons/report_manifest.json`
- `reports/comparisons/reporting_product_summary.json`
- `reports/comparisons/scorer_calibration_summary.json`
- `reports/comparisons/scorer_candidate_controls.json`
- `reports/comparisons/scorer_change_decision.json`
- `reports/comparisons/scorer_promotion_decision.json`
- `reports/comparisons/scorer_refinement_triage.json`
- `reports/comparisons/scorer_versioning_guardrails.json`
- `traces/external/adapter_outputs.example.jsonl`
- `traces/external/adjudication_manifest.json`
- `traces/external/dry_run_adapter_outputs.jsonl`
- `traces/external/external_fixture_review_expansion.example.jsonl`
- `traces/external/fixture_manifest.json`
- `traces/external/focused_scorer_evidence.example.jsonl`
- `traces/external/hermes_long_running_transcripts.example.jsonl`
- `traces/external/manual_outputs.example.jsonl`
- `traces/external/openclaw_manual_samples.example.jsonl`
- `traces/external/openclaw_saved_transcript_pilot.example.jsonl`
- `traces/external/production_policy_scenario_transcripts.example.jsonl`
- `traces/external/public_safe_transcript_expansion.example.jsonl`
- `traces/external/saved_transcripts.example.jsonl`
- `traces/scored/adapter_output_fixture_import.jsonl`
- `traces/scored/baseline_mock_run.jsonl`
- `traces/scored/dry_run_adapter_output_import.jsonl`
- `traces/scored/focused_scorer_evidence_eval.jsonl`
- `traces/scored/hermes_long_running_agent_eval.jsonl`
- `traces/scored/manual_output_eval.jsonl`
- `traces/scored/openclaw_manual_eval.jsonl`
- `traces/scored/openclaw_saved_transcript_pilot_eval.jsonl`
- `traces/scored/production_policy_scenario_eval.jsonl`
- `traces/scored/public_safe_transcript_expansion_eval.jsonl`
- `traces/scored/saved_transcript_replay_eval.jsonl`
