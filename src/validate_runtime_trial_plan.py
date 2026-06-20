"""Validate optional non-gated runtime trial plans.

This M44 validator checks committed public-safe runtime-trial planning
metadata. It does not execute OpenClaw, Hermes, CLI agents, providers, local
models, shell commands, browser/email tools, networks, file mutations, or
external actions.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from run_eval import load_cases
from schema_validation_utils import display_path, load_json_object, validate_schema_value
from validate_adapter_run_metadata import validate_metadata


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN_PATH = REPO_ROOT / "traces/external/non_gated_runtime_trial_plan.example.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/runtime_trial_plan.schema.json"

EXPECTED_SAFE_ASSERTIONS = {
    "public_safe": True,
    "live_execution": False,
    "external_actions": False,
    "contains_private_data": False,
    "credentials_required": False,
}
REQUIRED_BLOCKED_CAPABILITIES = {
    "network_collection",
    "credentials",
    "private_runtime_logs",
    "private_memory",
    "private_workspace_paths",
    "external_actions",
    "browser_email_actions",
    "file_mutation",
    "shell_execution",
    "provider_execution",
    "local_model_execution",
    "live_quality_gate_execution",
}
EXPECTED_FALSE_CONTROL_FIELDS = {
    "network_access",
    "credentials_required",
    "external_actions",
    "browser_email_actions",
    "shell_execution",
    "file_mutation",
    "private_logs_allowed",
}
EXPECTED_TRUE_CONTROL_FIELDS = {
    "manual_execution_required",
    "non_gated",
    "disposable",
    "review_required_before_promotion",
    "tools_disabled",
}


class RuntimeTrialPlanValidationError(Exception):
    """Runtime trial plan validation error with public-safe context."""


def validate_plan(
    plan_path: Path = DEFAULT_PLAN_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate a runtime trial plan and return a deterministic summary."""

    schema = load_json_object(schema_path, "schema", repo_root, RuntimeTrialPlanValidationError)
    plan = load_json_object(plan_path, "runtime trial plan", repo_root, RuntimeTrialPlanValidationError)
    context = display_path(plan_path, repo_root)

    validate_schema_value(plan, schema, context, plan_path, repo_root, RuntimeTrialPlanValidationError)
    validate_utc_timestamp(plan["created_at"], f"{context}.created_at")
    validate_prepared_prompt(plan["prepared_prompt"], f"{context}.prepared_prompt", repo_root)
    validate_adapter_metadata_reference(plan, context, repo_root)
    validate_procedure_path(plan["procedure_path"], f"{context}.procedure_path", repo_root)
    validate_trial_controls(plan["trial_controls"], f"{context}.trial_controls")
    validate_output_policy(plan["output_policy"], f"{context}.output_policy", repo_root)
    validate_promotion_path(plan["promotion_path"], f"{context}.promotion_path", repo_root)
    validate_quality_gate(plan["quality_gate"], f"{context}.quality_gate")
    validate_closeout_decision(plan["closeout_decision"], f"{context}.closeout_decision")
    validate_safety_assertions(plan["safety_assertions"], f"{context}.safety_assertions")
    validate_blocked_capabilities(plan["blocked_capabilities"], f"{context}.blocked_capabilities")

    return {
        "plan_path": context,
        "schema_path": display_path(schema_path, repo_root),
        "plan_id": str(plan["plan_id"]),
        "target_runtime": str(plan["target_runtime"]),
        "status": str(plan["status"]),
        "decision": str(plan["closeout_decision"]["decision"]),
        "runtime_native_evidence_needed": plan["closeout_decision"]["runtime_native_evidence_needed"],
        "case_id": str(plan["prepared_prompt"]["case_id"]),
        "runtime_execution_in_quality_gate": plan["quality_gate"]["runtime_execution_in_quality_gate"],
    }


def validate_prepared_prompt(value: dict[str, Any], context: str, repo_root: Path) -> None:
    """Require one public-safe committed eval case as the prepared prompt."""

    if value["prompt_count"] != 1:
        raise RuntimeTrialPlanValidationError(f"{context}.prompt_count must equal 1")
    if value["public_safe_prompt_only"] is not True:
        raise RuntimeTrialPlanValidationError(f"{context}.public_safe_prompt_only must be true")

    case_path = require_existing_repo_path(value["case_source_path"], f"{context}.case_source_path", repo_root)
    if case_path.suffix != ".jsonl":
        raise RuntimeTrialPlanValidationError(f"{context}.case_source_path must point to JSONL")

    source_case_ids = {
        str(case["case_id"])
        for case in load_cases([case_path])
        if str(case.get("case_id", "")).strip()
    }
    case_id = str(value["case_id"])
    if case_id not in source_case_ids:
        raise RuntimeTrialPlanValidationError(f"{context}.case_id is not in case_source_path: {case_id}")


def validate_adapter_metadata_reference(plan: dict[str, Any], context: str, repo_root: Path) -> None:
    """Validate and cross-check the referenced adapter run metadata."""

    metadata_path = require_existing_repo_path(
        plan["adapter_run_metadata_path"],
        f"{context}.adapter_run_metadata_path",
        repo_root,
    )
    metadata_summary = validate_metadata(metadata_path, repo_root)
    metadata = load_json_object(metadata_path, "adapter run metadata", repo_root, RuntimeTrialPlanValidationError)
    if metadata_summary["case_count"] != 1:
        raise RuntimeTrialPlanValidationError(f"{context}.adapter_run_metadata_path must select exactly one case")
    if metadata_summary["live_run_in_quality_gate"] is not False:
        raise RuntimeTrialPlanValidationError(f"{context}.adapter_run_metadata_path must keep live run out of gate")
    if metadata["case_selection"]["case_ids"] != [plan["prepared_prompt"]["case_id"]]:
        raise RuntimeTrialPlanValidationError(
            f"{context}.adapter_run_metadata_path case_ids must match prepared_prompt.case_id"
        )
    path_pairs = [
        ("raw_output_path", plan["output_policy"]["raw_output_path"], metadata["outputs"]["raw_output_path"]),
        ("reviewed_output_path", plan["output_policy"]["reviewed_output_path"], metadata["outputs"]["normalized_output_path"]),
        ("scored_trace_path", plan["output_policy"]["scored_trace_path"], metadata["outputs"]["scored_trace_path"]),
    ]
    for field_name, plan_path, metadata_path_value in path_pairs:
        if plan_path != metadata_path_value:
            raise RuntimeTrialPlanValidationError(
                f"{context}.adapter_run_metadata_path outputs.{field_name} must match output_policy.{field_name}"
            )


def validate_procedure_path(value: str, context: str, repo_root: Path) -> None:
    """Require the documented manual procedure to exist."""

    procedure_path = require_existing_repo_path(value, context, repo_root)
    if procedure_path.suffix != ".md":
        raise RuntimeTrialPlanValidationError(f"{context} must point to Markdown")
    text = procedure_path.read_text(encoding="utf-8")
    for required_phrase in [
        "Manual and non-gated",
        "Raw local files are not committable",
        "Promotion requires separate review notes",
    ]:
        if required_phrase not in text:
            raise RuntimeTrialPlanValidationError(f"{context} missing required procedure phrase: {required_phrase}")


def validate_trial_controls(value: dict[str, Any], context: str) -> None:
    """Require manual, disposable, no-tool, no-external-action trial controls."""

    for field_name in EXPECTED_TRUE_CONTROL_FIELDS:
        if value[field_name] is not True:
            raise RuntimeTrialPlanValidationError(f"{context}.{field_name} must be true")
    for field_name in EXPECTED_FALSE_CONTROL_FIELDS:
        if value[field_name] is not False:
            raise RuntimeTrialPlanValidationError(f"{context}.{field_name} must be false")


def validate_output_policy(value: dict[str, Any], context: str, repo_root: Path) -> None:
    """Validate local raw paths and reviewed candidate path conventions."""

    raw_output_path = require_repo_path(value["raw_output_path"], f"{context}.raw_output_path", repo_root)
    reviewed_output_path = require_repo_path(value["reviewed_output_path"], f"{context}.reviewed_output_path", repo_root)
    scored_trace_path = require_repo_path(value["scored_trace_path"], f"{context}.scored_trace_path", repo_root)

    require_path_under(raw_output_path, repo_root / "traces/raw", f"{context}.raw_output_path")
    require_path_under(reviewed_output_path, repo_root / "traces/external", f"{context}.reviewed_output_path")
    require_path_under(scored_trace_path, repo_root / "traces/scored", f"{context}.scored_trace_path")

    if not raw_output_path.name.endswith(".local.jsonl"):
        raise RuntimeTrialPlanValidationError(f"{context}.raw_output_path must end with .local.jsonl")
    if not scored_trace_path.name.endswith(".local.jsonl"):
        raise RuntimeTrialPlanValidationError(f"{context}.scored_trace_path must end with .local.jsonl")
    if not reviewed_output_path.name.endswith(".reviewed.jsonl"):
        raise RuntimeTrialPlanValidationError(f"{context}.reviewed_output_path must end with .reviewed.jsonl")
    if value["raw_outputs_committable"] is not False:
        raise RuntimeTrialPlanValidationError(f"{context}.raw_outputs_committable must be false")
    if value["reviewed_outputs_committable_after_validation"] is not False:
        raise RuntimeTrialPlanValidationError(
            f"{context}.reviewed_outputs_committable_after_validation must be false for a deferred trial"
        )


def validate_promotion_path(value: dict[str, Any], context: str, repo_root: Path) -> None:
    """Require promotion through existing reviewed-output validation paths."""

    validator_path = require_existing_repo_path(value["validator"], f"{context}.validator", repo_root)
    importer_path = require_existing_repo_path(value["importer"], f"{context}.importer", repo_root)
    if validator_path.suffix != ".py":
        raise RuntimeTrialPlanValidationError(f"{context}.validator must point to a Python script")
    if importer_path.suffix != ".py":
        raise RuntimeTrialPlanValidationError(f"{context}.importer must point to a Python script")
    if value["review_notes_required"] is not True:
        raise RuntimeTrialPlanValidationError(f"{context}.review_notes_required must be true")
    if value["deterministic_scoring_after_promotion"] is not True:
        raise RuntimeTrialPlanValidationError(f"{context}.deterministic_scoring_after_promotion must be true")


def validate_quality_gate(value: dict[str, Any], context: str) -> None:
    """Validate quality-gate exclusion of runtime and raw-output execution."""

    if value["plan_validation_in_quality_gate"] is not True:
        raise RuntimeTrialPlanValidationError(f"{context}.plan_validation_in_quality_gate must be true")
    if value["metadata_validation_in_quality_gate"] is not True:
        raise RuntimeTrialPlanValidationError(f"{context}.metadata_validation_in_quality_gate must be true")
    if value["runtime_execution_in_quality_gate"] is not False:
        raise RuntimeTrialPlanValidationError(f"{context}.runtime_execution_in_quality_gate must be false")
    if value["raw_output_validation_in_quality_gate"] is not False:
        raise RuntimeTrialPlanValidationError(f"{context}.raw_output_validation_in_quality_gate must be false")


def validate_closeout_decision(value: dict[str, Any], context: str) -> None:
    """Validate the M44 decision semantics."""

    decision = str(value["decision"])
    runtime_native_evidence_needed = value["runtime_native_evidence_needed"]
    if runtime_native_evidence_needed is False and decision != "defer_live_runtime_trial":
        raise RuntimeTrialPlanValidationError(
            f"{context}.decision must be defer_live_runtime_trial when runtime_native_evidence_needed is false"
        )


def validate_safety_assertions(value: dict[str, Any], context: str) -> None:
    """Validate public-safe committed plan assertions."""

    for field_name, expected_value in EXPECTED_SAFE_ASSERTIONS.items():
        if value[field_name] is not expected_value:
            raise RuntimeTrialPlanValidationError(f"{context}.{field_name} must be {expected_value!r}")


def validate_blocked_capabilities(values: list[str], context: str) -> None:
    """Require all M44 blocked capability labels to stay explicit."""

    blocked = {str(value) for value in values}
    missing = sorted(REQUIRED_BLOCKED_CAPABILITIES - blocked)
    if missing:
        raise RuntimeTrialPlanValidationError(
            f"{context} missing required blocked capabilities: {', '.join(missing)}"
        )


def validate_utc_timestamp(value: Any, context: str) -> None:
    """Validate fixed UTC timestamp shape and date validity."""

    if not isinstance(value, str) or not value.strip():
        raise RuntimeTrialPlanValidationError(f"{context} must be a non-empty string")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise RuntimeTrialPlanValidationError(f"{context} must be a valid UTC timestamp") from exc


def require_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    """Resolve and require a repository-relative path."""

    if not isinstance(value, str) or not value.strip():
        raise RuntimeTrialPlanValidationError(f"{context} must be a non-empty string")
    path = Path(value)
    if path.is_absolute():
        raise RuntimeTrialPlanValidationError(f"{context} must be a repository-relative path")

    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise RuntimeTrialPlanValidationError(f"{context} must stay within the repository") from exc
    return resolved


def require_existing_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    """Resolve and require an existing repository-relative path."""

    path = require_repo_path(value, context, repo_root)
    if not path.exists():
        raise RuntimeTrialPlanValidationError(f"{context} does not exist: {display_path(path, repo_root)}")
    return path


def require_path_under(path: Path, parent: Path, context: str) -> None:
    try:
        path.relative_to(parent.resolve())
    except ValueError as exc:
        raise RuntimeTrialPlanValidationError(
            f"{context} must stay under {display_path(parent.resolve())}"
        ) from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate optional non-gated runtime trial plans.")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DEFAULT_PLAN_PATH,
        help="Runtime trial plan JSON path to validate.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help="Runtime trial plan JSON Schema path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = validate_plan(args.path, args.schema)
    except (RuntimeTrialPlanValidationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"runtime trial plan path: {summary['plan_path']}")
    print(f"runtime trial plan schema: {summary['schema_path']}")
    print(f"plan id: {summary['plan_id']}")
    print(f"target runtime: {summary['target_runtime']}")
    print(f"status: {summary['status']}")
    print(f"decision: {summary['decision']}")
    print(f"case id: {summary['case_id']}")
    print(f"runtime-native evidence needed: {str(summary['runtime_native_evidence_needed']).lower()}")
    print(f"runtime execution in quality gate: {str(summary['runtime_execution_in_quality_gate']).lower()}")
    print("runtime trial plan validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
