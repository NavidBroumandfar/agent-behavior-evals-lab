"""Validate optional harness bridge decision plans.

This M37 validator checks a committed public-safe decision plan for whether a
future Hermes, OpenClaw, CLI-agent, or other runtime harness bridge is justified.
It reads local metadata only. It does not execute providers, local models,
OpenClaw, Hermes, CLI agents, shell commands, browser/email tools, networks, or
external actions.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from schema_validation_utils import display_path, load_json_object, validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN_PATH = REPO_ROOT / "traces/external/harness_bridge_plan.example.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/harness_bridge_plan.schema.json"

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
    "live_quality_gate_execution",
}
NON_HARNESS_PATHS = {
    "saved_transcript_replay",
    "normalized_adapter_output_import",
}
EXPECTED_RAW_OUTPUT_PATTERN = "traces/raw/*.local.jsonl"
EXPECTED_REVIEWED_OUTPUT_PATTERN = "traces/external/*.reviewed.jsonl"


class HarnessBridgePlanValidationError(Exception):
    """Harness bridge plan validation error with public-safe context."""


def validate_plan(
    plan_path: Path = DEFAULT_PLAN_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the harness bridge decision plan and return a summary."""

    schema = load_json_object(schema_path, "schema", repo_root, HarnessBridgePlanValidationError)
    plan = load_json_object(plan_path, "harness bridge plan", repo_root, HarnessBridgePlanValidationError)
    context = display_path(plan_path, repo_root)

    validate_schema_value(plan, schema, context, plan_path, repo_root, HarnessBridgePlanValidationError)
    validate_utc_timestamp(plan["created_at"], f"{context}.created_at")
    validate_evidence(plan["evidence"], plan_path, repo_root)
    validate_decision(plan, context)
    validate_bridge_contract(plan["bridge_contract"], f"{context}.bridge_contract")
    validate_quality_gate(plan["quality_gate"], f"{context}.quality_gate")
    validate_safety_assertions(plan["safety_assertions"], f"{context}.safety_assertions")
    validate_blocked_capabilities(plan["blocked_capabilities"], f"{context}.blocked_capabilities")

    return {
        "plan_path": context,
        "schema_path": display_path(schema_path, repo_root),
        "plan_id": str(plan["plan_id"]),
        "target_runtime": str(plan["target_runtime"]),
        "decision": str(plan["decision"]),
        "runtime_native_state_required": plan["runtime_native_state_required"],
        "evidence_count": len(plan["evidence"]),
        "preferred_path_count": len(plan["preferred_paths"]),
        "harness_execution_in_quality_gate": plan["quality_gate"]["harness_execution_in_quality_gate"],
    }


def validate_evidence(evidence_items: list[dict[str, Any]], plan_path: Path, repo_root: Path) -> None:
    """Validate evidence paths and duplicate IDs."""

    seen_ids: set[str] = set()
    for index, evidence in enumerate(evidence_items):
        context = f"{display_path(plan_path, repo_root)}.evidence[{index}]"
        evidence_id = str(evidence["evidence_id"])
        if evidence_id in seen_ids:
            raise HarnessBridgePlanValidationError(f"{context}.evidence_id duplicate value: {evidence_id}")
        seen_ids.add(evidence_id)

        evidence_path = require_existing_repo_path(evidence["path"], f"{context}.path", repo_root)
        if evidence_path.name.endswith(".local.jsonl"):
            raise HarnessBridgePlanValidationError(f"{context}.path must not reference local-only output")


def validate_decision(plan: dict[str, Any], context: str) -> None:
    """Validate M37 decision-rule semantics."""

    decision = str(plan["decision"])
    preferred_paths = {str(path) for path in plan["preferred_paths"]}
    runtime_native_state_required = plan["runtime_native_state_required"]

    if runtime_native_state_required is False and decision != "defer_harness_integration":
        raise HarnessBridgePlanValidationError(
            f"{context}.decision must be defer_harness_integration when runtime_native_state_required is false"
        )

    if decision == "defer_harness_integration" and not preferred_paths.intersection(NON_HARNESS_PATHS):
        expected = ", ".join(sorted(NON_HARNESS_PATHS))
        raise HarnessBridgePlanValidationError(
            f"{context}.preferred_paths must include at least one non-harness path: {expected}"
        )

    if decision != "defer_harness_integration" and "harness_bridge" not in preferred_paths:
        raise HarnessBridgePlanValidationError(
            f"{context}.preferred_paths must include harness_bridge when decision prepares a bridge"
        )


def validate_bridge_contract(contract: dict[str, Any], context: str) -> None:
    """Validate bridge contract safety flags and local-only path patterns."""

    if contract["raw_output_path_pattern"] != EXPECTED_RAW_OUTPUT_PATTERN:
        raise HarnessBridgePlanValidationError(
            f"{context}.raw_output_path_pattern must be {EXPECTED_RAW_OUTPUT_PATTERN!r}"
        )
    if contract["reviewed_output_path_pattern"] != EXPECTED_REVIEWED_OUTPUT_PATTERN:
        raise HarnessBridgePlanValidationError(
            f"{context}.reviewed_output_path_pattern must be {EXPECTED_REVIEWED_OUTPUT_PATTERN!r}"
        )

    expected_false_fields = [
        "external_actions",
        "credentials_required",
        "private_logs_allowed",
        "quality_gate_execution_allowed",
    ]
    for field_name in expected_false_fields:
        if contract[field_name] is not False:
            raise HarnessBridgePlanValidationError(f"{context}.{field_name} must be false")

    if contract["review_required_before_promotion"] is not True:
        raise HarnessBridgePlanValidationError(f"{context}.review_required_before_promotion must be true")


def validate_quality_gate(value: dict[str, Any], context: str) -> None:
    """Validate quality-gate exclusion of runtime execution."""

    if value["plan_validation_in_quality_gate"] is not True:
        raise HarnessBridgePlanValidationError(f"{context}.plan_validation_in_quality_gate must be true")
    if value["harness_execution_in_quality_gate"] is not False:
        raise HarnessBridgePlanValidationError(f"{context}.harness_execution_in_quality_gate must be false")


def validate_safety_assertions(value: dict[str, Any], context: str) -> None:
    """Validate public-safe committed plan assertions."""

    for field_name, expected_value in EXPECTED_SAFE_ASSERTIONS.items():
        if value[field_name] is not expected_value:
            raise HarnessBridgePlanValidationError(f"{context}.{field_name} must be {expected_value!r}")


def validate_blocked_capabilities(values: list[str], context: str) -> None:
    """Require all M37 blocked capability labels to stay explicit."""

    blocked = {str(value) for value in values}
    missing = sorted(REQUIRED_BLOCKED_CAPABILITIES - blocked)
    if missing:
        raise HarnessBridgePlanValidationError(
            f"{context} missing required blocked capabilities: {', '.join(missing)}"
        )


def validate_utc_timestamp(value: Any, context: str) -> None:
    """Validate fixed UTC timestamp shape and date validity."""

    if not isinstance(value, str) or not value.strip():
        raise HarnessBridgePlanValidationError(f"{context} must be a non-empty string")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise HarnessBridgePlanValidationError(f"{context} must be a valid UTC timestamp") from exc


def require_existing_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    """Resolve and require an existing repository-relative path."""

    if not isinstance(value, str) or not value.strip():
        raise HarnessBridgePlanValidationError(f"{context} must be a non-empty string")
    path = Path(value)
    if path.is_absolute():
        raise HarnessBridgePlanValidationError(f"{context} must be a repository-relative path")

    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise HarnessBridgePlanValidationError(f"{context} must stay within the repository") from exc

    if not resolved.exists():
        raise HarnessBridgePlanValidationError(f"{context} does not exist: {display_path(resolved, repo_root)}")
    return resolved


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate optional harness bridge decision plans.")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DEFAULT_PLAN_PATH,
        help="Harness bridge plan JSON path to validate.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help="Harness bridge plan JSON Schema path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = validate_plan(args.path, args.schema)
    except (HarnessBridgePlanValidationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"harness bridge plan path: {summary['plan_path']}")
    print(f"harness bridge plan schema: {summary['schema_path']}")
    print(f"plan id: {summary['plan_id']}")
    print(f"target runtime: {summary['target_runtime']}")
    print(f"decision: {summary['decision']}")
    print(f"runtime-native state required: {str(summary['runtime_native_state_required']).lower()}")
    print(f"evidence entries: {summary['evidence_count']}")
    print(f"preferred paths: {summary['preferred_path_count']}")
    print(f"harness execution in quality gate: {str(summary['harness_execution_in_quality_gate']).lower()}")
    print("harness bridge plan validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
