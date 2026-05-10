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
- [External Fixture Comparison](concepts/external_fixture_comparison.md)
- [Adapter Dry-Run Contract Test](concepts/adapter_dry_run_contract_test.md)
- [Provider-Agnostic Adapter Interface](concepts/provider_agnostic_adapter_interface.md)
- [Adapter Interface Conformance Tests](concepts/adapter_interface_conformance_tests.md)

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
- Adapter dry-run contract test: `src/dry_run_adapter.py`
- Adapter interface conformance tests: `tests/test_adapter_output_conformance.py`
- External fixture comparison: `src/compare_external_fixtures.py` and `reports/comparisons/external_fixture_comparison_report.md`
- Adapter contract: `targets/adapters/adapter_contract.md`
- Provider-agnostic adapter interface: `targets/adapters/provider_agnostic_adapter_interface.md`
- Real model adapter design: `targets/adapters/real_model_adapter_design.md`
- Milestone 3 closeout: `docs/milestones/m3-controlled-real-output-prep-closeout.md`
- Milestone 4 closeout: `docs/milestones/m4-adapter-readiness-closeout.md`

## Reading Order

Start with eval case anatomy, then policy-to-eval traceability, then the behavior-specific pages. Read mock vs real evaluations before interpreting baseline results.
