# Evaluator Wiki

This wiki explains the core concepts used by Agent Behavior Evals Lab. It is project-local documentation for the evaluator itself, not a personal knowledge base and not a claim of real model benchmarking.

Milestone 1 is a deterministic mock evaluation harness. The current pipeline loads JSONL cases, generates controlled mock responses for three profiles, scores them with a v0 heuristic scorer, writes scored traces, and generates a Markdown report.

## Concept Pages

- [Eval Case Anatomy](concepts/eval_case_anatomy.md)
- [Policy-To-Eval Traceability](concepts/policy_to_eval_traceability.md)
- [Failure Taxonomy](concepts/failure_taxonomy.md)
- [Approval Gates](concepts/approval_gates.md)
- [Refusal Boundaries](concepts/refusal_boundaries.md)
- [Uncertainty Handling](concepts/uncertainty_handling.md)
- [Mock Vs Real Evaluations](concepts/mock_vs_real_evaluations.md)
- [OpenClaw As A System Under Test](concepts/openclaw_as_system_under_test.md)
- [Saved Transcript Replay](concepts/saved_transcript_replay.md)
- [Normalized Adapter Outputs](concepts/normalized_adapter_outputs.md)
- [Adapter Output Provenance](concepts/adapter_output_provenance.md)
- [Fixture Manifest](concepts/fixture_manifest.md)
- [Fixture Manifest Validation Tests](concepts/fixture_manifest_validation_tests.md)
- [External Fixture Comparison](concepts/external_fixture_comparison.md)
- [Adapter Dry-Run Contract Test](concepts/adapter_dry_run_contract_test.md)
- [Provider-Agnostic Adapter Interface](concepts/provider_agnostic_adapter_interface.md)
- [Adapter Interface Conformance Tests](concepts/adapter_interface_conformance_tests.md)
- [Controlled Adapter Sandbox](concepts/controlled_adapter_sandbox.md)
- [Text-Only Saved Output Workflow](concepts/text_only_saved_output_workflow.md)
- [Promoted Reviewed Outputs](concepts/promoted_reviewed_outputs.md)
- [Human Adjudications](concepts/human_adjudications.md)
- [Adjudication-Aware Reporting](concepts/adjudication_aware_reporting.md)
- [Scored Trace Comparison](concepts/scored_trace_comparison.md)
- [Reporting Regression Snapshots](concepts/reporting_regression_snapshots.md)
- [Reviewed Fixture Quality-Gate Promotion Checklist](concepts/reviewed_fixture_quality_gate_promotion.md)

## Current Source Artifacts

- Policy: `policy/agent_behavior_policy.md`
- Case files: `evals/cases/*.jsonl`
- Failure taxonomy: `evals/failure_taxonomy.md`
- Target profiles and prompts: `targets/profiles/` and `targets/prompts/`
- Mock client: `src/model_clients.py`
- Scorer: `src/scorers.py`
- Trace writer and runner: `src/trace_writer.py` and `src/run_eval.py`
- Report generator: `src/report_generator.py`
- Baseline trace and report: `traces/scored/baseline_mock_run.jsonl` and `reports/baseline_report.md`
- Manual output evaluator: `src/evaluate_manual_outputs.py`
- Saved transcript replay: `src/replay_saved_transcripts.py`
- Normalized adapter-output validator: `src/validate_adapter_outputs.py`
- Adapter-output fixture importer: `src/import_adapter_outputs.py`
- Adapter-output provenance: `docs/wiki/concepts/adapter_output_provenance.md`
- Fixture manifest: `traces/external/fixture_manifest.json` and `src/validate_fixture_manifest.py`
- Fixture manifest validation tests: `tests/test_fixture_manifest_validation.py`
- Adapter dry-run contract test: `src/dry_run_adapter.py`
- Adapter interface conformance tests: `tests/test_adapter_output_conformance.py`
- Controlled adapter sandbox: `targets/adapters/controlled_adapter_sandbox.md`
- Adapter run metadata: `traces/external/adapter_run_metadata.example.json` and `src/validate_adapter_run_metadata.py`
- Target registry: `targets/target_registry.json` and `src/target_registry.py`
- Text-only saved output workflow: `src/collect_text_only_outputs.py` and `src/review_text_only_outputs.py`
- Reviewed output promotion: `src/promote_reviewed_outputs.py`
- Human adjudications: `traces/external/adjudications.example.jsonl`, `traces/external/adjudications.followup.example.jsonl`, and `src/validate_adjudications.py`
- Adjudication fixture manifest: `traces/external/adjudication_manifest.json`
- Adjudication-aware reporting: `src/adjudication_report.py`, `reports/comparisons/adjudication_summary_report.md`, and `reports/comparisons/adjudicated_aggregate_report.md`
- Adjudication regression snapshot: `src/adjudication_regression_check.py` and `reports/comparisons/adjudication_regression_snapshot.json`
- Shared reporting utilities: `src/reporting_utils.py`
- Scored trace comparison: `src/compare_scored_traces.py` and `reports/comparisons/baseline_self_comparison_report.md`
- External fixture comparison: `src/compare_external_fixtures.py` and `reports/comparisons/external_fixture_comparison_report.md`
- Adapter contract: `targets/adapters/adapter_contract.md`
- Provider-agnostic adapter interface: `targets/adapters/provider_agnostic_adapter_interface.md`
- Real model adapter design: `targets/adapters/real_model_adapter_design.md`
- Milestone 3 closeout: `docs/milestones/m3-controlled-real-output-prep-closeout.md`
- Milestone 4 closeout: `docs/milestones/m4-adapter-readiness-closeout.md`
- Milestone 5 closeout: `docs/milestones/m5-adapter-contract-hardening-closeout.md`
- Milestone 6 closeout: `docs/milestones/m6-controlled-adapter-sandbox-closeout.md`
- Milestone 7 closeout: `docs/milestones/m7-text-only-saved-output-collector-closeout.md`
- Milestone 8 closeout: `docs/milestones/m8-reviewed-output-promotion-closeout.md`
- Milestone 9 closeout: `docs/milestones/m9-adjudication-and-trace-comparison-closeout.md`
- Milestone 10 closeout: `docs/milestones/m10-adjudication-aware-reporting-closeout.md`
- Milestone 11 closeout: `docs/milestones/m11-reporting-regression-hardening-closeout.md`
- Milestone 12 closeout: `docs/milestones/m12-reviewed-adjudication-coverage-closeout.md`
- Milestone 13 closeout: `docs/milestones/m13-multiple-adjudication-fixtures-closeout.md`
- Milestone 14 closeout: `docs/milestones/m14-adjudication-fixture-status-governance-closeout.md`
- Milestone 15 closeout: `docs/milestones/m15-status-aware-adjudication-thresholds-closeout.md`

## Reading Order

Start with eval case anatomy, then policy-to-eval traceability, then the behavior-specific pages. Read mock vs real evaluations before interpreting baseline results.
