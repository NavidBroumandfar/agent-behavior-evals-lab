"""Validate the M57 live-local text-only run plan.

The committed plan is dry-run metadata only. This validator does not call
Ollama, local OpenAI-compatible servers, providers, agents, networks, tools,
credentials, or external actions.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from live_local_harness import (
    HARNESS_ID,
    LIVE_LOCAL_REQUIRED_ENV,
    LIVE_LOCAL_REQUIRED_FLAG,
    LiveLocalHarnessError,
    PROMPT_TEMPLATE_ID,
    REPO_ROOT,
    SUPPORTED_LIVE_ADAPTER_IDS,
    load_jsonl,
)
from schema_validation_utils import display_path, load_json_object, validate_schema_value
from validate_local_adapter_registry import DEFAULT_REGISTRY_PATH, validate_registry


DEFAULT_PLAN_PATH = REPO_ROOT / "traces/external/live_local_run_plan.example.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/live_local_run.schema.json"
EXPECTED_SAFE_ASSERTIONS = {
    "public_safe": True,
    "live_execution": False,
    "external_actions": False,
    "contains_private_data": False,
    "credentials_required": False,
}


class LiveLocalRunValidationError(Exception):
    """Live-local run plan validation error."""


def validate_live_local_run_plan(
    plan_path: Path = DEFAULT_PLAN_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the committed M57 dry-run plan and return a concise summary."""

    schema = load_json_object(schema_path, "schema", repo_root, LiveLocalRunValidationError)
    plan = load_json_object(plan_path, "live-local run plan", repo_root, LiveLocalRunValidationError)
    context = display_path(plan_path, repo_root)

    validate_schema_value(plan, schema, context, plan_path, repo_root, LiveLocalRunValidationError)
    validate_created_at(plan["created_at"], f"{context}.created_at")
    validate_plan_mode(plan, context)
    validate_adapter(plan["adapter"], context)
    validate_case_set(plan["case_set"], context, repo_root)
    validate_prompt_template(plan["prompt_template"], context)
    validate_outputs(plan["outputs"], context, repo_root)
    validate_execution_controls(plan["execution_controls"], context)
    validate_safety_assertions(plan["safety_assertions"], context)

    return {
        "plan_path": context,
        "schema_path": display_path(schema_path, repo_root),
        "run_id": str(plan["run_id"]),
        "adapter_id": str(plan["adapter"]["adapter_id"]),
        "model": str(plan["adapter"]["model"]),
        "case_set_id": str(plan["case_set"]["case_set_id"]),
        "benchmark_split": str(plan["case_set"]["benchmark_split"]),
        "case_count": int(plan["case_set"]["case_count"]),
        "mode": str(plan["mode"]),
    }


def validate_plan_mode(plan: dict[str, Any], context: str) -> None:
    if plan["mode"] != "plan_only":
        raise LiveLocalRunValidationError(f"{context}.mode must be plan_only for committed quality-gate metadata")
    if plan["harness_id"] != HARNESS_ID:
        raise LiveLocalRunValidationError(f"{context}.harness_id must equal {HARNESS_ID}")


def validate_adapter(adapter: dict[str, Any], context: str) -> None:
    adapter_context = f"{context}.adapter"
    registry_summary = validate_registry(DEFAULT_REGISTRY_PATH)
    registry_adapter_ids = set(registry_summary["adapter_ids"])
    if adapter["adapter_id"] not in SUPPORTED_LIVE_ADAPTER_IDS:
        raise LiveLocalRunValidationError(f"{adapter_context}.adapter_id must be a supported live-local adapter")
    if adapter["adapter_id"] not in registry_adapter_ids:
        raise LiveLocalRunValidationError(f"{adapter_context}.adapter_id must exist in the local adapter registry")
    if not str(adapter["endpoint"]).startswith(("http://127.0.0.1", "http://localhost")):
        raise LiveLocalRunValidationError(f"{adapter_context}.endpoint must use loopback")
    if int(adapter["parameters"]["timeout_seconds"]) <= 0:
        raise LiveLocalRunValidationError(f"{adapter_context}.parameters.timeout_seconds must be positive")


def validate_case_set(case_set: dict[str, Any], context: str, repo_root: Path) -> None:
    case_context = f"{context}.case_set"
    manifest_path = require_existing_repo_path(case_set["manifest_path"], f"{case_context}.manifest_path", repo_root)
    case_path = require_existing_repo_path(case_set["case_path"], f"{case_context}.case_path", repo_root)
    manifest = load_json_object(manifest_path, "local benchmark manifest", repo_root, LiveLocalRunValidationError)
    try:
        cases = load_jsonl(case_path)
    except LiveLocalHarnessError as exc:
        raise LiveLocalRunValidationError(str(exc)) from exc

    if case_set["case_set_id"] != manifest["case_set_id"]:
        raise LiveLocalRunValidationError(f"{case_context}.case_set_id must match manifest")
    if case_set["case_set_version"] != manifest["version"]:
        raise LiveLocalRunValidationError(f"{case_context}.case_set_version must match manifest")

    split = str(case_set["benchmark_split"])
    planned_case_ids = [str(case_id) for case_id in case_set["case_ids"]]
    if len(planned_case_ids) != int(case_set["case_count"]):
        raise LiveLocalRunValidationError(f"{case_context}.case_count must match case_ids length")

    cases_by_id = {str(case["case_id"]): case for case in cases}
    unknown_case_ids = sorted(set(planned_case_ids) - set(cases_by_id))
    if unknown_case_ids:
        raise LiveLocalRunValidationError(
            f"{case_context}.case_ids contains unknown IDs: {', '.join(unknown_case_ids)}"
        )
    wrong_split = [
        case_id for case_id in planned_case_ids if split not in cases_by_id[case_id]["benchmark_splits"]
    ]
    if wrong_split:
        raise LiveLocalRunValidationError(
            f"{case_context}.case_ids not in split {split}: {', '.join(wrong_split)}"
        )


def validate_prompt_template(prompt_template: dict[str, Any], context: str) -> None:
    prompt_context = f"{context}.prompt_template"
    if prompt_template["template_id"] != PROMPT_TEMPLATE_ID:
        raise LiveLocalRunValidationError(f"{prompt_context}.template_id must equal {PROMPT_TEMPLATE_ID}")
    if prompt_template["tools_enabled"] is not False:
        raise LiveLocalRunValidationError(f"{prompt_context}.tools_enabled must be false")


def validate_outputs(outputs: dict[str, Any], context: str, repo_root: Path) -> None:
    output_context = f"{context}.outputs"
    raw_path = require_repo_path(outputs["raw_output_path"], f"{output_context}.raw_output_path", repo_root)
    metadata_path = require_repo_path(outputs["run_metadata_path"], f"{output_context}.run_metadata_path", repo_root)
    normalized_path = require_repo_path(outputs["normalized_output_path"], f"{output_context}.normalized_output_path", repo_root)
    scored_path = require_repo_path(outputs["scored_trace_path"], f"{output_context}.scored_trace_path", repo_root)

    require_path_under(raw_path, repo_root / "traces/raw", f"{output_context}.raw_output_path")
    require_path_under(metadata_path, repo_root / "traces/raw", f"{output_context}.run_metadata_path")
    require_path_under(normalized_path, repo_root / "traces/external", f"{output_context}.normalized_output_path")
    require_path_under(scored_path, repo_root / "traces/scored", f"{output_context}.scored_trace_path")

    if outputs["raw_outputs_committable"] is not False:
        raise LiveLocalRunValidationError(f"{output_context}.raw_outputs_committable must be false")
    if outputs["normalized_outputs_require_review"] is not True:
        raise LiveLocalRunValidationError(f"{output_context}.normalized_outputs_require_review must be true")


def validate_execution_controls(controls: dict[str, Any], context: str) -> None:
    controls_context = f"{context}.execution_controls"
    if controls["live_local_required_flag"] != LIVE_LOCAL_REQUIRED_FLAG:
        raise LiveLocalRunValidationError(f"{controls_context}.live_local_required_flag must equal --live-local")
    if controls["live_local_required_env"] != LIVE_LOCAL_REQUIRED_ENV:
        raise LiveLocalRunValidationError(
            f"{controls_context}.live_local_required_env must equal {LIVE_LOCAL_REQUIRED_ENV}"
        )
    if controls["live_local_flag_present"] is not False:
        raise LiveLocalRunValidationError(f"{controls_context}.live_local_flag_present must be false in committed plan")
    if controls["live_local_env_present"] is not False:
        raise LiveLocalRunValidationError(f"{controls_context}.live_local_env_present must be false in committed plan")
    if controls["quality_gate_execution_allowed"] is not False:
        raise LiveLocalRunValidationError(f"{controls_context}.quality_gate_execution_allowed must be false")
    if controls["dry_run_plan_in_quality_gate"] is not True:
        raise LiveLocalRunValidationError(f"{controls_context}.dry_run_plan_in_quality_gate must be true")
    for field_name in [
        "tools_enabled",
        "external_actions_allowed",
        "credentials_required",
        "shell_or_file_actions_as_system_under_test",
    ]:
        if controls[field_name] is not False:
            raise LiveLocalRunValidationError(f"{controls_context}.{field_name} must be false")
    if controls["model_availability_check_required"] is not True:
        raise LiveLocalRunValidationError(f"{controls_context}.model_availability_check_required must be true")


def validate_safety_assertions(value: dict[str, Any], context: str) -> None:
    for field_name, expected_value in EXPECTED_SAFE_ASSERTIONS.items():
        if value[field_name] is not expected_value:
            raise LiveLocalRunValidationError(
                f"{context}.safety_assertions.{field_name} must equal {expected_value!r}"
            )


def validate_created_at(value: str, context: str) -> None:
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise LiveLocalRunValidationError(f"{context} must be a valid UTC timestamp") from exc


def require_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise LiveLocalRunValidationError(f"{context} must be a non-empty string")
    path = Path(value)
    if path.is_absolute():
        raise LiveLocalRunValidationError(f"{context} must be repository-relative")
    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise LiveLocalRunValidationError(f"{context} must stay within the repository") from exc
    return resolved


def require_existing_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    path = require_repo_path(value, context, repo_root)
    if not path.exists():
        raise LiveLocalRunValidationError(f"{context} does not exist: {display_path(path, repo_root)}")
    return path


def require_path_under(path: Path, parent: Path, context: str) -> None:
    try:
        path.relative_to(parent.resolve())
    except ValueError as exc:
        raise LiveLocalRunValidationError(f"{context} must stay under {display_path(parent.resolve())}") from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the M57 live-local dry-run plan.")
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_PLAN_PATH)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = validate_live_local_run_plan(args.path, args.schema)
    except (LiveLocalRunValidationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"live-local run plan path: {summary['plan_path']}")
    print(f"live-local run schema: {summary['schema_path']}")
    print(f"run id: {summary['run_id']}")
    print(f"mode: {summary['mode']}")
    print(f"adapter id: {summary['adapter_id']}")
    print(f"model: {summary['model']}")
    print(f"case set: {summary['case_set_id']}")
    print(f"split: {summary['benchmark_split']}")
    print(f"cases planned: {summary['case_count']}")
    print("live-local run plan validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
