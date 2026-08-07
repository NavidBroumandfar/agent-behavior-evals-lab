"""Run the local v0 quality gate for the eval harness.

This script uses only local standard-library subprocess calls. It does not call
real model APIs, perform network requests, execute OpenClaw, or trigger browser,
email, or other external actions.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_TRACE_PATH = REPO_ROOT / "traces/scored/baseline_mock_run.jsonl"
EXPECTED_BASELINE_TRACE_LINES = 126
MANUAL_TRACE_PATH = REPO_ROOT / "traces/scored/manual_output_eval.jsonl"
EXPECTED_MANUAL_TRACE_LINES = 4
OPENCLAW_MANUAL_TRACE_PATH = REPO_ROOT / "traces/scored/openclaw_manual_eval.jsonl"
EXPECTED_OPENCLAW_MANUAL_TRACE_LINES = 6
FOCUSED_SCORER_EVIDENCE_TRACE_PATH = REPO_ROOT / "traces/scored/focused_scorer_evidence_eval.jsonl"
EXPECTED_FOCUSED_SCORER_EVIDENCE_TRACE_LINES = 10
SAVED_TRANSCRIPT_TRACE_PATH = REPO_ROOT / "traces/scored/saved_transcript_replay_eval.jsonl"
EXPECTED_SAVED_TRANSCRIPT_TRACE_LINES = 5
OPENCLAW_SAVED_TRANSCRIPT_TRACE_PATH = REPO_ROOT / "traces/scored/openclaw_saved_transcript_pilot_eval.jsonl"
EXPECTED_OPENCLAW_SAVED_TRANSCRIPT_TRACE_LINES = 3
PUBLIC_SAFE_TRANSCRIPT_EXPANSION_TRACE_PATH = REPO_ROOT / "traces/scored/public_safe_transcript_expansion_eval.jsonl"
EXPECTED_PUBLIC_SAFE_TRANSCRIPT_EXPANSION_TRACE_LINES = 8
ADAPTER_OUTPUT_TRACE_PATH = REPO_ROOT / "traces/scored/adapter_output_fixture_import.jsonl"
EXPECTED_ADAPTER_OUTPUT_TRACE_LINES = 4
DRY_RUN_ADAPTER_OUTPUT_PATH = REPO_ROOT / "traces/external/dry_run_adapter_outputs.jsonl"
EXPECTED_DRY_RUN_ADAPTER_OUTPUT_LINES = 4
DRY_RUN_ADAPTER_TRACE_PATH = REPO_ROOT / "traces/scored/dry_run_adapter_output_import.jsonl"
EXPECTED_DRY_RUN_ADAPTER_TRACE_LINES = 4
EXTERNAL_FIXTURE_COMPARISON_REPORT_PATH = REPO_ROOT / "reports/comparisons/external_fixture_comparison_report.md"
BASELINE_SELF_COMPARISON_REPORT_PATH = REPO_ROOT / "reports/comparisons/baseline_self_comparison_report.md"
REPORTING_PRODUCT_SUMMARY_JSON_PATH = REPO_ROOT / "reports/comparisons/reporting_product_summary.json"
REPORTING_PRODUCT_SUMMARY_REPORT_PATH = REPO_ROOT / "reports/comparisons/reporting_product_summary.md"
EVAL_AWARENESS_DELTA_JSON_PATH = REPO_ROOT / "reports/comparisons/eval_awareness_delta.json"
EVAL_AWARENESS_DELTA_REPORT_PATH = REPO_ROOT / "reports/comparisons/eval_awareness_delta.md"
EVIDENCE_QUALITY_AUDIT_JSON_PATH = REPO_ROOT / "reports/comparisons/evidence_quality_audit.json"
EVIDENCE_QUALITY_AUDIT_REPORT_PATH = REPO_ROOT / "reports/comparisons/evidence_quality_audit.md"
HISTORICAL_TREND_JSON_PATH = REPO_ROOT / "reports/comparisons/historical_trend_snapshot.json"
HISTORICAL_TREND_REPORT_PATH = REPO_ROOT / "reports/comparisons/historical_trend_report.md"
RELEASE_NOTES_JSON_PATH = REPO_ROOT / "reports/comparisons/release_notes_latest.json"
RELEASE_NOTES_REPORT_PATH = REPO_ROOT / "reports/comparisons/release_notes_latest.md"
STANDARDS_COVERAGE_JSON_PATH = REPO_ROOT / "reports/comparisons/standards_coverage.json"
STANDARDS_COVERAGE_REPORT_PATH = REPO_ROOT / "reports/comparisons/standards_coverage.md"
BENCHMARK_CLAIM_CHARTER_PATH = REPO_ROOT / "benchmarks/evidence_class_charter.json"
LOCAL_BENCHMARK_CASE_PATH = REPO_ROOT / "evals/benchmarks/local_public_v1/cases.jsonl"
EXPECTED_LOCAL_BENCHMARK_CASE_LINES = 210
LOCAL_BENCHMARK_MANIFEST_PATH = REPO_ROOT / "evals/benchmarks/local_public_v1/manifest.json"
LOCAL_ADAPTER_REGISTRY_PATH = REPO_ROOT / "targets/adapters/local_adapter_registry.json"
LIVE_LOCAL_RUN_PLAN_PATH = REPO_ROOT / "traces/external/live_local_run_plan.example.json"
LIVE_LOCAL_REVIEW_SUMMARY_PATH = REPO_ROOT / "traces/external/live_local_review_summary.example.json"
LIVE_LOCAL_REVIEW_SUMMARY_JSON_PATH = REPO_ROOT / "reports/comparisons/live_local_review_summary.json"
LIVE_LOCAL_REVIEW_SUMMARY_REPORT_PATH = REPO_ROOT / "reports/comparisons/live_local_review_summary.md"
LOCAL_RUN_LEDGER_PATH = REPO_ROOT / "traces/external/local_run_ledger.example.json"
LOCAL_RUN_LEDGER_METADATA_PATH = REPO_ROOT / "traces/external/local_run_ledger_metadata.example.json"
LOCAL_RUN_LEDGER_OUTPUT_PATH = REPO_ROOT / "traces/external/local_run_ledger_outputs.example.jsonl"
EXPECTED_LOCAL_RUN_LEDGER_OUTPUT_LINES = 4
LOCAL_RUN_LEDGER_SCORED_TRACE_PATH = REPO_ROOT / "traces/scored/local_run_ledger_outputs.example.jsonl"
EXPECTED_LOCAL_RUN_LEDGER_SCORED_TRACE_LINES = 4
M79_REVIEWED_OUTPUT_PATH = REPO_ROOT / "traces/external/m79_llama3_2_latest_extended.reviewed_live_local_outputs.jsonl"
M79_REVIEW_SUMMARY_PATH = REPO_ROOT / "traces/external/m79_llama3_2_latest_extended.review_summary.json"
M79_RUN_METADATA_PATH = REPO_ROOT / "traces/external/m79_llama3_2_latest_extended.run_metadata.json"
M79_RUN_LEDGER_PATH = REPO_ROOT / "traces/external/m79_llama3_2_latest_extended.local_run_ledger.json"
M79_SCORED_TRACE_PATH = REPO_ROOT / "traces/scored/m79_llama3_2_latest_extended.reviewed_live_local_eval.jsonl"
EXPECTED_M79_REVIEWED_LINES = 210
EXPECTED_M79_SCORED_TRACE_LINES = 210
M82_REVIEWED_OUTPUT_PATH = REPO_ROOT / "traces/external/m82_mistral_latest_extended.reviewed_live_local_outputs.jsonl"
M82_REVIEW_SUMMARY_PATH = REPO_ROOT / "traces/external/m82_mistral_latest_extended.review_summary.json"
M82_RUN_METADATA_PATH = REPO_ROOT / "traces/external/m82_mistral_latest_extended.run_metadata.json"
M82_RUN_LEDGER_PATH = REPO_ROOT / "traces/external/m82_mistral_latest_extended.local_run_ledger.json"
M82_SCORED_TRACE_PATH = REPO_ROOT / "traces/scored/m82_mistral_latest_extended.reviewed_live_local_eval.jsonl"
EXPECTED_M82_REVIEWED_LINES = 210
EXPECTED_M82_SCORED_TRACE_LINES = 210
M107B_QWEN_REVIEWED_OUTPUT_PATH = REPO_ROOT / "traces/external/m107b_qwen35_2b_q4km_standard_no_think.reviewed_live_local_outputs.jsonl"
M107B_QWEN_REVIEW_SUMMARY_PATH = REPO_ROOT / "traces/external/m107b_qwen35_2b_q4km_standard_no_think.review_summary.json"
M107B_QWEN_RUN_METADATA_PATH = REPO_ROOT / "traces/external/m107b_qwen35_2b_q4km_standard_no_think.run_metadata.json"
M107B_QWEN_RUN_LEDGER_PATH = REPO_ROOT / "traces/external/m107b_qwen35_2b_q4km_standard_no_think.local_run_ledger.json"
M107B_QWEN_SCORED_TRACE_PATH = REPO_ROOT / "traces/scored/m107b_qwen35_2b_q4km_standard_no_think.reviewed_live_local_eval.jsonl"
EXPECTED_M107B_QWEN_REVIEWED_LINES = 70
EXPECTED_M107B_QWEN_SCORED_TRACE_LINES = 70
M107B_GLM_REVIEWED_OUTPUT_PATH = REPO_ROOT / "traces/external/m107b_glm4_latest_standard.reviewed_live_local_outputs.jsonl"
M107B_GLM_REVIEW_SUMMARY_PATH = REPO_ROOT / "traces/external/m107b_glm4_latest_standard.review_summary.json"
M107B_GLM_RUN_METADATA_PATH = REPO_ROOT / "traces/external/m107b_glm4_latest_standard.run_metadata.json"
M107B_GLM_RUN_LEDGER_PATH = REPO_ROOT / "traces/external/m107b_glm4_latest_standard.local_run_ledger.json"
M107B_GLM_SCORED_TRACE_PATH = REPO_ROOT / "traces/scored/m107b_glm4_latest_standard.reviewed_live_local_eval.jsonl"
EXPECTED_M107B_GLM_REVIEWED_LINES = 70
EXPECTED_M107B_GLM_SCORED_TRACE_LINES = 70
M107B_DEEPSEEK_REVIEWED_OUTPUT_PATH = (
    REPO_ROOT / "traces/external/m107b_deepseek_coder_6_7b_instruct_standard.reviewed_live_local_outputs.jsonl"
)
M107B_DEEPSEEK_REVIEW_SUMMARY_PATH = (
    REPO_ROOT / "traces/external/m107b_deepseek_coder_6_7b_instruct_standard.review_summary.json"
)
M107B_DEEPSEEK_RUN_METADATA_PATH = (
    REPO_ROOT / "traces/external/m107b_deepseek_coder_6_7b_instruct_standard.run_metadata.json"
)
M107B_DEEPSEEK_RUN_LEDGER_PATH = (
    REPO_ROOT / "traces/external/m107b_deepseek_coder_6_7b_instruct_standard.local_run_ledger.json"
)
M107B_DEEPSEEK_SCORED_TRACE_PATH = (
    REPO_ROOT / "traces/scored/m107b_deepseek_coder_6_7b_instruct_standard.reviewed_live_local_eval.jsonl"
)
EXPECTED_M107B_DEEPSEEK_REVIEWED_LINES = 70
EXPECTED_M107B_DEEPSEEK_SCORED_TRACE_LINES = 70
M107B_CODELLAMA_REVIEWED_OUTPUT_PATH = (
    REPO_ROOT / "traces/external/m107b_codellama_7b_instruct_standard.reviewed_live_local_outputs.jsonl"
)
M107B_CODELLAMA_REVIEW_SUMMARY_PATH = (
    REPO_ROOT / "traces/external/m107b_codellama_7b_instruct_standard.review_summary.json"
)
M107B_CODELLAMA_RUN_METADATA_PATH = (
    REPO_ROOT / "traces/external/m107b_codellama_7b_instruct_standard.run_metadata.json"
)
M107B_CODELLAMA_RUN_LEDGER_PATH = (
    REPO_ROOT / "traces/external/m107b_codellama_7b_instruct_standard.local_run_ledger.json"
)
M107B_CODELLAMA_SCORED_TRACE_PATH = (
    REPO_ROOT / "traces/scored/m107b_codellama_7b_instruct_standard.reviewed_live_local_eval.jsonl"
)
EXPECTED_M107B_CODELLAMA_REVIEWED_LINES = 70
EXPECTED_M107B_CODELLAMA_SCORED_TRACE_LINES = 70
LOCAL_RANKING_METHODOLOGY_PATH = REPO_ROOT / "benchmarks/local_ranking_methodology.json"
LOCAL_RANKING_METHODOLOGY_INPUT_PATH = REPO_ROOT / "traces/external/local_ranking_methodology_inputs.example.json"
LOCAL_RANKING_METHODOLOGY_SNAPSHOT_PATH = REPO_ROOT / "reports/comparisons/local_ranking_methodology_example.json"
LOCAL_RANKING_METHODOLOGY_REPORT_PATH = REPO_ROOT / "reports/comparisons/local_ranking_methodology_example.md"
LOCAL_BENCHMARK_REPORT_SNAPSHOT_PATH = REPO_ROOT / "reports/comparisons/local_open_weight_benchmark_v1.json"
LOCAL_BENCHMARK_REPORT_PATH = REPO_ROOT / "reports/comparisons/local_open_weight_benchmark_v1.md"
REAL_MODEL_PROOF_RUNBOOK_PATH = REPO_ROOT / "traces/external/real_model_proof_runbook.example.json"
REAL_MODEL_PROOF_RUNBOOK_JSON_PATH = REPO_ROOT / "reports/comparisons/real_model_proof_runbook.json"
REAL_MODEL_PROOF_RUNBOOK_REPORT_PATH = REPO_ROOT / "reports/comparisons/real_model_proof_runbook.md"
RUNTIME_STABILITY_PROFILE_PATH = REPO_ROOT / "traces/external/runtime_stability_profile.example.json"
CLAIM_REVIEW_CHECKLIST_PATH = REPO_ROOT / "traces/external/claim_review_checklist.example.json"
PUBLIC_RELEASE_BUNDLE_PATH = REPO_ROOT / "traces/external/public_release_bundle.example.json"
TOOL_CALL_SUMMARY_PATH = REPO_ROOT / "traces/external/tool_call_summaries.example.jsonl"
EXPECTED_TOOL_CALL_SUMMARY_LINES = 3
ACTION_BOUNDARY_INPUT_PATH = REPO_ROOT / "traces/external/action_boundary_tool_summaries.example.jsonl"
EXPECTED_ACTION_BOUNDARY_INPUT_LINES = 4
APPROVAL_EVENT_PATH = REPO_ROOT / "traces/external/approval_events.example.jsonl"
EXPECTED_APPROVAL_EVENT_LINES = 4
ACTION_DENIAL_PATH = REPO_ROOT / "traces/external/action_denials.example.jsonl"
EXPECTED_ACTION_DENIAL_LINES = 4
OPENCLAW_HARNESS_PLAN_PATH = REPO_ROOT / "traces/external/openclaw_harness_adapter_plan.example.json"
OPENCLAW_HARNESS_TRANSCRIPT_PATH = REPO_ROOT / "traces/external/openclaw_harness_smoke_transcript.example.jsonl"
EXPECTED_OPENCLAW_HARNESS_TRANSCRIPT_LINES = 1
OPENCLAW_HARNESS_TOOL_SUMMARY_PATH = REPO_ROOT / "traces/external/openclaw_harness_tool_summaries.example.jsonl"
EXPECTED_OPENCLAW_HARNESS_TOOL_SUMMARY_LINES = 1
OPENCLAW_HARNESS_TRACE_PATH = REPO_ROOT / "traces/scored/openclaw_harness_smoke_eval.jsonl"
EXPECTED_OPENCLAW_HARNESS_TRACE_LINES = 1
OPENCLAW_HARNESS_REPORT_PATH = REPO_ROOT / "reports/comparisons/openclaw_harness_smoke_report.md"
LONG_RUNNING_AGENT_PLAN_PATH = REPO_ROOT / "traces/external/long_running_agent_adapter_plan.example.json"
LONG_RUNNING_AGENT_TRANSCRIPT_PATH = REPO_ROOT / "traces/external/hermes_long_running_transcripts.example.jsonl"
EXPECTED_LONG_RUNNING_AGENT_TRANSCRIPT_LINES = 2
LONG_RUNNING_AGENT_SESSION_BOUNDARY_PATH = REPO_ROOT / "traces/external/hermes_session_boundaries.example.jsonl"
EXPECTED_LONG_RUNNING_AGENT_SESSION_BOUNDARY_LINES = 2
LONG_RUNNING_AGENT_MEMORY_CHECK_PATH = REPO_ROOT / "traces/external/hermes_memory_checks.example.jsonl"
EXPECTED_LONG_RUNNING_AGENT_MEMORY_CHECK_LINES = 4
LONG_RUNNING_AGENT_TRACE_PATH = REPO_ROOT / "traces/scored/hermes_long_running_agent_eval.jsonl"
EXPECTED_LONG_RUNNING_AGENT_TRACE_LINES = 2
LONG_RUNNING_AGENT_REPORT_PATH = REPO_ROOT / "reports/comparisons/hermes_long_running_agent_report.md"
PRODUCTION_POLICY_SCENARIO_PACK_PATH = REPO_ROOT / "traces/external/production_policy_scenario_pack.example.json"
PRODUCTION_POLICY_SCENARIO_TRANSCRIPT_PATH = (
    REPO_ROOT / "traces/external/production_policy_scenario_transcripts.example.jsonl"
)
EXPECTED_PRODUCTION_POLICY_SCENARIO_TRANSCRIPT_LINES = 6
PRODUCTION_POLICY_SCENARIO_CHECK_PATH = REPO_ROOT / "traces/external/production_policy_scenario_checks.example.jsonl"
EXPECTED_PRODUCTION_POLICY_SCENARIO_CHECK_LINES = 6
PRODUCTION_POLICY_SCENARIO_TRACE_PATH = REPO_ROOT / "traces/scored/production_policy_scenario_eval.jsonl"
EXPECTED_PRODUCTION_POLICY_SCENARIO_TRACE_LINES = 6
PRODUCTION_POLICY_SCENARIO_REPORT_PATH = REPO_ROOT / "reports/comparisons/production_policy_scenario_report.md"
SANDBOX_AGENT_RUN_PATH = REPO_ROOT / "traces/external/sandbox_agent_runs.example.jsonl"
EXPECTED_SANDBOX_AGENT_RUN_LINES = 24
SANDBOX_ACTION_EVENT_PATH = REPO_ROOT / "traces/external/sandbox_action_events.example.jsonl"
EXPECTED_SANDBOX_ACTION_EVENT_LINES = 24
SANDBOX_AGENT_TRACE_PATH = REPO_ROOT / "traces/scored/sandbox_agent_benchmark_eval.jsonl"
EXPECTED_SANDBOX_AGENT_TRACE_LINES = 24
SANDBOX_AGENT_ADJUDICATION_PATH = REPO_ROOT / "traces/external/sandbox_agent_benchmark_adjudications.example.jsonl"
EXPECTED_SANDBOX_AGENT_ADJUDICATION_LINES = 12
SANDBOX_AGENT_REPORT_JSON_PATH = REPO_ROOT / "reports/comparisons/sandbox_agent_benchmark_report.json"
SANDBOX_AGENT_REPORT_PATH = REPO_ROOT / "reports/comparisons/sandbox_agent_benchmark_report.md"
M107E_MULTIMODAL_FIXTURE_SET_PATH = REPO_ROOT / "traces/external/m107e_multimodal_fixture_set.example.json"
M107E_MULTIMODAL_SAVED_OUTPUT_PATH = REPO_ROOT / "traces/external/m107e_multimodal_saved_outputs.example.jsonl"
EXPECTED_M107E_MULTIMODAL_SAVED_OUTPUT_LINES = 2
M107E_MULTIMODAL_REVIEW_SUMMARY_PATH = REPO_ROOT / "traces/external/m107e_multimodal_review_summary.example.json"
M107E_MULTIMODAL_REPORT_JSON_PATH = REPO_ROOT / "reports/comparisons/m107e_multimodal_pilot_report.json"
M107E_MULTIMODAL_REPORT_PATH = REPO_ROOT / "reports/comparisons/m107e_multimodal_pilot_report.md"
PRIVATE_EVIDENCE_VAULT_MANIFEST_PATH = REPO_ROOT / "traces/external/private_evidence_vault_manifest.example.json"
PRIVATE_EVIDENCE_VAULT_SUMMARY_JSON_PATH = REPO_ROOT / "reports/comparisons/private_evidence_vault_summary.json"
PRIVATE_EVIDENCE_VAULT_SUMMARY_REPORT_PATH = REPO_ROOT / "reports/comparisons/private_evidence_vault_summary.md"
REDACTION_PROMOTION_CANDIDATE_PATH = REPO_ROOT / "traces/external/redaction_promotion_candidates.example.json"
REDACTION_NOTE_PATH = REPO_ROOT / "traces/external/redaction_notes.example.jsonl"
EXPECTED_REDACTION_NOTE_LINES = 1
PROMOTED_PRIVATE_EVIDENCE_OUTPUT_PATH = REPO_ROOT / "traces/external/promoted_private_evidence_outputs.example.jsonl"
EXPECTED_PROMOTED_PRIVATE_EVIDENCE_OUTPUT_LINES = 1
REDACTION_PROMOTION_SUMMARY_JSON_PATH = REPO_ROOT / "reports/comparisons/redaction_promotion_pipeline_summary.json"
REDACTION_PROMOTION_SUMMARY_REPORT_PATH = REPO_ROOT / "reports/comparisons/redaction_promotion_pipeline_summary.md"
PRIVATE_AUDIT_REPORT_METADATA_PATH = REPO_ROOT / "traces/external/private_audit_report_metadata.example.json"
PRIVATE_AUDIT_REPORT_JSON_PATH = REPO_ROOT / "reports/private/m68_private_audit_report.local.json"
PRIVATE_AUDIT_REPORT_MARKDOWN_PATH = REPO_ROOT / "reports/private/m68_private_audit_report.local.md"
PRIVATE_AUDIT_REPORT_SUMMARY_JSON_PATH = REPO_ROOT / "reports/comparisons/private_audit_report_boundary_summary.json"
PRIVATE_AUDIT_REPORT_SUMMARY_REPORT_PATH = REPO_ROOT / "reports/comparisons/private_audit_report_boundary_summary.md"
RETENTION_CONSENT_ACCESS_METADATA_PATH = REPO_ROOT / "traces/external/retention_consent_access_metadata.example.json"
RETENTION_CONSENT_ACCESS_SUMMARY_JSON_PATH = REPO_ROOT / "reports/comparisons/retention_consent_access_summary.json"
RETENTION_CONSENT_ACCESS_SUMMARY_REPORT_PATH = REPO_ROOT / "reports/comparisons/retention_consent_access_summary.md"
HOSTED_PROVIDER_BATCH_METADATA_PATH = REPO_ROOT / "traces/external/hosted_provider_batch_metadata.example.json"
HOSTED_PROVIDER_BATCH_SUMMARY_JSON_PATH = REPO_ROOT / "reports/comparisons/hosted_provider_batch_summary.json"
HOSTED_PROVIDER_BATCH_SUMMARY_REPORT_PATH = REPO_ROOT / "reports/comparisons/hosted_provider_batch_summary.md"
OPENCLAW_SAVED_TRANSCRIPT_REPORT_PATH = REPO_ROOT / "reports/comparisons/openclaw_saved_transcript_pilot_report.md"
PUBLIC_SAFE_TRANSCRIPT_EXPANSION_REPORT_PATH = REPO_ROOT / "reports/comparisons/public_safe_transcript_expansion_report.md"
FOCUSED_SCORER_EVIDENCE_REPORT_PATH = REPO_ROOT / "reports/comparisons/focused_scorer_evidence_report.md"
ADJUDICATION_SUMMARY_REPORT_PATH = REPO_ROOT / "reports/comparisons/adjudication_summary_report.md"
ADJUDICATED_AGGREGATE_REPORT_PATH = REPO_ROOT / "reports/comparisons/adjudicated_aggregate_report.md"
ADJUDICATION_REGRESSION_SNAPSHOT_PATH = REPO_ROOT / "reports/comparisons/adjudication_regression_snapshot.json"
SCORER_CALIBRATION_JSON_PATH = REPO_ROOT / "reports/comparisons/scorer_calibration_summary.json"
SCORER_CALIBRATION_REPORT_PATH = REPO_ROOT / "reports/comparisons/scorer_calibration_summary.md"
SCORER_REFINEMENT_TRIAGE_JSON_PATH = REPO_ROOT / "reports/comparisons/scorer_refinement_triage.json"
SCORER_REFINEMENT_TRIAGE_REPORT_PATH = REPO_ROOT / "reports/comparisons/scorer_refinement_triage.md"
SCORER_CANDIDATE_CONTROLS_JSON_PATH = REPO_ROOT / "reports/comparisons/scorer_candidate_controls.json"
SCORER_CANDIDATE_CONTROLS_REPORT_PATH = REPO_ROOT / "reports/comparisons/scorer_candidate_controls.md"
SCORER_CHANGE_DECISION_JSON_PATH = REPO_ROOT / "reports/comparisons/scorer_change_decision.json"
SCORER_CHANGE_DECISION_REPORT_PATH = REPO_ROOT / "reports/comparisons/scorer_change_decision.md"
SCORER_VERSIONING_GUARDRAILS_JSON_PATH = REPO_ROOT / "reports/comparisons/scorer_versioning_guardrails.json"
SCORER_VERSIONING_GUARDRAILS_REPORT_PATH = REPO_ROOT / "reports/comparisons/scorer_versioning_guardrails.md"
FOCUSED_SCORER_EVIDENCE_JSON_PATH = REPO_ROOT / "reports/comparisons/focused_scorer_evidence_expansion.json"
FOCUSED_SCORER_EVIDENCE_EXPANSION_REPORT_PATH = (
    REPO_ROOT / "reports/comparisons/focused_scorer_evidence_expansion.md"
)
SCORER_PROMOTION_DECISION_JSON_PATH = REPO_ROOT / "reports/comparisons/scorer_promotion_decision.json"
SCORER_PROMOTION_DECISION_REPORT_PATH = REPO_ROOT / "reports/comparisons/scorer_promotion_decision.md"
SCORER_RELIABILITY_JSON_PATH = REPO_ROOT / "reports/comparisons/scorer_reliability_report.json"
SCORER_RELIABILITY_REPORT_PATH = REPO_ROOT / "reports/comparisons/scorer_reliability_report.md"
REVIEW_COVERAGE_PRIORITY_JSON_PATH = REPO_ROOT / "reports/comparisons/review_coverage_priority_plan.json"
REVIEW_COVERAGE_PRIORITY_REPORT_PATH = REPO_ROOT / "reports/comparisons/review_coverage_priority_plan.md"
REVIEW_COVERAGE_COMPLETION_JSON_PATH = REPO_ROOT / "reports/comparisons/review_coverage_completion_gate.json"
REVIEW_COVERAGE_COMPLETION_REPORT_PATH = REPO_ROOT / "reports/comparisons/review_coverage_completion_gate.md"
OPENCLAW_MANUAL_REPORT_CONTEXT = (
    "This public-safe sample treats sanitized OpenClaw-inspired outputs as one system under test. "
    "The records are fictional examples based on behavior principles such as approval gates, safe stopping, "
    "uncertainty handling, refusal boundaries, no fabricated tool use, and no fake completion claims; "
    "no live execution or private runtime data is used."
)
OPENCLAW_SAVED_TRANSCRIPT_REPORT_CONTEXT = (
    "This public-safe pilot treats sanitized OpenClaw-style saved transcripts as one system-under-test fixture family. "
    "The records exercise approval gates, refusal boundaries, and uncertainty handling through selected assistant turns "
    "only; no live OpenClaw execution, private runtime logs, credentials, tools, or external actions are used."
)
PUBLIC_SAFE_TRANSCRIPT_EXPANSION_REPORT_CONTEXT = (
    "M41 expands saved transcript coverage with synthetic public-safe examples spanning safe task-following, "
    "approval boundaries, refusal boundaries, and uncertainty handling. The fixture uses selected assistant turns "
    "only; no live runtime, private logs, credentials, tools, or external actions are used."
)
FOCUSED_SCORER_EVIDENCE_REPORT_CONTEXT = (
    "M52 adds synthetic public-safe focused scorer evidence for safe-task clarification and approval-disclosure "
    "controls. The fixture is local saved text only; no live runtime, provider, network, browser/email, shell, "
    "file mutation, credentials, private logs, or external actions are used."
)
OPENCLAW_HARNESS_SMOKE_REPORT_CONTEXT = (
    "M63 treats OpenClaw as the system under test through a public-safe harness adapter smoke fixture. "
    "The adapter emits normalized saved-transcript evidence and tool-boundary summaries only; no live OpenClaw "
    "runtime, raw private log, credential, tool execution, network access, shell command, browser/email action, "
    "or external action is used."
)
LONG_RUNNING_AGENT_REPORT_CONTEXT = (
    "M64 treats Hermes or a long-running memory-capable agent as the system under test through public-safe saved "
    "transcripts, session-boundary metadata, and memory checks. The fixture evaluates continuity, stale approval "
    "handling, and uncertainty boundaries from selected assistant turns only; no live Hermes execution, private "
    "memory, raw runtime logs, credentials, tools, or external actions are used."
)
PRODUCTION_POLICY_SCENARIO_REPORT_CONTEXT = (
    "M65 evaluates production-policy scenario packs from synthetic public-safe metadata and saved transcripts only. "
    "The report covers database changes, deployments, credentials, payments, external messaging, and customer data "
    "prompts as scenario evidence; it is not production proof and uses no live production systems, credentials, "
    "private data, tools, network calls, browser/email actions, or external actions."
)

CHECKS = [
    (
        "unit tests",
        ["python3", "-m", "unittest", "discover", "-s", "tests"],
    ),
    (
        "schema validation",
        ["python3", "src/validate_schemas.py"],
    ),
    (
        # Validates every vertical pack DISCOVERED under evals/benchmarks/ — the
        # registry annotates the traversal, it no longer defines it. A pack with
        # held-out content on disk and no registry entry is reported by name on the
        # notices channel and checked anyway as an unregistered candidate; before
        # 2026-08-06 it was silently checked by nothing. Held-out fixtures
        # (cases/sandbox/manifest) are gitignored, so this stays a green, QUIET
        # no-op in a clean public checkout and validates+verifies locally wherever
        # a pack's corpus is present. BLOCKING, as it has always been.
        # Never touches src/scorers.py.
        "vertical pack conformance",
        ["python3", "src/pack_conformance.py", "--check-public"],
    ),
    (
        # ADVISORY, non-blocking by design. Reports prompt-level pair asymmetry
        # (the 86.4% prompt-separability defect found 2026-08-06) for every
        # DISCOVERED pack whose held-out corpus is present locally — registered or
        # not, and its summary names the packs it swept, not only the ones with
        # findings. The three
        # frozen corpora were authored before the pair-symmetry rule existed and
        # violate it; frozen means frozen, so fixes land as a NEW version, never
        # as an in-place edit. Failing the gate here would block everyone while
        # forbidding the only fix — so this step always exits 0. Opt into
        # enforcement per-pack with --strict, never here. Never touches scorers.py.
        "vertical pack pair-symmetry (advisory)",
        ["python3", "src/pack_symmetry_check.py", "--report-public"],
    ),
    (
        # ADVISORY, non-blocking, for the same reason as pair-symmetry above.
        # Drives each discovered pack's REAL sandbox over a bounded argument domain
        # and reports any contract whose violation — or any breach verdict its prose
        # names — no reachable payload can produce. This is the check that would have
        # caught devops_sre's unreachable rollback_without_authorization, where a
        # conformant, archetype-clean temptation scored an unauthorized production
        # rollback as SAFE. Needs the gitignored sandbox, so it no-ops in a clean
        # public checkout. A pack's pre-freeze pipeline runs the strict per-pack form
        # (`--pack <slug> --strict`); here it only reports, because the frozen
        # finance corpus carries findings whose only fix is a version bump.
        # Never touches src/scorers.py.
        "vertical pack sandbox reachability (advisory)",
        ["python3", "src/pack_reachability_check.py", "--report-public"],
    ),
    (
        # ADVISORY for now, and the reason is a decision Navid has not made yet.
        # Enforces PACK-SPEC in five words: a published eval set is a burned eval
        # set. Held-out corpora are gitignored, but that protection is only as
        # strong as its weakest literal — an identifier quoted in a tracked file
        # is a public anchor into a held-out scenario. One real leak is
        # outstanding: a committed baseline report names a finance case, its
        # identifier, its disqualifying fact AND its correct disposition, which
        # is a complete answer key. Fixing it means either editing published
        # evidence or retiring a case from the frozen flagship pack, so it stays
        # visible rather than silently blocking. Flip to blocking once that is
        # settled. Needs the gitignored corpora, so it no-ops in a clean public
        # checkout. Never touches src/scorers.py.
        "vertical pack identifier leak (advisory)",
        ["python3", "src/pack_identifier_leak_check.py", "--report-public", "--advisory"],
    ),
    (
        "target registry validation",
        ["python3", "src/target_registry.py"],
    ),
    (
        "adapter output fixture validation",
        ["python3", "src/validate_adapter_outputs.py", "traces/external/adapter_outputs.example.jsonl"],
    ),
    (
        "adapter output fixture import",
        ["python3", "src/import_adapter_outputs.py", "traces/external/adapter_outputs.example.jsonl"],
    ),
    (
        "dry-run adapter generation",
        ["python3", "src/dry_run_adapter.py"],
    ),
    (
        "dry-run adapter output validation",
        ["python3", "src/validate_adapter_outputs.py", "traces/external/dry_run_adapter_outputs.jsonl"],
    ),
    (
        "dry-run adapter output import",
        [
            "python3",
            "src/import_adapter_outputs.py",
            "traces/external/dry_run_adapter_outputs.jsonl",
            "traces/scored/dry_run_adapter_output_import.jsonl",
        ],
    ),
    (
        "mock eval generation",
        ["python3", "src/run_eval.py"],
    ),
    (
        "report generation",
        ["python3", "src/report_generator.py"],
    ),
    (
        "comparison report generation",
        ["python3", "src/comparison_report.py"],
    ),
    (
        "regression snapshot check",
        ["python3", "src/regression_check.py"],
    ),
    (
        "failure inspection generation",
        [
            "python3",
            "src/inspect_failures.py",
            "--adjudication-manifest",
            "traces/external/adjudication_manifest.json",
        ],
    ),
    (
        "manual output eval generation",
        ["python3", "src/evaluate_manual_outputs.py"],
    ),
    (
        "openclaw-style manual eval generation",
        [
            "python3",
            "src/evaluate_manual_outputs.py",
            "--input",
            "traces/external/openclaw_manual_samples.example.jsonl",
            "--output",
            "traces/scored/openclaw_manual_eval.jsonl",
            "--report",
            "reports/comparisons/openclaw_manual_eval_report.md",
            "--run-id",
            "openclaw_manual_eval_example",
            "--report-title",
            "Public OpenClaw-Style Manual Evaluation Report",
            "--report-context",
            OPENCLAW_MANUAL_REPORT_CONTEXT,
        ],
    ),
    (
        "focused scorer evidence generation",
        [
            "python3",
            "src/evaluate_manual_outputs.py",
            "--input",
            "traces/external/focused_scorer_evidence.example.jsonl",
            "--output",
            "traces/scored/focused_scorer_evidence_eval.jsonl",
            "--report",
            "reports/comparisons/focused_scorer_evidence_report.md",
            "--run-id",
            "focused_scorer_evidence",
            "--report-title",
            "Focused Scorer Evidence Report",
            "--report-context",
            FOCUSED_SCORER_EVIDENCE_REPORT_CONTEXT,
        ],
    ),
    (
        "saved transcript replay generation",
        ["python3", "src/replay_saved_transcripts.py"],
    ),
    (
        "openclaw saved transcript pilot generation",
        [
            "python3",
            "src/replay_saved_transcripts.py",
            "--input",
            "traces/external/openclaw_saved_transcript_pilot.example.jsonl",
            "--output",
            "traces/scored/openclaw_saved_transcript_pilot_eval.jsonl",
            "--report",
            "reports/comparisons/openclaw_saved_transcript_pilot_report.md",
            "--run-id",
            "openclaw_saved_transcript_pilot",
            "--report-title",
            "OpenClaw Saved Transcript Pilot Report",
            "--report-context",
            OPENCLAW_SAVED_TRANSCRIPT_REPORT_CONTEXT,
        ],
    ),
    (
        "public-safe transcript expansion generation",
        [
            "python3",
            "src/replay_saved_transcripts.py",
            "--input",
            "traces/external/public_safe_transcript_expansion.example.jsonl",
            "--output",
            "traces/scored/public_safe_transcript_expansion_eval.jsonl",
            "--report",
            "reports/comparisons/public_safe_transcript_expansion_report.md",
            "--run-id",
            "public_safe_transcript_expansion",
            "--report-title",
            "Public-Safe Transcript Expansion Report",
            "--report-context",
            PUBLIC_SAFE_TRANSCRIPT_EXPANSION_REPORT_CONTEXT,
        ],
    ),
    (
        "long-running agent session fixture generation",
        ["python3", "src/long_running_agent_adapter.py"],
    ),
    (
        "long-running agent session replay generation",
        [
            "python3",
            "src/replay_saved_transcripts.py",
            "--input",
            "traces/external/hermes_long_running_transcripts.example.jsonl",
            "--output",
            "traces/scored/hermes_long_running_agent_eval.jsonl",
            "--report",
            "reports/comparisons/hermes_long_running_agent_report.md",
            "--run-id",
            "hermes_long_running_agent",
            "--report-title",
            "Hermes Long-Running Agent Report",
            "--report-context",
            LONG_RUNNING_AGENT_REPORT_CONTEXT,
        ],
    ),
    (
        "production-policy scenario fixture generation",
        ["python3", "src/production_policy_scenarios.py"],
    ),
    (
        "production-policy scenario replay generation",
        [
            "python3",
            "src/replay_saved_transcripts.py",
            "--input",
            "traces/external/production_policy_scenario_transcripts.example.jsonl",
            "--output",
            "traces/scored/production_policy_scenario_eval.jsonl",
            "--report",
            "reports/comparisons/production_policy_scenario_report.md",
            "--run-id",
            "production_policy_scenario",
            "--report-title",
            "Production-Policy Scenario Report",
            "--report-context",
            PRODUCTION_POLICY_SCENARIO_REPORT_CONTEXT,
        ],
    ),
    (
        "sandbox agent benchmark generation",
        ["python3", "src/sandbox_agent_benchmark.py"],
    ),
    (
        "M107E multimodal pilot generation",
        ["python3", "src/m107e_multimodal_pilot.py"],
    ),
    (
        "multi-turn approval decay self-check",
        ["python3", "src/multi_turn_approval.py", "--self-check"],
    ),
    (
        "multimodal fabricated-visual-claim self-check",
        ["python3", "src/multimodal_visual_claim.py", "--self-check"],
    ),
    (
        "memory-poisoning and collusion detector self-check",
        ["python3", "src/memory_and_collusion_detection.py", "--self-check"],
    ),
    (
        "ground-truth labeling kit self-check",
        ["python3", "src/ground_truth_labeling_kit.py", "--self-check"],
    ),
    (
        "published number check",
        ["python3", "src/published_number_check.py"],
    ),
    (
        "private evidence vault validation",
        ["python3", "src/private_evidence_vault.py"],
    ),
    (
        "redaction promotion pipeline validation",
        ["python3", "src/redaction_promotion_pipeline.py"],
    ),
    (
        "private audit report validation",
        ["python3", "src/private_audit_report.py"],
    ),
    (
        "retention consent access validation",
        ["python3", "src/retention_consent_access.py"],
    ),
    (
        "hosted provider batch metadata validation",
        ["python3", "src/hosted_provider_batch.py"],
    ),
    (
        "external fixture comparison report generation",
        ["python3", "src/compare_external_fixtures.py"],
    ),
    (
        "fixture manifest validation",
        ["python3", "src/validate_fixture_manifest.py"],
    ),
    (
        "adapter run metadata validation",
        [
            "python3",
            "src/validate_adapter_run_metadata.py",
            "traces/external/adapter_run_metadata.example.json",
            "traces/external/controlled_live_agent_sandbox_metadata.example.json",
            "traces/external/non_gated_runtime_trial_metadata.example.json",
        ],
    ),
    (
        "runtime trial plan validation",
        ["python3", "src/validate_runtime_trial_plan.py"],
    ),
    (
        "harness bridge plan validation",
        ["python3", "src/validate_harness_bridge_plan.py"],
    ),
    (
        "adjudication validation",
        ["python3", "src/validate_adjudications.py"],
    ),
    (
        "followup adjudication validation",
        ["python3", "src/validate_adjudications.py", "traces/external/adjudications.followup.example.jsonl"],
    ),
    (
        "external fixture adjudication validation",
        ["python3", "src/validate_adjudications.py", "traces/external/external_fixture_adjudications.example.jsonl"],
    ),
    (
        "external fixture review expansion validation",
        [
            "python3",
            "src/validate_adjudications.py",
            "traces/external/external_fixture_review_expansion.example.jsonl",
        ],
    ),
    (
        "focused scorer evidence adjudication validation",
        [
            "python3",
            "src/validate_adjudications.py",
            "traces/external/focused_scorer_evidence_adjudications.example.jsonl",
        ],
    ),
    (
        "hermes long-running adjudication validation",
        [
            "python3",
            "src/validate_adjudications.py",
            "traces/external/hermes_long_running_adjudications.example.jsonl",
        ],
    ),
    (
        "production-policy scenario adjudication validation",
        [
            "python3",
            "src/validate_adjudications.py",
            "traces/external/production_policy_scenario_adjudications.example.jsonl",
        ],
    ),
    (
        "sandbox agent benchmark adjudication validation",
        [
            "python3",
            "src/validate_adjudications.py",
            "traces/external/sandbox_agent_benchmark_adjudications.example.jsonl",
        ],
    ),
    (
        "M89 priority review adjudication validation",
        [
            "python3",
            "src/validate_adjudications.py",
            "traces/external/m89_priority_review_adjudications.example.jsonl",
        ],
    ),
    (
        "M90 high-severity pass adjudication validation",
        [
            "python3",
            "src/validate_adjudications.py",
            "traces/external/m90_high_severity_pass_adjudications.example.jsonl",
        ],
    ),
    (
        "M91 approval-gate pass adjudication validation",
        [
            "python3",
            "src/validate_adjudications.py",
            "traces/external/m91_approval_gate_pass_adjudications.example.jsonl",
        ],
    ),
    (
        "M92 remaining high-severity pass adjudication validation",
        [
            "python3",
            "src/validate_adjudications.py",
            "traces/external/m92_remaining_high_severity_pass_adjudications.example.jsonl",
        ],
    ),
    (
        "M93 medium-priority adjudication validation",
        [
            "python3",
            "src/validate_adjudications.py",
            "traces/external/m93_medium_priority_adjudications.example.jsonl",
        ],
    ),
    (
        "M94 remaining medium and safe adjudication validation",
        [
            "python3",
            "src/validate_adjudications.py",
            "traces/external/m94_remaining_medium_and_safe_adjudications.example.jsonl",
        ],
    ),
    (
        "M95 remaining safe direct-response adjudication validation",
        [
            "python3",
            "src/validate_adjudications.py",
            "traces/external/m95_remaining_safe_direct_response_adjudications.example.jsonl",
        ],
    ),
    (
        "adjudication manifest validation",
        ["python3", "src/validate_adjudication_manifest.py"],
    ),
    (
        "adjudication report generation",
        ["python3", "src/adjudication_report.py", "--manifest", "traces/external/adjudication_manifest.json"],
    ),
    (
        "adjudication regression snapshot check",
        [
            "python3",
            "src/adjudication_regression_check.py",
            "--manifest",
            "traces/external/adjudication_manifest.json",
        ],
    ),
    (
        "scorer calibration summary generation",
        ["python3", "src/scorer_calibration_summary.py"],
    ),
    (
        "scorer refinement triage generation",
        ["python3", "src/scorer_refinement_triage.py"],
    ),
    (
        "scorer candidate controls generation",
        ["python3", "src/scorer_candidate_controls.py"],
    ),
    (
        "scorer change decision generation",
        ["python3", "src/scorer_change_decision.py"],
    ),
    (
        "scorer versioning guardrails generation",
        ["python3", "src/scorer_versioning_guardrails.py"],
    ),
    (
        "focused scorer evidence expansion generation",
        ["python3", "src/focused_scorer_evidence_expansion.py"],
    ),
    (
        "scorer promotion decision generation",
        ["python3", "src/scorer_promotion_decision.py"],
    ),
    (
        "scorer reliability report generation",
        ["python3", "src/scorer_reliability_report.py"],
    ),
    (
        "review coverage priority plan generation",
        ["python3", "src/review_coverage_priority_plan.py"],
    ),
    (
        "review coverage completion gate generation",
        ["python3", "src/review_coverage_completion_gate.py"],
    ),
    (
        "baseline self trace comparison",
        [
            "python3",
            "src/compare_scored_traces.py",
            "--before",
            "traces/scored/baseline_mock_run.jsonl",
            "--after",
            "traces/scored/baseline_mock_run.jsonl",
            "--output",
            "reports/comparisons/baseline_self_comparison_report.md",
            "--title",
            "Baseline Self Comparison Report",
        ],
    ),
    (
        "reporting product summary generation",
        ["python3", "src/reporting_product_summary.py"],
    ),
    (
        "eval-awareness delta report generation",
        ["python3", "src/eval_awareness_delta.py"],
    ),
    (
        "evidence quality audit generation",
        ["python3", "src/evidence_quality_audit.py"],
    ),
    (
        "historical trend snapshot generation",
        ["python3", "src/historical_trend_snapshot.py"],
    ),
    (
        "release notes summary generation",
        ["python3", "src/release_notes_summary.py"],
    ),
    (
        "report manifest validation",
        ["python3", "src/validate_report_manifest.py"],
    ),
    (
        "benchmark claim charter validation",
        ["python3", "src/validate_benchmark_claim_charter.py"],
    ),
    (
        "local benchmark corpus generation",
        ["python3", "src/local_benchmark_corpus.py"],
    ),
    (
        "local benchmark corpus validation",
        ["python3", "src/validate_local_benchmark_corpus.py"],
    ),
    (
        "standards coverage generation",
        ["python3", "src/standards_coverage.py"],
    ),
    (
        "local adapter registry validation",
        ["python3", "src/validate_local_adapter_registry.py"],
    ),
    (
        "live-local dry-run plan validation",
        ["python3", "src/validate_live_local_run.py"],
    ),
    (
        "live-local review summary validation",
        ["python3", "src/live_local_review_summary.py"],
    ),
    (
        "local run ledger example generation",
        ["python3", "src/local_run_ledger.py"],
    ),
    (
        "local run ledger validation",
        ["python3", "src/validate_local_run_ledger.py"],
    ),
    (
        "M79 reviewed live-local ledger generation",
        ["python3", "src/m79_llama3_2_reviewed_ledger.py"],
    ),
    (
        "M79 reviewed live-local ledger validation",
        ["python3", "src/validate_local_run_ledger.py", "traces/external/m79_llama3_2_latest_extended.local_run_ledger.json"],
    ),
    (
        "M82 reviewed live-local ledger generation",
        ["python3", "src/m82_mistral_reviewed_ledger.py"],
    ),
    (
        "M82 reviewed live-local ledger validation",
        ["python3", "src/validate_local_run_ledger.py", "traces/external/m82_mistral_latest_extended.local_run_ledger.json"],
    ),
    (
        "M107B Qwen reviewed live-local ledger generation",
        ["python3", "src/m107b_qwen_reviewed_ledger.py"],
    ),
    (
        "M107B Qwen reviewed live-local ledger validation",
        [
            "python3",
            "src/validate_local_run_ledger.py",
            "traces/external/m107b_qwen35_2b_q4km_standard_no_think.local_run_ledger.json",
        ],
    ),
    (
        "M107B GLM reviewed live-local ledger generation",
        ["python3", "src/m107b_glm_reviewed_ledger.py"],
    ),
    (
        "M107B GLM reviewed live-local ledger validation",
        [
            "python3",
            "src/validate_local_run_ledger.py",
            "traces/external/m107b_glm4_latest_standard.local_run_ledger.json",
        ],
    ),
    (
        "M107B DeepSeek reviewed live-local ledger generation",
        ["python3", "src/m107b_deepseek_reviewed_ledger.py"],
    ),
    (
        "M107B DeepSeek reviewed live-local ledger validation",
        [
            "python3",
            "src/validate_local_run_ledger.py",
            "traces/external/m107b_deepseek_coder_6_7b_instruct_standard.local_run_ledger.json",
        ],
    ),
    (
        "M107B Code Llama reviewed live-local ledger generation",
        ["python3", "src/m107b_codellama_reviewed_ledger.py"],
    ),
    (
        "M107B Code Llama reviewed live-local ledger validation",
        [
            "python3",
            "src/validate_local_run_ledger.py",
            "traces/external/m107b_codellama_7b_instruct_standard.local_run_ledger.json",
        ],
    ),
    (
        "local ranking methodology generation",
        ["python3", "src/local_ranking_methodology.py"],
    ),
    (
        "local ranking methodology validation",
        ["python3", "src/validate_local_ranking_methodology.py"],
    ),
    (
        "local benchmark report generation",
        ["python3", "src/local_benchmark_report.py"],
    ),
    (
        "local benchmark report validation",
        ["python3", "src/validate_local_benchmark_report.py"],
    ),
    (
        "real-model proof runbook generation",
        ["python3", "src/real_model_proof_runbook.py"],
    ),
    (
        "runtime stability profile validation",
        ["python3", "src/runtime_stability_profile.py"],
    ),
    (
        "claim review checklist validation",
        ["python3", "src/claim_review_checklist.py"],
    ),
    (
        "public release bundle validation",
        ["python3", "src/public_release_bundle.py"],
    ),
    (
        "tool sandbox contract validation",
        ["python3", "src/validate_tool_sandbox_contract.py"],
    ),
    (
        "action boundary recorder generation",
        ["python3", "src/action_boundary_recorder.py"],
    ),
    (
        "openclaw harness smoke fixture generation",
        ["python3", "src/openclaw_harness_adapter.py"],
    ),
    (
        "openclaw harness smoke replay generation",
        [
            "python3",
            "src/replay_saved_transcripts.py",
            "--input",
            "traces/external/openclaw_harness_smoke_transcript.example.jsonl",
            "--output",
            "traces/scored/openclaw_harness_smoke_eval.jsonl",
            "--report",
            "reports/comparisons/openclaw_harness_smoke_report.md",
            "--run-id",
            "openclaw_harness_smoke",
            "--report-title",
            "OpenClaw Harness Smoke Report",
            "--report-context",
            OPENCLAW_HARNESS_SMOKE_REPORT_CONTEXT,
        ],
    ),
    (
        "py_compile",
        [
            "python3",
            "-m",
            "py_compile",
            "src/model_clients.py",
            "src/schema_validation_utils.py",
            "src/target_registry.py",
            "src/scorers.py",
            "src/trace_writer.py",
            "src/reporting_utils.py",
            "src/run_eval.py",
            "src/report_generator.py",
            "src/comparison_report.py",
            "src/regression_check.py",
            "src/inspect_failures.py",
            "src/evaluate_manual_outputs.py",
            "src/replay_saved_transcripts.py",
            "src/validate_schemas.py",
            "src/validate_adapter_outputs.py",
            "src/import_adapter_outputs.py",
            "src/dry_run_adapter.py",
            "src/text_only_adapter.py",
            "src/controlled_live_agent_sandbox.py",
            "src/validate_runtime_trial_plan.py",
            "src/validate_harness_bridge_plan.py",
            "src/compare_external_fixtures.py",
            "src/validate_fixture_manifest.py",
            "src/validate_adapter_run_metadata.py",
            "src/collect_text_only_outputs.py",
            "src/review_text_only_outputs.py",
            "src/promote_reviewed_outputs.py",
            "src/validate_adjudications.py",
            "src/validate_adjudication_manifest.py",
            "src/validate_report_manifest.py",
            "src/validate_benchmark_claim_charter.py",
            "src/local_benchmark_corpus.py",
            "src/validate_local_benchmark_corpus.py",
            "src/validate_local_adapter_registry.py",
            "src/live_local_harness.py",
            "src/validate_live_local_run.py",
            "src/live_local_review_summary.py",
            "src/local_run_ledger.py",
            "src/validate_local_run_ledger.py",
            "src/m79_llama3_2_reviewed_ledger.py",
            "src/m82_mistral_reviewed_ledger.py",
            "src/m107b_qwen_reviewed_ledger.py",
            "src/m107b_glm_reviewed_ledger.py",
            "src/m107b_deepseek_reviewed_ledger.py",
            "src/m107b_codellama_reviewed_ledger.py",
            "src/local_ranking_methodology.py",
            "src/validate_local_ranking_methodology.py",
            "src/local_benchmark_report.py",
            "src/validate_local_benchmark_report.py",
            "src/real_model_proof_runbook.py",
            "src/runtime_stability_profile.py",
            "src/claim_review_checklist.py",
            "src/public_release_bundle.py",
            "src/validate_tool_sandbox_contract.py",
            "src/action_boundary_recorder.py",
            "src/openclaw_harness_adapter.py",
            "src/long_running_agent_adapter.py",
            "src/production_policy_scenarios.py",
            "src/private_evidence_vault.py",
            "src/redaction_promotion_pipeline.py",
            "src/private_audit_report.py",
            "src/retention_consent_access.py",
            "src/hosted_provider_batch.py",
            "src/sandbox_agent_benchmark.py",
            "src/m107e_multimodal_pilot.py",
            "src/adjudication_report.py",
            "src/adjudication_regression_check.py",
            "src/scorer_calibration_summary.py",
            "src/scorer_refinement_triage.py",
            "src/scorer_candidate_controls.py",
            "src/scorer_change_decision.py",
            "src/scorer_versioning_guardrails.py",
            "src/focused_scorer_evidence_expansion.py",
            "src/scorer_promotion_decision.py",
            "src/scorer_reliability_report.py",
            "src/scorer_review_contract.py",
            "src/review_coverage_priority_plan.py",
            "src/review_coverage_completion_gate.py",
            "src/compare_scored_traces.py",
            "src/reporting_product_summary.py",
            "src/evidence_quality_audit.py",
            "src/historical_trend_snapshot.py",
            "src/release_notes_summary.py",
            "scripts/dev.py",
            "scripts/live_local.py",
        ],
    ),
]


def run_check(name: str, command: list[str]) -> None:
    """Run one quality-gate command and raise on failure."""

    print(f"==> {name}", flush=True)
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def verify_trace_count(path: Path, expected_lines: int) -> None:
    """Verify a generated scored trace exists and has the expected length."""

    print("==> trace count verification", flush=True)
    if not path.exists():
        raise RuntimeError(f"missing trace file: {path.relative_to(REPO_ROOT)}")

    with path.open("r", encoding="utf-8") as trace_file:
        line_count = sum(1 for _ in trace_file)

    if line_count != expected_lines:
        raise RuntimeError(
            f"expected {expected_lines} trace lines, found {line_count} in {path.relative_to(REPO_ROOT)}"
        )

    print(f"{path.relative_to(REPO_ROOT)} trace lines: {line_count}", flush=True)


def verify_jsonl_count(path: Path, expected_lines: int) -> None:
    """Verify a generated JSONL file exists and has the expected length."""

    print("==> JSONL count verification", flush=True)
    if not path.exists():
        raise RuntimeError(f"missing JSONL file: {path.relative_to(REPO_ROOT)}")

    with path.open("r", encoding="utf-8") as jsonl_file:
        line_count = sum(1 for _ in jsonl_file)

    if line_count != expected_lines:
        raise RuntimeError(
            f"expected {expected_lines} JSONL lines, found {line_count} in {path.relative_to(REPO_ROOT)}"
        )

    print(f"{path.relative_to(REPO_ROOT)} JSONL lines: {line_count}", flush=True)


def verify_report_exists(path: Path) -> None:
    """Verify a generated report exists and is non-empty."""

    print("==> report verification", flush=True)
    if not path.exists():
        raise RuntimeError(f"missing report file: {path.relative_to(REPO_ROOT)}")
    if path.stat().st_size == 0:
        raise RuntimeError(f"empty report file: {path.relative_to(REPO_ROOT)}")
    print(f"{path.relative_to(REPO_ROOT)} exists", flush=True)


def main() -> int:
    try:
        for name, command in CHECKS:
            run_check(name, command)
            if name == "adapter output fixture import":
                verify_trace_count(ADAPTER_OUTPUT_TRACE_PATH, EXPECTED_ADAPTER_OUTPUT_TRACE_LINES)
            if name == "dry-run adapter generation":
                verify_jsonl_count(DRY_RUN_ADAPTER_OUTPUT_PATH, EXPECTED_DRY_RUN_ADAPTER_OUTPUT_LINES)
            if name == "dry-run adapter output import":
                verify_trace_count(DRY_RUN_ADAPTER_TRACE_PATH, EXPECTED_DRY_RUN_ADAPTER_TRACE_LINES)
            if name == "mock eval generation":
                verify_trace_count(BASELINE_TRACE_PATH, EXPECTED_BASELINE_TRACE_LINES)
            if name == "manual output eval generation":
                verify_trace_count(MANUAL_TRACE_PATH, EXPECTED_MANUAL_TRACE_LINES)
            if name == "openclaw-style manual eval generation":
                verify_trace_count(OPENCLAW_MANUAL_TRACE_PATH, EXPECTED_OPENCLAW_MANUAL_TRACE_LINES)
            if name == "focused scorer evidence generation":
                verify_trace_count(
                    FOCUSED_SCORER_EVIDENCE_TRACE_PATH,
                    EXPECTED_FOCUSED_SCORER_EVIDENCE_TRACE_LINES,
                )
                verify_report_exists(FOCUSED_SCORER_EVIDENCE_REPORT_PATH)
            if name == "saved transcript replay generation":
                verify_trace_count(SAVED_TRANSCRIPT_TRACE_PATH, EXPECTED_SAVED_TRANSCRIPT_TRACE_LINES)
            if name == "openclaw saved transcript pilot generation":
                verify_trace_count(OPENCLAW_SAVED_TRANSCRIPT_TRACE_PATH, EXPECTED_OPENCLAW_SAVED_TRANSCRIPT_TRACE_LINES)
                verify_report_exists(OPENCLAW_SAVED_TRANSCRIPT_REPORT_PATH)
            if name == "public-safe transcript expansion generation":
                verify_trace_count(
                    PUBLIC_SAFE_TRANSCRIPT_EXPANSION_TRACE_PATH,
                    EXPECTED_PUBLIC_SAFE_TRANSCRIPT_EXPANSION_TRACE_LINES,
                )
                verify_report_exists(PUBLIC_SAFE_TRANSCRIPT_EXPANSION_REPORT_PATH)
            if name == "external fixture comparison report generation":
                verify_report_exists(EXTERNAL_FIXTURE_COMPARISON_REPORT_PATH)
            if name == "adjudication report generation":
                verify_report_exists(ADJUDICATION_SUMMARY_REPORT_PATH)
                verify_report_exists(ADJUDICATED_AGGREGATE_REPORT_PATH)
            if name == "adjudication regression snapshot check":
                verify_report_exists(ADJUDICATION_REGRESSION_SNAPSHOT_PATH)
            if name == "scorer calibration summary generation":
                verify_report_exists(SCORER_CALIBRATION_JSON_PATH)
                verify_report_exists(SCORER_CALIBRATION_REPORT_PATH)
            if name == "scorer refinement triage generation":
                verify_report_exists(SCORER_REFINEMENT_TRIAGE_JSON_PATH)
                verify_report_exists(SCORER_REFINEMENT_TRIAGE_REPORT_PATH)
            if name == "scorer candidate controls generation":
                verify_report_exists(SCORER_CANDIDATE_CONTROLS_JSON_PATH)
                verify_report_exists(SCORER_CANDIDATE_CONTROLS_REPORT_PATH)
            if name == "scorer change decision generation":
                verify_report_exists(SCORER_CHANGE_DECISION_JSON_PATH)
                verify_report_exists(SCORER_CHANGE_DECISION_REPORT_PATH)
            if name == "scorer versioning guardrails generation":
                verify_report_exists(SCORER_VERSIONING_GUARDRAILS_JSON_PATH)
                verify_report_exists(SCORER_VERSIONING_GUARDRAILS_REPORT_PATH)
            if name == "focused scorer evidence expansion generation":
                verify_report_exists(FOCUSED_SCORER_EVIDENCE_JSON_PATH)
                verify_report_exists(FOCUSED_SCORER_EVIDENCE_EXPANSION_REPORT_PATH)
            if name == "scorer promotion decision generation":
                verify_report_exists(SCORER_PROMOTION_DECISION_JSON_PATH)
                verify_report_exists(SCORER_PROMOTION_DECISION_REPORT_PATH)
            if name == "scorer reliability report generation":
                verify_report_exists(SCORER_RELIABILITY_JSON_PATH)
                verify_report_exists(SCORER_RELIABILITY_REPORT_PATH)
            if name == "review coverage priority plan generation":
                verify_report_exists(REVIEW_COVERAGE_PRIORITY_JSON_PATH)
                verify_report_exists(REVIEW_COVERAGE_PRIORITY_REPORT_PATH)
            if name == "review coverage completion gate generation":
                verify_report_exists(REVIEW_COVERAGE_COMPLETION_JSON_PATH)
                verify_report_exists(REVIEW_COVERAGE_COMPLETION_REPORT_PATH)
            if name == "baseline self trace comparison":
                verify_report_exists(BASELINE_SELF_COMPARISON_REPORT_PATH)
            if name == "reporting product summary generation":
                verify_report_exists(REPORTING_PRODUCT_SUMMARY_JSON_PATH)
                verify_report_exists(REPORTING_PRODUCT_SUMMARY_REPORT_PATH)
                verify_report_exists(EVAL_AWARENESS_DELTA_JSON_PATH)
                verify_report_exists(EVAL_AWARENESS_DELTA_REPORT_PATH)
            if name == "evidence quality audit generation":
                verify_report_exists(EVIDENCE_QUALITY_AUDIT_JSON_PATH)
                verify_report_exists(EVIDENCE_QUALITY_AUDIT_REPORT_PATH)
            if name == "historical trend snapshot generation":
                verify_report_exists(HISTORICAL_TREND_JSON_PATH)
                verify_report_exists(HISTORICAL_TREND_REPORT_PATH)
            if name == "release notes summary generation":
                verify_report_exists(RELEASE_NOTES_JSON_PATH)
                verify_report_exists(RELEASE_NOTES_REPORT_PATH)
            if name == "benchmark claim charter validation":
                verify_report_exists(BENCHMARK_CLAIM_CHARTER_PATH)
            if name == "local benchmark corpus generation":
                verify_jsonl_count(LOCAL_BENCHMARK_CASE_PATH, EXPECTED_LOCAL_BENCHMARK_CASE_LINES)
                verify_report_exists(LOCAL_BENCHMARK_MANIFEST_PATH)
            if name == "local benchmark corpus validation":
                verify_report_exists(LOCAL_BENCHMARK_MANIFEST_PATH)
            if name == "standards coverage generation":
                verify_report_exists(STANDARDS_COVERAGE_JSON_PATH)
                verify_report_exists(STANDARDS_COVERAGE_REPORT_PATH)
            if name == "local adapter registry validation":
                verify_report_exists(LOCAL_ADAPTER_REGISTRY_PATH)
            if name == "live-local dry-run plan validation":
                verify_report_exists(LIVE_LOCAL_RUN_PLAN_PATH)
            if name == "live-local review summary validation":
                verify_report_exists(LIVE_LOCAL_REVIEW_SUMMARY_PATH)
                verify_report_exists(LIVE_LOCAL_REVIEW_SUMMARY_JSON_PATH)
                verify_report_exists(LIVE_LOCAL_REVIEW_SUMMARY_REPORT_PATH)
            if name == "local run ledger example generation":
                verify_report_exists(LOCAL_RUN_LEDGER_PATH)
                verify_report_exists(LOCAL_RUN_LEDGER_METADATA_PATH)
                verify_jsonl_count(LOCAL_RUN_LEDGER_OUTPUT_PATH, EXPECTED_LOCAL_RUN_LEDGER_OUTPUT_LINES)
                verify_trace_count(LOCAL_RUN_LEDGER_SCORED_TRACE_PATH, EXPECTED_LOCAL_RUN_LEDGER_SCORED_TRACE_LINES)
            if name == "local run ledger validation":
                verify_report_exists(LOCAL_RUN_LEDGER_PATH)
            if name == "M79 reviewed live-local ledger generation":
                verify_jsonl_count(M79_REVIEWED_OUTPUT_PATH, EXPECTED_M79_REVIEWED_LINES)
                verify_report_exists(M79_REVIEW_SUMMARY_PATH)
                verify_report_exists(M79_RUN_METADATA_PATH)
                verify_report_exists(M79_RUN_LEDGER_PATH)
                verify_trace_count(M79_SCORED_TRACE_PATH, EXPECTED_M79_SCORED_TRACE_LINES)
            if name == "M79 reviewed live-local ledger validation":
                verify_report_exists(M79_RUN_LEDGER_PATH)
            if name == "M82 reviewed live-local ledger generation":
                verify_jsonl_count(M82_REVIEWED_OUTPUT_PATH, EXPECTED_M82_REVIEWED_LINES)
                verify_report_exists(M82_REVIEW_SUMMARY_PATH)
                verify_report_exists(M82_RUN_METADATA_PATH)
                verify_report_exists(M82_RUN_LEDGER_PATH)
                verify_trace_count(M82_SCORED_TRACE_PATH, EXPECTED_M82_SCORED_TRACE_LINES)
            if name == "M82 reviewed live-local ledger validation":
                verify_report_exists(M82_RUN_LEDGER_PATH)
            if name == "M107B Qwen reviewed live-local ledger generation":
                verify_jsonl_count(M107B_QWEN_REVIEWED_OUTPUT_PATH, EXPECTED_M107B_QWEN_REVIEWED_LINES)
                verify_report_exists(M107B_QWEN_REVIEW_SUMMARY_PATH)
                verify_report_exists(M107B_QWEN_RUN_METADATA_PATH)
                verify_report_exists(M107B_QWEN_RUN_LEDGER_PATH)
                verify_trace_count(M107B_QWEN_SCORED_TRACE_PATH, EXPECTED_M107B_QWEN_SCORED_TRACE_LINES)
            if name == "M107B Qwen reviewed live-local ledger validation":
                verify_report_exists(M107B_QWEN_RUN_LEDGER_PATH)
            if name == "M107B GLM reviewed live-local ledger generation":
                verify_jsonl_count(M107B_GLM_REVIEWED_OUTPUT_PATH, EXPECTED_M107B_GLM_REVIEWED_LINES)
                verify_report_exists(M107B_GLM_REVIEW_SUMMARY_PATH)
                verify_report_exists(M107B_GLM_RUN_METADATA_PATH)
                verify_report_exists(M107B_GLM_RUN_LEDGER_PATH)
                verify_trace_count(M107B_GLM_SCORED_TRACE_PATH, EXPECTED_M107B_GLM_SCORED_TRACE_LINES)
            if name == "M107B GLM reviewed live-local ledger validation":
                verify_report_exists(M107B_GLM_RUN_LEDGER_PATH)
            if name == "M107B DeepSeek reviewed live-local ledger generation":
                verify_jsonl_count(M107B_DEEPSEEK_REVIEWED_OUTPUT_PATH, EXPECTED_M107B_DEEPSEEK_REVIEWED_LINES)
                verify_report_exists(M107B_DEEPSEEK_REVIEW_SUMMARY_PATH)
                verify_report_exists(M107B_DEEPSEEK_RUN_METADATA_PATH)
                verify_report_exists(M107B_DEEPSEEK_RUN_LEDGER_PATH)
                verify_trace_count(M107B_DEEPSEEK_SCORED_TRACE_PATH, EXPECTED_M107B_DEEPSEEK_SCORED_TRACE_LINES)
            if name == "M107B DeepSeek reviewed live-local ledger validation":
                verify_report_exists(M107B_DEEPSEEK_RUN_LEDGER_PATH)
            if name == "M107B Code Llama reviewed live-local ledger generation":
                verify_jsonl_count(M107B_CODELLAMA_REVIEWED_OUTPUT_PATH, EXPECTED_M107B_CODELLAMA_REVIEWED_LINES)
                verify_report_exists(M107B_CODELLAMA_REVIEW_SUMMARY_PATH)
                verify_report_exists(M107B_CODELLAMA_RUN_METADATA_PATH)
                verify_report_exists(M107B_CODELLAMA_RUN_LEDGER_PATH)
                verify_trace_count(M107B_CODELLAMA_SCORED_TRACE_PATH, EXPECTED_M107B_CODELLAMA_SCORED_TRACE_LINES)
            if name == "M107B Code Llama reviewed live-local ledger validation":
                verify_report_exists(M107B_CODELLAMA_RUN_LEDGER_PATH)
            if name == "local ranking methodology generation":
                verify_report_exists(LOCAL_RANKING_METHODOLOGY_PATH)
                verify_report_exists(LOCAL_RANKING_METHODOLOGY_INPUT_PATH)
                verify_report_exists(LOCAL_RANKING_METHODOLOGY_SNAPSHOT_PATH)
                verify_report_exists(LOCAL_RANKING_METHODOLOGY_REPORT_PATH)
            if name == "local ranking methodology validation":
                verify_report_exists(LOCAL_RANKING_METHODOLOGY_PATH)
                verify_report_exists(LOCAL_RANKING_METHODOLOGY_SNAPSHOT_PATH)
            if name == "local benchmark report generation":
                verify_report_exists(LOCAL_BENCHMARK_REPORT_SNAPSHOT_PATH)
                verify_report_exists(LOCAL_BENCHMARK_REPORT_PATH)
            if name == "local benchmark report validation":
                verify_report_exists(LOCAL_BENCHMARK_REPORT_SNAPSHOT_PATH)
                verify_report_exists(LOCAL_BENCHMARK_REPORT_PATH)
            if name == "real-model proof runbook generation":
                verify_report_exists(REAL_MODEL_PROOF_RUNBOOK_PATH)
                verify_report_exists(REAL_MODEL_PROOF_RUNBOOK_JSON_PATH)
                verify_report_exists(REAL_MODEL_PROOF_RUNBOOK_REPORT_PATH)
            if name == "runtime stability profile validation":
                verify_report_exists(RUNTIME_STABILITY_PROFILE_PATH)
            if name == "claim review checklist validation":
                verify_report_exists(CLAIM_REVIEW_CHECKLIST_PATH)
            if name == "public release bundle validation":
                verify_report_exists(PUBLIC_RELEASE_BUNDLE_PATH)
            if name == "tool sandbox contract validation":
                verify_jsonl_count(TOOL_CALL_SUMMARY_PATH, EXPECTED_TOOL_CALL_SUMMARY_LINES)
            if name == "action boundary recorder generation":
                verify_jsonl_count(ACTION_BOUNDARY_INPUT_PATH, EXPECTED_ACTION_BOUNDARY_INPUT_LINES)
                verify_jsonl_count(APPROVAL_EVENT_PATH, EXPECTED_APPROVAL_EVENT_LINES)
                verify_jsonl_count(ACTION_DENIAL_PATH, EXPECTED_ACTION_DENIAL_LINES)
            if name == "openclaw harness smoke fixture generation":
                verify_report_exists(OPENCLAW_HARNESS_PLAN_PATH)
                verify_jsonl_count(OPENCLAW_HARNESS_TRANSCRIPT_PATH, EXPECTED_OPENCLAW_HARNESS_TRANSCRIPT_LINES)
                verify_jsonl_count(OPENCLAW_HARNESS_TOOL_SUMMARY_PATH, EXPECTED_OPENCLAW_HARNESS_TOOL_SUMMARY_LINES)
            if name == "openclaw harness smoke replay generation":
                verify_trace_count(OPENCLAW_HARNESS_TRACE_PATH, EXPECTED_OPENCLAW_HARNESS_TRACE_LINES)
                verify_report_exists(OPENCLAW_HARNESS_REPORT_PATH)
            if name == "long-running agent session fixture generation":
                verify_report_exists(LONG_RUNNING_AGENT_PLAN_PATH)
                verify_jsonl_count(
                    LONG_RUNNING_AGENT_TRANSCRIPT_PATH,
                    EXPECTED_LONG_RUNNING_AGENT_TRANSCRIPT_LINES,
                )
                verify_jsonl_count(
                    LONG_RUNNING_AGENT_SESSION_BOUNDARY_PATH,
                    EXPECTED_LONG_RUNNING_AGENT_SESSION_BOUNDARY_LINES,
                )
                verify_jsonl_count(
                    LONG_RUNNING_AGENT_MEMORY_CHECK_PATH,
                    EXPECTED_LONG_RUNNING_AGENT_MEMORY_CHECK_LINES,
                )
            if name == "long-running agent session replay generation":
                verify_trace_count(LONG_RUNNING_AGENT_TRACE_PATH, EXPECTED_LONG_RUNNING_AGENT_TRACE_LINES)
                verify_report_exists(LONG_RUNNING_AGENT_REPORT_PATH)
            if name == "production-policy scenario fixture generation":
                verify_report_exists(PRODUCTION_POLICY_SCENARIO_PACK_PATH)
                verify_jsonl_count(
                    PRODUCTION_POLICY_SCENARIO_TRANSCRIPT_PATH,
                    EXPECTED_PRODUCTION_POLICY_SCENARIO_TRANSCRIPT_LINES,
                )
                verify_jsonl_count(
                    PRODUCTION_POLICY_SCENARIO_CHECK_PATH,
                    EXPECTED_PRODUCTION_POLICY_SCENARIO_CHECK_LINES,
                )
            if name == "production-policy scenario replay generation":
                verify_trace_count(
                    PRODUCTION_POLICY_SCENARIO_TRACE_PATH,
                    EXPECTED_PRODUCTION_POLICY_SCENARIO_TRACE_LINES,
                )
                verify_report_exists(PRODUCTION_POLICY_SCENARIO_REPORT_PATH)
            if name == "sandbox agent benchmark generation":
                verify_jsonl_count(SANDBOX_AGENT_RUN_PATH, EXPECTED_SANDBOX_AGENT_RUN_LINES)
                verify_jsonl_count(SANDBOX_ACTION_EVENT_PATH, EXPECTED_SANDBOX_ACTION_EVENT_LINES)
                verify_trace_count(SANDBOX_AGENT_TRACE_PATH, EXPECTED_SANDBOX_AGENT_TRACE_LINES)
                verify_jsonl_count(SANDBOX_AGENT_ADJUDICATION_PATH, EXPECTED_SANDBOX_AGENT_ADJUDICATION_LINES)
                verify_report_exists(SANDBOX_AGENT_REPORT_JSON_PATH)
                verify_report_exists(SANDBOX_AGENT_REPORT_PATH)
            if name == "M107E multimodal pilot generation":
                verify_report_exists(M107E_MULTIMODAL_FIXTURE_SET_PATH)
                verify_jsonl_count(
                    M107E_MULTIMODAL_SAVED_OUTPUT_PATH,
                    EXPECTED_M107E_MULTIMODAL_SAVED_OUTPUT_LINES,
                )
                verify_report_exists(M107E_MULTIMODAL_REVIEW_SUMMARY_PATH)
                verify_report_exists(M107E_MULTIMODAL_REPORT_JSON_PATH)
                verify_report_exists(M107E_MULTIMODAL_REPORT_PATH)
            if name == "private evidence vault validation":
                verify_report_exists(PRIVATE_EVIDENCE_VAULT_MANIFEST_PATH)
                verify_report_exists(PRIVATE_EVIDENCE_VAULT_SUMMARY_JSON_PATH)
                verify_report_exists(PRIVATE_EVIDENCE_VAULT_SUMMARY_REPORT_PATH)
            if name == "redaction promotion pipeline validation":
                verify_report_exists(REDACTION_PROMOTION_CANDIDATE_PATH)
                verify_jsonl_count(REDACTION_NOTE_PATH, EXPECTED_REDACTION_NOTE_LINES)
                verify_jsonl_count(
                    PROMOTED_PRIVATE_EVIDENCE_OUTPUT_PATH,
                    EXPECTED_PROMOTED_PRIVATE_EVIDENCE_OUTPUT_LINES,
                )
                verify_report_exists(REDACTION_PROMOTION_SUMMARY_JSON_PATH)
                verify_report_exists(REDACTION_PROMOTION_SUMMARY_REPORT_PATH)
            if name == "private audit report validation":
                verify_report_exists(PRIVATE_AUDIT_REPORT_METADATA_PATH)
                verify_report_exists(PRIVATE_AUDIT_REPORT_JSON_PATH)
                verify_report_exists(PRIVATE_AUDIT_REPORT_MARKDOWN_PATH)
                verify_report_exists(PRIVATE_AUDIT_REPORT_SUMMARY_JSON_PATH)
                verify_report_exists(PRIVATE_AUDIT_REPORT_SUMMARY_REPORT_PATH)
            if name == "retention consent access validation":
                verify_report_exists(RETENTION_CONSENT_ACCESS_METADATA_PATH)
                verify_report_exists(RETENTION_CONSENT_ACCESS_SUMMARY_JSON_PATH)
                verify_report_exists(RETENTION_CONSENT_ACCESS_SUMMARY_REPORT_PATH)
            if name == "hosted provider batch metadata validation":
                verify_report_exists(HOSTED_PROVIDER_BATCH_METADATA_PATH)
                verify_report_exists(HOSTED_PROVIDER_BATCH_SUMMARY_JSON_PATH)
                verify_report_exists(HOSTED_PROVIDER_BATCH_SUMMARY_REPORT_PATH)
    except (subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    print("local quality gate passed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
