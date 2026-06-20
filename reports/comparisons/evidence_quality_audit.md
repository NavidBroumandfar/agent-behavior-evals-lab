# Evidence Quality Audit

## Summary

| Field | Value |
| --- | ---: |
| Eval cases | 42 |
| Total scored records | 160 |
| External fixture records | 34 |
| Adjudication records | 42 |
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
| Baseline mock trace | 126 | 115 | 11 | 91.3% |
| External fixture traces | 34 | 19 | 15 | 55.9% |

### External Fixtures

| Fixture group | Source type | Scored | Failed | Pass rate |
| --- | --- | ---: | ---: | ---: |
| `manual_outputs` | `manual_output` | 4 | 2 | 50.0% |
| `sanitized_openclaw_style_manual_samples` | `openclaw_style_manual_output` | 6 | 2 | 66.7% |
| `saved_transcript_replay` | `saved_transcript_replay` | 5 | 2 | 60.0% |
| `openclaw_saved_transcript_pilot` | `openclaw_saved_transcript_pilot` | 3 | 0 | 100.0% |
| `public_safe_transcript_expansion` | `public_safe_transcript_expansion` | 8 | 4 | 50.0% |
| `normalized_adapter_outputs` | `normalized_adapter_output` | 4 | 3 | 25.0% |
| `dry_run_adapter_outputs` | `dry_run_adapter_output` | 4 | 2 | 50.0% |

### Adjudication Coverage

| Coverage area | Reviewed | Source records | Coverage |
| --- | ---: | ---: | ---: |
| `traces/scored/adapter_output_fixture_import.jsonl` | 4 | 4 | 100.0% |
| `traces/scored/baseline_mock_run.jsonl` | 12 | 126 | 9.5% |
| `traces/scored/dry_run_adapter_output_import.jsonl` | 4 | 4 | 100.0% |
| `traces/scored/manual_output_eval.jsonl` | 4 | 4 | 100.0% |
| `traces/scored/openclaw_manual_eval.jsonl` | 6 | 6 | 100.0% |
| `traces/scored/openclaw_saved_transcript_pilot_eval.jsonl` | 3 | 3 | 100.0% |
| `traces/scored/public_safe_transcript_expansion_eval.jsonl` | 4 | 8 | 50.0% |
| `traces/scored/saved_transcript_replay_eval.jsonl` | 5 | 5 | 100.0% |
| category `approval_gated` | 14 | 52 | 26.9% |
| category `refusal_required` | 7 | 32 | 21.9% |
| category `safe_direct_response` | 11 | 43 | 25.6% |
| category `uncertainty_handling` | 10 | 33 | 30.3% |

### Report Artifacts

| Metric | Value |
| --- | ---: |
| Report artifacts | 32 |
| Quality-gate artifacts | 32 |
| Markdown reports | 21 |
| JSON snapshots | 11 |

## Gap Report

### Missing Fixture Coverage

| Gap | Severity | Summary | Sources |
| --- | --- | --- | --- |
| `no_live_runtime_evidence` | high | The committed evidence is saved, sanitized, synthetic, or mock evidence only; it does not prove live runtime behavior. | `traces/external/fixture_manifest.json`, `traces/external/harness_bridge_plan.example.json`, `docs/roadmap.md` |
| `small_external_fixture_groups` | medium | External fixture groups contain 3-8 scored records each (34 total), so they validate paths but are not representative samples. | `traces/external/manual_outputs.example.jsonl`, `traces/external/openclaw_manual_samples.example.jsonl`, `traces/external/saved_transcripts.example.jsonl`, +4 more |
| `refusal_required_review_gap` | medium | Refusal-required reviewed source records have 21.9% adjudication coverage (7 reviewed records). | `reports/comparisons/adjudication_regression_snapshot.json`, `traces/external/adjudication_manifest.json` |

### Scorer Weakness

| Gap | Severity | Summary | Sources |
| --- | --- | --- | --- |
| `heuristic_scorer_not_semantic_judge` | high | The v0 scorer uses deterministic phrase and pattern checks, so scores are triage signals rather than ground truth. | `src/scorers.py`, `docs/wiki/concepts/v0_scorer_limitations.md` |
| `limited_adjudication_calibration_set` | medium | 42 adjudications cover 8 source traces; all manifest-backed external fixture traces now have adjudication coverage. M49 controls cover 4 focused scorer cases with 0 accepted scorer changes. M50 records decision `rubric_only_no_scorer_change` with 0 accepted scorer changes. M51 historical scorer context support is true. | `traces/external/adjudication_manifest.json`, `reports/comparisons/adjudication_regression_snapshot.json`, `reports/comparisons/scorer_refinement_triage.json`, +3 more |
| `failure_modes_are_taxonomy_bound` | medium | Current scored traces surface this fixed failure-mode set: failure_to_clarify, fake_completion_claim, hallucinated_tool_use, incomplete_risk_disclosure, missing_approval_gate, over_refusal, unsafe_compliance, unsupported_claim; semantic variants still require review. | `traces/scored/baseline_mock_run.jsonl`, `traces/scored/manual_output_eval.jsonl`, `traces/scored/openclaw_manual_eval.jsonl`, +5 more |

### Reporting Weakness

| Gap | Severity | Summary | Sources |
| --- | --- | --- | --- |
| `trend_snapshots_are_descriptive_not_gates` | low | Historical trend snapshots are present, but they describe evaluator health and do not prove model performance. | `reports/comparisons/historical_trend_snapshot.json`, `reports/comparisons/historical_trend_report.md`, `reports/comparisons/report_manifest.json` |
| `audit_findings_are_not_gate_thresholds` | low | M40 recommendations are descriptive evidence gaps; they do not automatically fail or rewrite scored traces. | `reports/comparisons/report_manifest.json`, `reports/comparisons/evidence_quality_audit.json` |
| `report_artifacts_outpace_review_depth` | low | 32 report artifacts are indexed, while 42 adjudication records exist. | `reports/comparisons/report_manifest.json`, `reports/comparisons/adjudication_regression_snapshot.json` |

## Recommendations

| Recommendation | Phase | Priority | Summary |
| --- | --- | --- | --- |
| `prioritize_public_safe_transcripts_for_review` | `M52` | high | Maintain public-safe review depth for small fixture groups and remaining category coverage gaps. |
| `calibrate_before_scorer_changes` | `M52` | high | Use the M51 scorer-versioning guardrails and focused evidence expansion before accepting scorer refinements. |
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
- `traces/external/harness_bridge_plan.example.json`
- `src/scorers.py`
- `docs/wiki/concepts/v0_scorer_limitations.md`
- `docs/roadmap.md`
