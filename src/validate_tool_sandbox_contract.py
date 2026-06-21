"""Validate the M61 sandboxed tool runtime contract.

This validator checks committed public-safe contract metadata and synthetic
tool-call summaries only. It does not launch agents, execute tools, read raw
runtime logs, call networks, use credentials, mutate files, or perform external
actions.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from schema_validation_utils import display_path, load_json_object, validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT_PATH = REPO_ROOT / "traces/external/tool_sandbox_contract.example.json"
DEFAULT_CONTRACT_SCHEMA_PATH = REPO_ROOT / "schemas/tool_sandbox_contract.schema.json"
DEFAULT_SUMMARY_SCHEMA_PATH = REPO_ROOT / "schemas/tool_call_summary.schema.json"

REQUIRED_TOOL_SURFACES = {
    "filesystem",
    "shell",
    "browser",
    "email",
    "network",
    "external_action",
}
REQUIRED_BLOCKED_CAPABILITIES = {
    "filesystem_read",
    "filesystem_write",
    "filesystem_delete",
    "shell_execution",
    "browser_navigation",
    "browser_form_submission",
    "email_read",
    "email_send",
    "network_collection",
    "network_mutation",
    "credentials",
    "private_runtime_logs",
    "private_memory",
    "private_workspace_paths",
    "external_actions",
    "payments",
    "purchases",
    "messaging",
    "deployments",
    "production_changes",
    "live_quality_gate_execution",
    "provider_execution",
    "local_model_execution",
}
EXPECTED_SAFE_ASSERTIONS = {
    "public_safe": True,
    "live_execution": False,
    "tool_execution": False,
    "external_actions": False,
    "contains_private_data": False,
    "credentials_required": False,
    "raw_private_logs": False,
}


class ToolSandboxContractValidationError(Exception):
    """Tool sandbox contract validation error with public-safe context."""


def validate_contract(
    contract_path: Path = DEFAULT_CONTRACT_PATH,
    contract_schema_path: Path = DEFAULT_CONTRACT_SCHEMA_PATH,
    summary_schema_path: Path = DEFAULT_SUMMARY_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the sandbox contract and referenced public-safe summaries."""

    contract_schema = load_json_object(
        contract_schema_path,
        "tool sandbox contract schema",
        repo_root,
        ToolSandboxContractValidationError,
    )
    summary_schema = load_json_object(
        summary_schema_path,
        "tool call summary schema",
        repo_root,
        ToolSandboxContractValidationError,
    )
    contract = load_json_object(contract_path, "tool sandbox contract", repo_root, ToolSandboxContractValidationError)
    context = display_path(contract_path, repo_root)

    validate_schema_value(
        contract,
        contract_schema,
        context,
        contract_path,
        repo_root,
        ToolSandboxContractValidationError,
    )
    validate_utc_timestamp(contract["created_at"], f"{context}.created_at")
    validate_tool_surfaces(contract["tool_surfaces"], f"{context}.tool_surfaces")
    validate_disposable_workspace(contract["disposable_workspace"], f"{context}.disposable_workspace")
    validate_default_deny_policy(contract["default_deny_policy"], f"{context}.default_deny_policy")
    validate_approval_policy(contract["approval_policy"], f"{context}.approval_policy")
    validate_summary_schema_reference(contract["summary_schema"], summary_schema_path, f"{context}.summary_schema", repo_root)
    validate_quality_gate(contract["quality_gate"], f"{context}.quality_gate")
    validate_safety_assertions(contract["safety_assertions"], f"{context}.safety_assertions")
    validate_blocked_capabilities(contract["blocked_capabilities"], f"{context}.blocked_capabilities")
    validate_public_safe_examples(contract["public_safe_examples"], f"{context}.public_safe_examples", repo_root)
    summary_count, summary_statuses = validate_summary_records(
        require_existing_repo_path(contract["summary_schema"]["example_path"], f"{context}.summary_schema.example_path", repo_root),
        summary_schema,
        str(contract["contract_id"]),
        repo_root,
    )

    return {
        "contract_path": context,
        "contract_schema_path": display_path(contract_schema_path, repo_root),
        "summary_schema_path": display_path(summary_schema_path, repo_root),
        "contract_id": str(contract["contract_id"]),
        "sandbox_mode": str(contract["sandbox_mode"]),
        "tool_surface_count": len(contract["tool_surfaces"]),
        "summary_count": summary_count,
        "summary_statuses": sorted(summary_statuses),
        "runtime_execution_in_quality_gate": contract["quality_gate"]["runtime_execution_in_quality_gate"],
        "tool_execution_in_quality_gate": contract["quality_gate"]["tool_execution_in_quality_gate"],
    }


def validate_tool_surfaces(values: list[dict[str, Any]], context: str) -> None:
    """Require all tool surfaces to be default-deny and metadata-only."""

    seen: set[str] = set()
    for index, surface_policy in enumerate(values):
        surface_context = f"{context}[{index}]"
        surface = str(surface_policy["surface"])
        if surface in seen:
            raise ToolSandboxContractValidationError(f"{surface_context}.surface duplicate value: {surface}")
        seen.add(surface)
        if surface_policy["default_policy"] != "deny":
            raise ToolSandboxContractValidationError(f"{surface_context}.default_policy must be deny")
        for field_name in [
            "execution_allowed",
            "raw_log_capture_allowed",
            "private_data_allowed",
            "external_side_effects_allowed",
        ]:
            if surface_policy[field_name] is not False:
                raise ToolSandboxContractValidationError(f"{surface_context}.{field_name} must be false")
        for field_name in ["blocked_action_recording", "approval_request_recording"]:
            if surface_policy[field_name] is not True:
                raise ToolSandboxContractValidationError(f"{surface_context}.{field_name} must be true")

    missing = sorted(REQUIRED_TOOL_SURFACES - seen)
    extra = sorted(seen - REQUIRED_TOOL_SURFACES)
    if missing:
        raise ToolSandboxContractValidationError(f"{context} missing required surfaces: {', '.join(missing)}")
    if extra:
        raise ToolSandboxContractValidationError(f"{context} contains unsupported surfaces: {', '.join(extra)}")


def validate_disposable_workspace(value: dict[str, Any], context: str) -> None:
    """Validate disposable workspace setup without requiring a real workspace."""

    expected_true_fields = ["required", "must_be_outside_repo", "delete_after_run"]
    expected_false_fields = ["committable"]
    for field_name in expected_true_fields:
        if value[field_name] is not True:
            raise ToolSandboxContractValidationError(f"{context}.{field_name} must be true")
    for field_name in expected_false_fields:
        if value[field_name] is not False:
            raise ToolSandboxContractValidationError(f"{context}.{field_name} must be false")
    if not str(value["root_pattern"]).startswith("system_temp_directory/"):
        raise ToolSandboxContractValidationError(f"{context}.root_pattern must use system_temp_directory/")
    if str(value["allowed_artifact_pattern"]) != "traces/raw/tool_runtime_*.local.jsonl":
        raise ToolSandboxContractValidationError(
            f"{context}.allowed_artifact_pattern must be traces/raw/tool_runtime_*.local.jsonl"
        )


def validate_default_deny_policy(value: dict[str, Any], context: str) -> None:
    """Require the default sandbox to deny real actions."""

    for field_name in [
        "unknown_tools_denied",
        "deny_without_explicit_allow",
        "approval_requests_recordable",
        "blocked_actions_recordable",
        "fake_completion_claims_forbidden",
    ]:
        if value[field_name] is not True:
            raise ToolSandboxContractValidationError(f"{context}.{field_name} must be true")
    if value["real_actions_allowed_by_default"] is not False:
        raise ToolSandboxContractValidationError(f"{context}.real_actions_allowed_by_default must be false")


def validate_approval_policy(value: dict[str, Any], context: str) -> None:
    """Require approval requests to be recordable without granting execution."""

    expected_true_fields = [
        "approval_can_be_requested",
        "approval_events_are_summaries_only",
        "approval_request_must_name_surface",
        "approval_request_must_name_intended_action",
    ]
    for field_name in expected_true_fields:
        if value[field_name] is not True:
            raise ToolSandboxContractValidationError(f"{context}.{field_name} must be true")
    if value["approval_grants_execution"] is not False:
        raise ToolSandboxContractValidationError(f"{context}.approval_grants_execution must be false")


def validate_summary_schema_reference(
    value: dict[str, Any],
    summary_schema_path: Path,
    context: str,
    repo_root: Path,
) -> None:
    """Validate summary schema and example path references."""

    schema_path = require_existing_repo_path(value["schema_path"], f"{context}.schema_path", repo_root)
    example_path = require_existing_repo_path(value["example_path"], f"{context}.example_path", repo_root)
    if schema_path.resolve() != summary_schema_path.resolve():
        raise ToolSandboxContractValidationError(f"{context}.schema_path must match the validator summary schema")
    if example_path.suffix != ".jsonl":
        raise ToolSandboxContractValidationError(f"{context}.example_path must point to JSONL")
    if value["summary_contains_raw_private_logs"] is not False:
        raise ToolSandboxContractValidationError(f"{context}.summary_contains_raw_private_logs must be false")
    if value["summary_score_ready"] is not True:
        raise ToolSandboxContractValidationError(f"{context}.summary_score_ready must be true")


def validate_quality_gate(value: dict[str, Any], context: str) -> None:
    """Validate that the quality gate only checks schemas and examples."""

    if value["contract_validation_in_quality_gate"] is not True:
        raise ToolSandboxContractValidationError(f"{context}.contract_validation_in_quality_gate must be true")
    if value["summary_validation_in_quality_gate"] is not True:
        raise ToolSandboxContractValidationError(f"{context}.summary_validation_in_quality_gate must be true")
    for field_name in [
        "runtime_execution_in_quality_gate",
        "tool_execution_in_quality_gate",
        "raw_log_validation_in_quality_gate",
    ]:
        if value[field_name] is not False:
            raise ToolSandboxContractValidationError(f"{context}.{field_name} must be false")


def validate_safety_assertions(value: dict[str, Any], context: str) -> None:
    """Validate public-safe safety assertions."""

    for field_name, expected_value in EXPECTED_SAFE_ASSERTIONS.items():
        if value[field_name] is not expected_value:
            raise ToolSandboxContractValidationError(f"{context}.{field_name} must be {expected_value!r}")


def validate_blocked_capabilities(values: list[str], context: str) -> None:
    """Require explicit default-deny blocked capabilities."""

    blocked = {str(value) for value in values}
    missing = sorted(REQUIRED_BLOCKED_CAPABILITIES - blocked)
    if missing:
        raise ToolSandboxContractValidationError(
            f"{context} missing required blocked capabilities: {', '.join(missing)}"
        )


def validate_public_safe_examples(values: list[dict[str, Any]], context: str, repo_root: Path) -> None:
    """Validate that example artifact paths exist and stay public-safe."""

    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    for index, example in enumerate(values):
        example_context = f"{context}[{index}]"
        example_id = str(example["example_id"])
        example_path = str(example["path"])
        if example_id in seen_ids:
            raise ToolSandboxContractValidationError(f"{example_context}.example_id duplicate value: {example_id}")
        if example_path in seen_paths:
            raise ToolSandboxContractValidationError(f"{example_context}.path duplicate value: {example_path}")
        seen_ids.add(example_id)
        seen_paths.add(example_path)
        require_existing_repo_path(example_path, f"{example_context}.path", repo_root)


def validate_summary_records(
    summary_path: Path,
    summary_schema: dict[str, Any],
    contract_id: str,
    repo_root: Path,
) -> tuple[int, set[str]]:
    """Validate public-safe tool-call summary JSONL records."""

    seen_ids: set[str] = set()
    statuses: set[str] = set()
    approval_requested = False
    blocked_recorded = False
    count = 0

    with summary_path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            context = f"{display_path(summary_path, repo_root)}:{line_number}"
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ToolSandboxContractValidationError(f"{context}: invalid JSON: {exc.msg}") from exc
            validate_schema_value(record, summary_schema, context, summary_path, repo_root, ToolSandboxContractValidationError)
            validate_summary_record(record, contract_id, context, repo_root)
            summary_id = str(record["summary_id"])
            if summary_id in seen_ids:
                raise ToolSandboxContractValidationError(f"{context}.summary_id duplicate value: {summary_id}")
            seen_ids.add(summary_id)
            statuses.add(str(record["action_status"]))
            approval_requested = approval_requested or bool(record["approval_request"]["requested"])
            blocked_recorded = blocked_recorded or record["action_status"] == "blocked_by_default_policy"
            count += 1

    if count == 0:
        raise ToolSandboxContractValidationError(f"{display_path(summary_path, repo_root)} must contain records")
    if not blocked_recorded:
        raise ToolSandboxContractValidationError(f"{display_path(summary_path, repo_root)} must include a blocked action")
    if not approval_requested:
        raise ToolSandboxContractValidationError(f"{display_path(summary_path, repo_root)} must include an approval request")
    return count, statuses


def validate_summary_record(record: dict[str, Any], contract_id: str, context: str, repo_root: Path) -> None:
    """Validate one summary record's safety semantics."""

    validate_utc_timestamp(record["created_at"], f"{context}.created_at")
    if record["contract_id"] != contract_id:
        raise ToolSandboxContractValidationError(f"{context}.contract_id must equal {contract_id}")
    if record["raw_private_log_included"] is not False:
        raise ToolSandboxContractValidationError(f"{context}.raw_private_log_included must be false")
    if record["score_ready"] is not True:
        raise ToolSandboxContractValidationError(f"{context}.score_ready must be true")
    for side_effect_name, side_effect_value in record["side_effects"].items():
        if side_effect_value is not False:
            raise ToolSandboxContractValidationError(f"{context}.side_effects.{side_effect_name} must be false")
    validate_safety_assertions(record["safety_assertions"], f"{context}.safety_assertions")
    source_path = require_existing_repo_path(record["source_evidence"]["source_path"], f"{context}.source_path", repo_root)
    if source_path.name.endswith(".local.jsonl"):
        raise ToolSandboxContractValidationError(f"{context}.source_path must not reference local-only raw output")
    if record["source_evidence"]["raw_log_path"] != "not_committed":
        raise ToolSandboxContractValidationError(f"{context}.raw_log_path must be not_committed")

    action_status = str(record["action_status"])
    approval = record["approval_request"]
    if action_status == "approval_requested_not_executed":
        if approval["requested"] is not True or approval["status"] != "requested_not_granted":
            raise ToolSandboxContractValidationError(f"{context}.approval_request must record requested_not_granted")
        if not str(approval["scope_summary"]).strip():
            raise ToolSandboxContractValidationError(f"{context}.approval_request.scope_summary must not be empty")
        if record["policy_decision"] != "approval_required":
            raise ToolSandboxContractValidationError(f"{context}.policy_decision must be approval_required")
    if action_status == "blocked_by_default_policy":
        if approval["requested"] is not False or approval["status"] != "not_requested":
            raise ToolSandboxContractValidationError(f"{context}.approval_request must record not_requested")
        if record["policy_decision"] != "deny":
            raise ToolSandboxContractValidationError(f"{context}.policy_decision must be deny")


def validate_utc_timestamp(value: Any, context: str) -> None:
    """Validate fixed UTC timestamp shape and date validity."""

    if not isinstance(value, str) or not value.strip():
        raise ToolSandboxContractValidationError(f"{context} must be a non-empty string")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ToolSandboxContractValidationError(f"{context} must be a valid UTC timestamp") from exc


def require_existing_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    """Resolve and require an existing repository-relative path."""

    if not isinstance(value, str) or not value.strip():
        raise ToolSandboxContractValidationError(f"{context} must be a non-empty string")
    path = Path(value)
    if path.is_absolute():
        raise ToolSandboxContractValidationError(f"{context} must be a repository-relative path")

    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ToolSandboxContractValidationError(f"{context} must stay within the repository") from exc

    if not resolved.exists():
        raise ToolSandboxContractValidationError(f"{context} does not exist: {display_path(resolved, repo_root)}")
    return resolved


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the M61 sandboxed tool runtime contract.")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DEFAULT_CONTRACT_PATH,
        help="Tool sandbox contract JSON path to validate.",
    )
    parser.add_argument(
        "--contract-schema",
        type=Path,
        default=DEFAULT_CONTRACT_SCHEMA_PATH,
        help="Tool sandbox contract JSON Schema path.",
    )
    parser.add_argument(
        "--summary-schema",
        type=Path,
        default=DEFAULT_SUMMARY_SCHEMA_PATH,
        help="Tool call summary JSON Schema path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = validate_contract(args.path, args.contract_schema, args.summary_schema)
    except (ToolSandboxContractValidationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"tool sandbox contract path: {summary['contract_path']}")
    print(f"tool sandbox contract schema: {summary['contract_schema_path']}")
    print(f"tool call summary schema: {summary['summary_schema_path']}")
    print(f"contract id: {summary['contract_id']}")
    print(f"sandbox mode: {summary['sandbox_mode']}")
    print(f"tool surfaces: {summary['tool_surface_count']}")
    print(f"tool summaries: {summary['summary_count']}")
    print(f"summary statuses: {', '.join(summary['summary_statuses'])}")
    print(f"runtime execution in quality gate: {str(summary['runtime_execution_in_quality_gate']).lower()}")
    print(f"tool execution in quality gate: {str(summary['tool_execution_in_quality_gate']).lower()}")
    print("tool sandbox contract validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
