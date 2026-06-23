# Evidence Quality Audit

## Summary

| Field | Value |
| --- | ---: |
| Eval cases | 42 |
| Total scored records | 202 |
| External fixture records | 76 |
| Adjudication records | 190 |
| Evidence gaps | 9 |

This is an audit of committed local evidence. It is not a live model benchmark, leaderboard, or real-world agent quality claim.

## Inventory

### Eval Cases

| Case file | Cases | Categories |
| --- | ---: | --- |
| `evals/cases/safe_task_cases.jsonl` | 12 | `safe_direct_response`: 12 |
| `evals/cases/approval_gate_cases.jsonl` | 14 | `approval_gated`: 14 |
| `evals/cases/refusal_cases.jsonl` | 8 | `refusal_required`: 8 |
| `evals/cases/uncertainty_cases.jsonl` | 8 | `uncertainty_handling`: 8 |

### Scored Evidence

| Evidence set | Records | Passed | Failed | Pass rate |
| --- | ---: | ---: | ---: | ---: |
| Baseline mock trace | 126 | 108 | 18 | 85.7% |
| External fixture traces | 76 | 44 | 32 | 57.9% |

### External Fixtures

| Fixture group | Source type | Scored | Failed | Pass rate |
| --- | --- | ---: | ---: | ---: |
| `manual_outputs` | `manual_output` | 4 | 2 | 50.0% |
| `sanitized_openclaw_style_manual_samples` | `openclaw_style_manual_output` | 6 | 2 | 66.7% |
| `focused_scorer_evidence` | `focused_scorer_evidence` | 10 | 6 | 40.0% |
| `saved_transcript_replay` | `saved_transcript_replay` | 5 | 2 | 60.0% |
| `openclaw_saved_transcript_pilot` | `openclaw_saved_transcript_pilot` | 3 | 0 | 100.0% |
| `public_safe_transcript_expansion` | `public_safe_transcript_expansion` | 8 | 4 | 50.0% |
| `hermes_long_running_agent` | `hermes_long_running_agent` | 2 | 0 | 100.0% |
| `production_policy_scenarios` | `production_policy_scenario` | 6 | 0 | 100.0% |
| `sandbox_agent_benchmark` | `sandbox_agent_run` | 24 | 12 | 50.0% |
| `normalized_adapter_outputs` | `normalized_adapter_output` | 4 | 2 | 50.0% |
| `dry_run_adapter_outputs` | `dry_run_adapter_output` | 4 | 2 | 50.0% |

### Adjudication Coverage

| Coverage area | Reviewed | Source records | Coverage |
| --- | ---: | ---: | ---: |
| `traces/scored/adapter_output_fixture_import.jsonl` | 4 | 4 | 100.0% |
| `traces/scored/baseline_mock_run.jsonl` | 126 | 126 | 100.0% |
| `traces/scored/dry_run_adapter_output_import.jsonl` | 4 | 4 | 100.0% |
| `traces/scored/focused_scorer_evidence_eval.jsonl` | 10 | 10 | 100.0% |
| `traces/scored/hermes_long_running_agent_eval.jsonl` | 2 | 2 | 100.0% |
| `traces/scored/manual_output_eval.jsonl` | 4 | 4 | 100.0% |
| `traces/scored/openclaw_manual_eval.jsonl` | 6 | 6 | 100.0% |
| `traces/scored/openclaw_saved_transcript_pilot_eval.jsonl` | 3 | 3 | 100.0% |
| `traces/scored/production_policy_scenario_eval.jsonl` | 6 | 6 | 100.0% |
| `traces/scored/public_safe_transcript_expansion_eval.jsonl` | 8 | 8 | 100.0% |
| `traces/scored/sandbox_agent_benchmark_eval.jsonl` | 12 | 24 | 50.0% |
| `traces/scored/saved_transcript_replay_eval.jsonl` | 5 | 5 | 100.0% |
| category `approval_gated` | 74 | 79 | 93.7% |
| category `refusal_required` | 34 | 34 | 100.0% |
| category `safe_direct_response` | 46 | 47 | 97.9% |
| category `uncertainty_handling` | 36 | 42 | 85.7% |

### Report Artifacts

| Metric | Value |
| --- | ---: |
| Report artifacts | 66 |
| Quality-gate artifacts | 66 |
| Markdown reports | 40 |
| JSON snapshots | 26 |

## Gap Report

### Missing Fixture Coverage

| Gap | Severity | Summary | Sources |
| --- | --- | --- | --- |
| `no_live_runtime_evidence` | high | The committed evidence is saved, sanitized, synthetic, or mock evidence only; it does not prove live runtime behavior. | `traces/external/fixture_manifest.json`, `traces/external/harness_bridge_plan.example.json`, `docs/roadmap.md` |
| `small_external_fixture_groups` | medium | External fixture groups contain 2-24 scored records each (76 total), so they validate paths but are not representative samples. | `traces/external/manual_outputs.example.jsonl`, `traces/external/openclaw_manual_samples.example.jsonl`, `traces/external/focused_scorer_evidence.example.jsonl`, +8 more |
| `refusal_required_review_gap` | medium | Refusal-required reviewed source records have 100.0% adjudication coverage (34 reviewed records). | `reports/comparisons/adjudication_regression_snapshot.json`, `traces/external/adjudication_manifest.json` |

### Scorer Weakness

| Gap | Severity | Summary | Sources |
| --- | --- | --- | --- |
| `heuristic_scorer_not_semantic_judge` | high | The v0 scorer uses deterministic phrase and pattern checks, so scores are triage signals rather than ground truth. | `src/scorers.py`, `docs/wiki/concepts/v0_scorer_limitations.md` |
| `limited_adjudication_calibration_set` | medium | 190 adjudications cover 12 source traces; all manifest-backed external fixture traces now have adjudication coverage. M49 controls cover 4 focused scorer cases with 1 accepted scorer changes. M50 records decision `approval_disclosure_scorer_change_accepted` with 1 accepted scorer changes. M51 historical scorer context support is true. M52 adds 10 focused controls with decision `m99_approval_disclosure_scorer_hardened`. M53 records decision `approval_disclosure_scorer_promotion_accepted` with 0 accepted rubric updates and 1 accepted scorer promotions. | `traces/external/adjudication_manifest.json`, `reports/comparisons/adjudication_regression_snapshot.json`, `reports/comparisons/scorer_refinement_triage.json`, +5 more |
| `failure_modes_are_taxonomy_bound` | medium | Current scored traces surface this fixed failure-mode set: failure_to_clarify, fake_completion_claim, hallucinated_tool_use, incomplete_risk_disclosure, missing_approval_gate, over_refusal, unsafe_compliance, unsupported_claim; semantic variants still require review. | `traces/scored/baseline_mock_run.jsonl`, `traces/scored/manual_output_eval.jsonl`, `traces/scored/openclaw_manual_eval.jsonl`, +9 more |

### Reporting Weakness

| Gap | Severity | Summary | Sources |
| --- | --- | --- | --- |
| `trend_snapshots_are_descriptive_not_gates` | low | Historical trend snapshots are present, but they describe evaluator health and do not prove model performance. | `reports/comparisons/historical_trend_snapshot.json`, `reports/comparisons/historical_trend_report.md`, `reports/comparisons/report_manifest.json` |
| `audit_findings_are_not_gate_thresholds` | low | M40 recommendations are descriptive evidence gaps; they do not automatically fail or rewrite scored traces. | `reports/comparisons/report_manifest.json`, `reports/comparisons/evidence_quality_audit.json` |
| `report_artifacts_outpace_review_depth` | low | 66 report artifacts are indexed, while 190 adjudication records exist. | `reports/comparisons/report_manifest.json`, `reports/comparisons/adjudication_regression_snapshot.json` |

## Recommendations

| Recommendation | Phase | Priority | Summary |
| --- | --- | --- | --- |
| `prioritize_public_safe_transcripts_for_review` | `Post-M53 maintenance` | high | Continue public-safe review depth for small fixture groups and remaining category coverage gaps. |
| `calibrate_before_scorer_changes` | `Post-M53 maintenance` | high | Keep M53 rubric-only guidance separate from scorer behavior until more focused evidence supports a narrow deterministic scorer change. |
| `maintain_evaluator_health_trends` | `M43` | medium | Keep versioned trend snapshots reviewed when committed reports, fixtures, or adjudication artifacts change. |

## Boundary

- This audit can describe local fixture, scorer, adjudication, and reporting coverage.
- This audit cannot rank models, agents, Hermes, OpenClaw, hosted systems, or production behavior.
- This audit does not prove live runtime behavior because it uses committed saved artifacts only.

## Sources

- `evals/cases/safe_task_cases.jsonl`
- `evals/cases/approval_gate_cases.jsonl`
- `evals/cases/refusal_cases.jsonl`
- `evals/cases/uncertainty_cases.jsonl`
- `traces/scored/baseline_mock_run.jsonl`
- `traces/external/fixture_manifest.json`
- `traces/external/adjudication_manifest.json`
- `reports/comparisons/adjudication_regression_snapshot.json`
- `reports/comparisons/report_manifest.json`
- `reports/comparisons/reporting_product_summary.json`
- `reports/comparisons/historical_trend_snapshot.json`
- `reports/comparisons/historical_trend_report.md`
- `reports/comparisons/scorer_refinement_triage.json`
- `reports/comparisons/scorer_refinement_triage.md`
- `reports/comparisons/scorer_candidate_controls.json`
- `reports/comparisons/scorer_candidate_controls.md`
- `reports/comparisons/scorer_change_decision.json`
- `reports/comparisons/scorer_change_decision.md`
- `reports/comparisons/scorer_versioning_guardrails.json`
- `reports/comparisons/scorer_versioning_guardrails.md`
- `reports/comparisons/focused_scorer_evidence_expansion.json`
- `reports/comparisons/focused_scorer_evidence_expansion.md`
- `reports/comparisons/scorer_promotion_decision.json`
- `reports/comparisons/scorer_promotion_decision.md`
- `traces/external/harness_bridge_plan.example.json`
- `src/scorers.py`
- `docs/wiki/concepts/v0_scorer_limitations.md`
- `docs/roadmap.md`
