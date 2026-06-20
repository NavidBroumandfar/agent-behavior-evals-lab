# Historical Trend Report

## Summary

| Field | Value |
| --- | ---: |
| Generated at | `2026-06-20T00:00:00Z` |
| Snapshot version | `0.1.0` |
| Baseline pass rate | 91.3% |
| External fixture pass rate | 55.9% |
| Adjudication records | 12 |
| Report artifacts | 24 |
| Evidence gaps | 10 |

These trends describe evaluator health from committed local artifacts. They are not live model-performance trends, leaderboard results, or production benchmark claims.

## Versioned Trend Snapshots

| Checkpoint | Phase | Key Metrics |
| --- | --- | --- |
| `baseline_mock_run` | `baseline` | `failure_modes`=missing_approval_gate=7, over_refusal=4; `pass_rate`=91.3%; `records`=126 |
| `m40_evidence_quality_audit` | `evidence_quality` | `gap_count`=10; `product_kpi_count`=4; `total_scored_records`=160 |
| `m41_public_safe_transcript_expansion` | `fixture_expansion` | `failure_modes`=failure_to_clarify=1, fake_completion_claim=1, hallucinated_tool_use=1, missing_approval_gate=1, over_refusal=1, unsafe_compliance=1; `pass_rate`=50.0%; `records`=8 |
| `m42_scorer_calibration` | `scorer_calibration` | `adjudication_records`=12; `calibration_label_counts`=ambiguous_review=3, scorer_false_negative=1, scorer_false_positive=1, scorer_upheld_failure=5, scorer_upheld_pass=2; `changed_result_count`=2 |
| `m43_historical_trend_snapshot` | `reporting_history` | `external_fixture_pass_rate`=55.9%; `fixture_groups`=7; `json_snapshots`=7; `markdown_reports`=17; `report_artifacts`=24 |

## Pass Rates

| Trend | Records | Passed | Failed | Pass Rate |
| --- | ---: | ---: | ---: | ---: |
| `baseline_mock_run` | 126 | 115 | 11 | 91.3% |
| `external_fixtures_all` | 34 | 19 | 15 | 55.9% |
| `manual_outputs` | 4 | 2 | 2 | 50.0% |
| `sanitized_openclaw_style_manual_samples` | 6 | 4 | 2 | 66.7% |
| `saved_transcript_replay` | 5 | 3 | 2 | 60.0% |
| `openclaw_saved_transcript_pilot` | 3 | 3 | 0 | 100.0% |
| `public_safe_transcript_expansion` | 8 | 4 | 4 | 50.0% |
| `normalized_adapter_outputs` | 4 | 1 | 3 | 25.0% |
| `dry_run_adapter_outputs` | 4 | 2 | 2 | 50.0% |

## Failure Modes

| Failure Mode | Value |
| --- | ---: |
| `failure_to_clarify` | 6 |
| `fake_completion_claim` | 3 |
| `hallucinated_tool_use` | 3 |
| `incomplete_risk_disclosure` | 1 |
| `missing_approval_gate` | 12 |
| `over_refusal` | 5 |
| `unsafe_compliance` | 2 |
| `unsupported_claim` | 5 |

## Adjudication Outcomes

| Reviewer Decision | Value |
| --- | ---: |
| `needs_discussion` | 3 |
| `override_fail` | 1 |
| `override_pass` | 1 |
| `uphold_score` | 7 |

## Scorer Calibration Labels

| Calibration Label | Value |
| --- | ---: |
| `ambiguous_review` | 3 |
| `scorer_false_negative` | 1 |
| `scorer_false_positive` | 1 |
| `scorer_upheld_failure` | 5 |
| `scorer_upheld_pass` | 2 |

## Report Manifest Coverage

| Metric | Value |
| --- | ---: |
| `json_snapshots` | 7 |
| `markdown_reports` | 17 |
| `public_safe_artifacts` | 24 |
| `quality_gate_artifacts` | 24 |
| `report_artifacts` | 24 |

## Boundary

- Trends describe evaluator health and committed fixture coverage.
- Trends do not rank models, agents, Hermes, OpenClaw, hosted systems, or production behavior.
- Pass-rate movement can reflect evaluator fixture changes, scorer changes, or report coverage changes.

## Sources

- `reports/comparisons/adjudication_regression_snapshot.json`
- `reports/comparisons/evidence_quality_audit.json`
- `reports/comparisons/report_manifest.json`
- `reports/comparisons/reporting_product_summary.json`
- `reports/comparisons/scorer_calibration_summary.json`
- `traces/external/adapter_outputs.example.jsonl`
- `traces/external/dry_run_adapter_outputs.jsonl`
- `traces/external/fixture_manifest.json`
- `traces/external/manual_outputs.example.jsonl`
- `traces/external/openclaw_manual_samples.example.jsonl`
- `traces/external/openclaw_saved_transcript_pilot.example.jsonl`
- `traces/external/public_safe_transcript_expansion.example.jsonl`
- `traces/external/saved_transcripts.example.jsonl`
- `traces/scored/adapter_output_fixture_import.jsonl`
- `traces/scored/baseline_mock_run.jsonl`
- `traces/scored/dry_run_adapter_output_import.jsonl`
- `traces/scored/manual_output_eval.jsonl`
- `traces/scored/openclaw_manual_eval.jsonl`
- `traces/scored/openclaw_saved_transcript_pilot_eval.jsonl`
- `traces/scored/public_safe_transcript_expansion_eval.jsonl`
- `traces/scored/saved_transcript_replay_eval.jsonl`
