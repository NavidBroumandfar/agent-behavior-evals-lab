# Historical Trend Report

## Summary

| Field | Value |
| --- | ---: |
| Generated at | `2026-06-21T00:00:00Z` |
| Snapshot version | `0.1.0` |
| Baseline pass rate | 85.7% |
| External fixture pass rate | 57.9% |
| Adjudication records | 190 |
| Report artifacts | 66 |
| Evidence gaps | 9 |
| Scorer triage candidates | 2 |
| Scorer candidate controls | 4 |
| Scorer change decision | `approval_disclosure_scorer_change_accepted` |
| Scorer versioning guardrails | true |
| Focused scorer evidence | `m99_approval_disclosure_scorer_hardened` |
| Scorer promotion decision | `approval_disclosure_scorer_promotion_accepted` |

These trends describe evaluator health from committed local artifacts. They are not live model-performance trends, leaderboard results, or production benchmark claims.

## Versioned Trend Snapshots

| Checkpoint | Phase | Key Metrics |
| --- | --- | --- |
| `baseline_mock_run` | `baseline` | `failure_modes`=incomplete_risk_disclosure=7, missing_approval_gate=7, over_refusal=4; `pass_rate`=85.7%; `records`=126 |
| `m40_evidence_quality_audit` | `evidence_quality` | `gap_count`=9; `product_kpi_count`=6; `total_scored_records`=202 |
| `m41_public_safe_transcript_expansion` | `fixture_expansion` | `failure_modes`=failure_to_clarify=1, fake_completion_claim=1, hallucinated_tool_use=1, missing_approval_gate=1, over_refusal=1, unsafe_compliance=1; `pass_rate`=50.0%; `records`=8 |
| `m42_scorer_calibration` | `scorer_calibration` | `adjudication_records`=190; `calibration_label_counts`=ambiguous_review=0, scorer_false_negative=0, scorer_false_positive=1, scorer_upheld_failure=43, scorer_upheld_pass=146; `changed_result_count`=1 |
| `m43_historical_trend_snapshot` | `reporting_history` | `external_fixture_pass_rate`=57.9%; `fixture_groups`=11; `json_snapshots`=26; `markdown_reports`=40; `report_artifacts`=66 |
| `m45_external_fixture_adjudication_coverage` | `review_coverage` | `adjudication_records`=190; `ambiguous_reviews`=0; `external_source_trace_count`=11; `source_trace_count`=12 |
| `m46_needs_discussion_resolution` | `review_resolution` | `adjudication_records`=190; `ambiguous_reviews`=0; `changed_result_count`=1; `needs_discussion`=0 |
| `m47_deterministic_scorer_refinement_triage` | `scorer_refinement_triage` | `accepted_scorer_changes`=1; `candidates`=2; `deferred_scorer_changes`=1; `scorer_code_changed`=False |
| `m48_external_fixture_review_expansion` | `review_expansion` | `accepted_scorer_changes`=1; `adjudication_records`=190; `external_source_trace_count`=11; `source_trace_count`=12 |
| `m49_scorer_candidate_control_tests` | `scorer_candidate_controls` | `accepted_scorer_changes`=1; `controls`=4; `current_differs_from_review_expectation`=1; `scorer_code_changed`=True |
| `m50_deterministic_scorer_change_decision` | `scorer_change_decision` | `accepted_scorer_changes`=1; `candidates_evaluated`=2; `rubric_only_no_change_decisions`=1; `scorer_code_changed`=True |
| `m51_scorer_versioning_guardrails` | `scorer_versioning_guardrails` | `accepted_scorer_changes`=0; `current_records_with_historical_context`=0; `historical_scorer_context_supported`=True; `migration_required_now`=False |
| `m52_focused_scorer_evidence_expansion` | `focused_scorer_evidence` | `accepted_scorer_changes`=1; `candidate_groups`=2; `decision`=m99_approval_disclosure_scorer_hardened; `focused_controls`=10; `review_scorer_result_mismatches`=0 |
| `m53_future_scorer_promotion_or_rubric_update` | `scorer_promotion_decision` | `accepted_rubric_updates`=0; `accepted_scorer_promotions`=1; `candidate_decisions`=2; `decision`=approval_disclosure_scorer_promotion_accepted |

## Pass Rates

| Trend | Records | Passed | Failed | Pass Rate |
| --- | ---: | ---: | ---: | ---: |
| `baseline_mock_run` | 126 | 108 | 18 | 85.7% |
| `external_fixtures_all` | 76 | 44 | 32 | 57.9% |
| `sandbox_dry_run` | 24 | 12 | 12 | 50.0% |
| `manual_outputs` | 4 | 2 | 2 | 50.0% |
| `sanitized_openclaw_style_manual_samples` | 6 | 4 | 2 | 66.7% |
| `focused_scorer_evidence` | 10 | 4 | 6 | 40.0% |
| `saved_transcript_replay` | 5 | 3 | 2 | 60.0% |
| `openclaw_saved_transcript_pilot` | 3 | 3 | 0 | 100.0% |
| `public_safe_transcript_expansion` | 8 | 4 | 4 | 50.0% |
| `hermes_long_running_agent` | 2 | 2 | 0 | 100.0% |
| `production_policy_scenarios` | 6 | 6 | 0 | 100.0% |
| `sandbox_agent_benchmark` | 24 | 12 | 12 | 50.0% |
| `normalized_adapter_outputs` | 4 | 2 | 2 | 50.0% |
| `dry_run_adapter_outputs` | 4 | 2 | 2 | 50.0% |

## Failure Modes

| Failure Mode | Value |
| --- | ---: |
| `failure_to_clarify` | 9 |
| `fake_completion_claim` | 6 |
| `hallucinated_tool_use` | 9 |
| `incomplete_risk_disclosure` | 11 |
| `missing_approval_gate` | 20 |
| `over_refusal` | 6 |
| `unsafe_compliance` | 3 |
| `unsupported_claim` | 8 |

## Adjudication Outcomes

| Reviewer Decision | Value |
| --- | ---: |
| `needs_discussion` | 0 |
| `override_fail` | 0 |
| `override_pass` | 1 |
| `uphold_score` | 189 |

## Scorer Calibration Labels

| Calibration Label | Value |
| --- | ---: |
| `ambiguous_review` | 0 |
| `scorer_false_negative` | 0 |
| `scorer_false_positive` | 1 |
| `scorer_upheld_failure` | 43 |
| `scorer_upheld_pass` | 146 |

## Report Manifest Coverage

| Metric | Value |
| --- | ---: |
| `json_snapshots` | 26 |
| `markdown_reports` | 40 |
| `public_safe_artifacts` | 66 |
| `quality_gate_artifacts` | 66 |
| `report_artifacts` | 66 |

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
- `traces/external/sandbox_agent_runs.example.jsonl`
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
- `traces/scored/sandbox_agent_benchmark_eval.jsonl`
- `traces/scored/saved_transcript_replay_eval.jsonl`
