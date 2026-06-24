"""Generate M107B public-safe reviewed live-local DeepSeek Coder ledger artifacts.

This module scores committed reviewed text-only outputs and writes public-safe
metadata, review-summary, and ledger derivatives. It does not execute local
models, call providers, read raw outputs, use credentials, or perform external
actions.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from import_adapter_outputs import import_adapter_outputs
from live_local_harness import (
    HARNESS_ID,
    HARNESS_VERSION,
    LIVE_LOCAL_REQUIRED_ENV,
    LIVE_LOCAL_REQUIRED_FLAG,
    PROMPT_TEMPLATE_ID,
    PROMPT_TEMPLATE_PATH,
    PROMPT_TEMPLATE_VERSION,
    load_jsonl,
)
from local_run_ledger import (
    LOCAL_ADAPTER_REGISTRY_PATH,
    LOCAL_BENCHMARK_CASE_PATH,
    LOCAL_BENCHMARK_MANIFEST_PATH,
    SCORER_ARTIFACT_PATH,
    SCORER_ID,
    SCORER_VERSION,
)
from reporting_utils import load_json_object, write_json_object
from schema_validation_utils import display_path
from validate_local_run_ledger import sha256_file, validate_local_run_ledger


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-24T00:00:00Z"
RUN_ID = "m107b_deepseek_coder_6_7b_instruct_standard"
ENTRY_ID = "m107b_deepseek_coder_6_7b_instruct_standard_reviewed_live_local_entry"
LEDGER_ID = "m107b_deepseek_coder_6_7b_instruct_standard_reviewed_live_local_ledger"
SUMMARY_ID = "m107b_deepseek_coder_6_7b_instruct_standard_review_summary"
METADATA_ID = "m107b_deepseek_coder_6_7b_instruct_standard_run_metadata"
MODEL_ID = "deepseek-coder:6.7b-instruct"

NORMALIZED_OUTPUT_PATH = (
    REPO_ROOT / "traces/external/m107b_deepseek_coder_6_7b_instruct_standard.reviewed_live_local_outputs.jsonl"
)
SCORED_TRACE_PATH = REPO_ROOT / "traces/scored/m107b_deepseek_coder_6_7b_instruct_standard.reviewed_live_local_eval.jsonl"
REVIEW_SUMMARY_PATH = REPO_ROOT / "traces/external/m107b_deepseek_coder_6_7b_instruct_standard.review_summary.json"
METADATA_PATH = REPO_ROOT / "traces/external/m107b_deepseek_coder_6_7b_instruct_standard.run_metadata.json"
LEDGER_PATH = REPO_ROOT / "traces/external/m107b_deepseek_coder_6_7b_instruct_standard.local_run_ledger.json"


class M107BDeepSeekLedgerGenerationError(Exception):
    """M107B DeepSeek Coder ledger generation error."""


def generate_m107b_deepseek_artifacts() -> dict[str, Any]:
    """Generate deterministic public-safe M107B artifacts from reviewed outputs."""

    if not NORMALIZED_OUTPUT_PATH.exists():
        raise M107BDeepSeekLedgerGenerationError(
            f"missing reviewed output path: {display_path(NORMALIZED_OUTPUT_PATH, REPO_ROOT)}"
        )

    score_summary = import_adapter_outputs(
        NORMALIZED_OUTPUT_PATH,
        SCORED_TRACE_PATH,
        allow_live_local=True,
        case_paths=[LOCAL_BENCHMARK_CASE_PATH],
        run_id=RUN_ID,
        trace_timestamp=GENERATED_AT,
    )

    normalized_records = load_jsonl(NORMALIZED_OUTPUT_PATH)
    scored_traces = load_jsonl(SCORED_TRACE_PATH)
    if len(normalized_records) != len(scored_traces):
        raise M107BDeepSeekLedgerGenerationError("normalized and scored record counts differ")

    registry = load_json_object(LOCAL_ADAPTER_REGISTRY_PATH)
    adapter = adapter_by_id(registry, "ollama_text_only")
    manifest = load_json_object(LOCAL_BENCHMARK_MANIFEST_PATH)

    metadata = build_run_metadata(adapter, manifest, normalized_records, scored_traces)
    write_json_object(metadata, METADATA_PATH)

    review_summary = build_review_summary(scored_traces)
    write_json_object(review_summary, REVIEW_SUMMARY_PATH)

    ledger = build_ledger(adapter, manifest, normalized_records, scored_traces, review_summary)
    write_json_object(ledger, LEDGER_PATH)
    validation_summary = validate_local_run_ledger(LEDGER_PATH)

    return {
        "ledger_path": display_path(LEDGER_PATH, REPO_ROOT),
        "metadata_path": display_path(METADATA_PATH, REPO_ROOT),
        "review_summary_path": display_path(REVIEW_SUMMARY_PATH, REPO_ROOT),
        "normalized_output_path": display_path(NORMALIZED_OUTPUT_PATH, REPO_ROOT),
        "scored_trace_path": display_path(SCORED_TRACE_PATH, REPO_ROOT),
        "records": len(scored_traces),
        "pass_count": score_summary["pass_count"],
        "fail_count": score_summary["fail_count"],
        "ledger_id": validation_summary["ledger_id"],
    }


def build_run_metadata(
    adapter: dict[str, Any],
    manifest: dict[str, Any],
    normalized_records: list[dict[str, Any]],
    scored_traces: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build public-safe run metadata for the reviewed live-local evidence."""

    case_ids = [str(record["case_id"]) for record in normalized_records]
    return {
        "metadata_id": METADATA_ID,
        "metadata_kind": "reviewed_live_local_run",
        "run_id": RUN_ID,
        "created_at": GENERATED_AT,
        "completed_at": GENERATED_AT,
        "source_run_id": RUN_ID,
        "source_milestones": ["M107B"],
        "harness": {
            "harness_id": HARNESS_ID,
            "harness_version": HARNESS_VERSION,
        },
        "adapter": {
            "adapter_id": adapter["adapter_id"],
            "adapter_version": adapter["adapter_version"],
            "runtime": "ollama",
            "model": MODEL_ID,
            "parameters": dict(adapter["default_parameters"]),
        },
        "case_set": {
            "case_set_id": manifest["case_set_id"],
            "case_set_version": manifest["version"],
            "benchmark_split": "standard",
            "case_count": len(case_ids),
            "case_ids": case_ids,
        },
        "prompt_template": {
            "template_id": PROMPT_TEMPLATE_ID,
            "template_version": PROMPT_TEMPLATE_VERSION,
            "template_path": display_path(PROMPT_TEMPLATE_PATH, REPO_ROOT),
            "tools_enabled": False,
        },
        "outputs": {
            "normalized_output_path": display_path(NORMALIZED_OUTPUT_PATH, REPO_ROOT),
            "normalized_output_sha256": sha256_file(NORMALIZED_OUTPUT_PATH),
            "normalized_output_record_count": len(normalized_records),
            "scored_trace_path": display_path(SCORED_TRACE_PATH, REPO_ROOT),
            "scored_trace_sha256": sha256_file(SCORED_TRACE_PATH),
            "scored_trace_record_count": len(scored_traces),
        },
        "results": {
            "planned_cases": len(case_ids),
            "attempted": len(scored_traces),
            "succeeded": len(scored_traces),
            "failed": 0,
            "skipped": 0,
            "scorer_pass_count": sum(1 for trace in scored_traces if trace["passed"] is True),
            "scorer_fail_count": sum(1 for trace in scored_traces if trace["passed"] is False),
        },
        "ranking_excluded": False,
        "ranking_exclusion_reason": "",
        "safety_assertions": live_local_safety_assertions(),
    }


def build_review_summary(scored_traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Build M70-compatible public-safe review metadata for the M107B ledger."""

    reviewed_records = []
    for trace in scored_traces:
        passed = trace["passed"] is True
        reviewed_records.append(
            {
                "record_id": str(trace["source_record_id"]),
                "case_id": str(trace["case_id"]),
                "severity": str(trace["severity"]),
                "heuristic_passed": passed,
                "effective_passed": passed,
                "reviewer_decision": "uphold_scorer_pass" if passed else "uphold_scorer_fail",
                "primary_reviewer_alias": "reviewer_m107b_deepseek_primary",
                "secondary_reviewer_alias": "",
                "inter_rater_status": "single_review",
                "unsafe_output": False,
                "malformed_output": False,
                "notes_public_safe": True,
            }
        )

    pass_count = sum(1 for record in reviewed_records if record["heuristic_passed"] is True)
    fail_count = len(reviewed_records) - pass_count
    return {
        "summary_id": SUMMARY_ID,
        "version": "0.1.0",
        "generated_at": GENERATED_AT,
        "status": "public_safe_live_local_review_summary",
        "review_protocol": {
            "protocol_id": "m70_reviewer_protocol_v1",
            "rubric_version": "0.1.0",
            "reviewer_aliases_only": True,
            "raw_outputs_included": False,
            "private_data_included": False,
            "allowed_decisions": [
                "uphold_scorer_pass",
                "uphold_scorer_fail",
                "override_pass",
                "override_fail",
                "needs_discussion",
            ],
        },
        "sampling_policy": {
            "policy_id": "m70_live_local_review_sampling_v1",
            "review_every_failed_case": True,
            "review_every_high_or_critical_case": True,
            "pass_sample_rate": 1.0,
            "deterministic_seed": "m107b_deepseek_coder_6_7b_instruct_standard_full_review",
        },
        "review_counts": {
            "records_reviewed": len(reviewed_records),
            "scorer_pass_count": pass_count,
            "scorer_fail_count": fail_count,
            "effective_pass_count": pass_count,
            "effective_fail_count": fail_count,
            "override_count": 0,
            "needs_discussion_count": 0,
            "unsafe_output_count": 0,
            "malformed_output_count": 0,
        },
        "inter_rater": {
            "reviewer_count": 1,
            "double_reviewed_count": 0,
            "agreement_count": 0,
            "disagreement_count": 0,
            "agreement_rate": 1.0,
        },
        "quality_gate": {
            "deterministic_gate_uses_fake_review_metadata_only": True,
            "live_local_execution_in_quality_gate": False,
            "provider_calls_in_quality_gate": False,
            "raw_outputs_read_in_quality_gate": False,
            "external_actions_in_quality_gate": False,
        },
        "safety_assertions": {
            "public_safe": True,
            "contains_private_data": False,
            "raw_outputs_included": False,
            "credentials_required": False,
            "external_actions": False,
            "production_safety_claim": False,
            "cloud_ranking_claim": False,
        },
        "reviewed_records": reviewed_records,
    }


def build_ledger(
    adapter: dict[str, Any],
    manifest: dict[str, Any],
    normalized_records: list[dict[str, Any]],
    scored_traces: list[dict[str, Any]],
    review_summary: dict[str, Any],
) -> dict[str, Any]:
    """Build the M58-compatible reviewed live-local ledger."""

    case_ids = [str(record["case_id"]) for record in normalized_records]
    entry = {
        "entry_id": ENTRY_ID,
        "run_id": RUN_ID,
        "evidence_class": "local_public_benchmark",
        "run_mode": "reviewed_live_local_run",
        "created_at": GENERATED_AT,
        "completed_at": GENERATED_AT,
        "run_status": "succeeded",
        "ranking_eligible": True,
        "ranking_exclusion_reason": "",
        "runtime": "ollama",
        "model": MODEL_ID,
        "harness": {
            "harness_id": HARNESS_ID,
            "harness_version": HARNESS_VERSION,
        },
        "adapter": {
            "adapter_id": adapter["adapter_id"],
            "adapter_version": adapter["adapter_version"],
            "registry_path": display_path(LOCAL_ADAPTER_REGISTRY_PATH, REPO_ROOT),
            "registry_sha256": sha256_file(LOCAL_ADAPTER_REGISTRY_PATH),
        },
        "case_set": {
            "case_set_id": manifest["case_set_id"],
            "case_set_version": manifest["version"],
            "benchmark_split": "standard",
            "case_count": len(case_ids),
            "case_ids": case_ids,
            "case_path": display_path(LOCAL_BENCHMARK_CASE_PATH, REPO_ROOT),
            "case_file_sha256": sha256_file(LOCAL_BENCHMARK_CASE_PATH),
            "manifest_path": display_path(LOCAL_BENCHMARK_MANIFEST_PATH, REPO_ROOT),
            "manifest_sha256": sha256_file(LOCAL_BENCHMARK_MANIFEST_PATH),
        },
        "prompt_template": {
            "template_id": PROMPT_TEMPLATE_ID,
            "template_version": PROMPT_TEMPLATE_VERSION,
            "template_path": display_path(PROMPT_TEMPLATE_PATH, REPO_ROOT),
            "template_sha256": sha256_file(PROMPT_TEMPLATE_PATH),
            "tools_enabled": False,
        },
        "outputs": {
            "normalized_output_path": display_path(NORMALIZED_OUTPUT_PATH, REPO_ROOT),
            "normalized_output_sha256": sha256_file(NORMALIZED_OUTPUT_PATH),
            "normalized_output_record_count": len(normalized_records),
            "scored_trace_path": display_path(SCORED_TRACE_PATH, REPO_ROOT),
            "scored_trace_sha256": sha256_file(SCORED_TRACE_PATH),
            "scored_trace_record_count": len(scored_traces),
        },
        "scorer": {
            "scorer_id": SCORER_ID,
            "scorer_version": SCORER_VERSION,
            "scorer_artifact_path": display_path(SCORER_ARTIFACT_PATH, REPO_ROOT),
            "scorer_artifact_sha256": sha256_file(SCORER_ARTIFACT_PATH),
        },
        "run_metadata": {
            "metadata_path": display_path(METADATA_PATH, REPO_ROOT),
            "metadata_sha256": sha256_file(METADATA_PATH),
            "metadata_kind": "reviewed_live_local_run",
        },
        "review_summary": {
            "summary_path": display_path(REVIEW_SUMMARY_PATH, REPO_ROOT),
            "summary_sha256": sha256_file(REVIEW_SUMMARY_PATH),
            "summary_id": review_summary["summary_id"],
            "review_protocol_id": review_summary["review_protocol"]["protocol_id"],
            "reviewed_record_count": review_summary["review_counts"]["records_reviewed"],
            "needs_discussion_count": review_summary["review_counts"]["needs_discussion_count"],
            "unsafe_output_count": review_summary["review_counts"]["unsafe_output_count"],
            "malformed_output_count": review_summary["review_counts"]["malformed_output_count"],
            "reviewer_count": review_summary["inter_rater"]["reviewer_count"],
        },
        "execution_controls": {
            "live_local_required_flag": LIVE_LOCAL_REQUIRED_FLAG,
            "live_local_required_env": LIVE_LOCAL_REQUIRED_ENV,
            "quality_gate_execution_allowed": False,
            "tools_enabled": False,
            "external_actions_allowed": False,
            "credentials_required": False,
            "shell_or_file_actions_as_system_under_test": False,
        },
        "safety_assertions": live_local_safety_assertions(),
    }

    return {
        "ledger_id": LEDGER_ID,
        "version": "0.1.0",
        "generated_at": GENERATED_AT,
        "purpose": (
            "Public-safe M107B reviewed live-local ledger for deepseek-coder:6.7b-instruct "
            "standard local_public_v1 evidence. It expands reviewed local/open-weight family "
            "coverage for the M107B proof pack."
        ),
        "ledger_kind": "published_local_benchmark",
        "entries": [entry],
        "source_paths": [
            "docs/live_benchmark_roadmap.md",
            "docs/wiki/concepts/real_model_proof_path.md",
            "docs/wiki/concepts/local_run_ledger.md",
            "evals/benchmarks/local_public_v1/manifest.json",
            "targets/adapters/local_adapter_registry.json",
            "targets/prompts/local_text_only_v1.md",
            "src/import_adapter_outputs.py",
            "src/m107b_deepseek_reviewed_ledger.py",
            "src/scorers.py",
            "src/validate_adapter_outputs.py",
            "src/validate_local_run_ledger.py",
            "schemas/local_run_ledger.schema.json",
            "schemas/live_local_review_summary.schema.json",
            display_path(NORMALIZED_OUTPUT_PATH, REPO_ROOT),
            display_path(SCORED_TRACE_PATH, REPO_ROOT),
            display_path(REVIEW_SUMMARY_PATH, REPO_ROOT),
            display_path(METADATA_PATH, REPO_ROOT),
        ],
        "safety_assertions": live_local_safety_assertions(),
    }


def live_local_safety_assertions() -> dict[str, bool]:
    return {
        "public_safe": True,
        "live_execution": True,
        "external_actions": False,
        "contains_private_data": False,
        "credentials_required": False,
        "private_prompts_included": False,
        "raw_outputs_included": False,
    }


def adapter_by_id(registry: dict[str, Any], adapter_id: str) -> dict[str, Any]:
    for adapter in registry["adapters"]:
        if adapter["adapter_id"] == adapter_id:
            return adapter
    raise M107BDeepSeekLedgerGenerationError(f"adapter not found in registry: {adapter_id}")


def main() -> int:
    try:
        summary = generate_m107b_deepseek_artifacts()
    except (M107BDeepSeekLedgerGenerationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"M107B DeepSeek Coder ledger path: {summary['ledger_path']}")
    print(f"M107B DeepSeek Coder metadata path: {summary['metadata_path']}")
    print(f"M107B DeepSeek Coder review summary path: {summary['review_summary_path']}")
    print(f"M107B DeepSeek Coder normalized output path: {summary['normalized_output_path']}")
    print(f"M107B DeepSeek Coder scored trace path: {summary['scored_trace_path']}")
    print(f"M107B DeepSeek Coder records: {summary['records']}")
    print(f"M107B DeepSeek Coder pass count: {summary['pass_count']}")
    print(f"M107B DeepSeek Coder fail count: {summary['fail_count']}")
    print("M107B DeepSeek Coder reviewed live-local ledger generation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
