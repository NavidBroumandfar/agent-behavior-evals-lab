"""Validate committed adapter run metadata examples.

M6 prepares for controlled, non-gated adapter experiments without adding live
execution. This validator checks public-safe metadata that describes planned or
saved-output adapter runs. It does not call providers, run local models,
execute agents, contact networks, read credentials, or validate private local
run output.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from run_eval import CASE_PATHS, load_cases
from target_registry import target_profile_names


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METADATA_PATH = REPO_ROOT / "traces/external/adapter_run_metadata.example.json"

REQUIRED_TOP_LEVEL_FIELDS = {
    "metadata_id",
    "version",
    "created_at",
    "run_id",
    "status",
    "adapter",
    "target",
    "case_selection",
    "sandbox",
    "outputs",
    "review",
    "quality_gate",
    "provenance",
}

REQUIRED_ADAPTER_FIELDS = {
    "adapter_name",
    "adapter_version",
    "adapter_type",
}
REQUIRED_TARGET_FIELDS = {
    "target_profile",
    "profile_path",
}
REQUIRED_CASE_SELECTION_FIELDS = {
    "case_source_paths",
    "case_ids",
    "case_count",
}
REQUIRED_SANDBOX_FIELDS = {
    "execution_mode",
    "network_access",
    "tool_execution",
    "external_actions",
    "credentials_required",
    "human_approval_required",
    "risk_level",
}
REQUIRED_OUTPUT_FIELDS = {
    "raw_output_path",
    "normalized_output_path",
    "scored_trace_path",
    "commit_policy",
}
REQUIRED_REVIEW_FIELDS = {
    "approval_checklist_path",
    "sanitization_required",
    "raw_outputs_committable",
    "normalized_outputs_committable_after_review",
    "notes",
}
REQUIRED_QUALITY_GATE_FIELDS = {
    "metadata_validation_in_quality_gate",
    "live_run_in_quality_gate",
    "reason",
}
REQUIRED_PROVENANCE_FIELDS = {
    "public_safe",
    "live_execution",
    "external_actions",
    "contains_private_data",
    "credentials_required",
}

ALLOWED_STATUS_VALUES = {
    "planned_only",
    "dry_run_only",
    "saved_output_review_only",
}
ALLOWED_ADAPTER_TYPES = {
    "hosted_model_text_only",
    "local_model_text_only",
    "cli_agent_text_only",
    "saved_transcript_import",
    "dry_run_contract",
}
ALLOWED_EXECUTION_MODES = {
    "planned_non_gated_live_output",
    "dry_run_only",
    "saved_output_review_only",
}
ALLOWED_NETWORK_ACCESS = {
    "disabled_for_committed_example",
    "allowed_for_manual_collection_only",
    "not_applicable",
}
ALLOWED_TOOL_EXECUTION = {
    "none",
    "text_generation_only",
    "local_read_only",
    "external_actions_blocked",
}
ALLOWED_RISK_LEVELS = {
    "low",
    "medium",
    "high",
    "critical",
}
EXPECTED_PROVENANCE_VALUES = {
    "public_safe": True,
    "live_execution": False,
    "external_actions": False,
    "contains_private_data": False,
    "credentials_required": False,
}

UTC_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class AdapterRunMetadataValidationError(Exception):
    """Validation error for adapter run metadata."""


def display_path(path: Path, repo_root: Path = REPO_ROOT) -> str:
    """Format a path relative to the repository when possible."""

    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def load_metadata(path: Path) -> dict[str, Any]:
    """Load one adapter run metadata JSON file."""

    if not path.exists():
        raise AdapterRunMetadataValidationError(f"{display_path(path)}: file does not exist")

    try:
        with path.open("r", encoding="utf-8") as input_file:
            metadata = json.load(input_file)
    except json.JSONDecodeError as exc:
        raise AdapterRunMetadataValidationError(
            f"{display_path(path)}:{exc.lineno}: invalid JSON: {exc.msg}"
        ) from exc

    if not isinstance(metadata, dict):
        raise AdapterRunMetadataValidationError(f"{display_path(path)}: metadata must be a JSON object")
    return metadata


def validate_metadata(path: Path = DEFAULT_METADATA_PATH, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Validate adapter run metadata and return a concise summary."""

    metadata = load_metadata(path)
    context = display_path(path, repo_root)
    validate_required_object(metadata, REQUIRED_TOP_LEVEL_FIELDS, context)

    require_non_empty_string(metadata["metadata_id"], f"{context}.metadata_id")
    require_non_empty_string(metadata["version"], f"{context}.version")
    require_non_empty_string(metadata["run_id"], f"{context}.run_id")
    validate_utc_timestamp(metadata["created_at"], f"{context}.created_at")
    require_enum(metadata["status"], ALLOWED_STATUS_VALUES, f"{context}.status")

    validate_adapter(metadata["adapter"], f"{context}.adapter")
    validate_target(metadata["target"], f"{context}.target", repo_root)
    validate_case_selection(metadata["case_selection"], f"{context}.case_selection", repo_root)
    validate_sandbox(metadata["sandbox"], f"{context}.sandbox")
    validate_outputs(metadata["outputs"], f"{context}.outputs", repo_root)
    validate_review(metadata["review"], f"{context}.review", repo_root)
    validate_quality_gate(metadata["quality_gate"], f"{context}.quality_gate")
    validate_provenance(metadata["provenance"], f"{context}.provenance")

    return {
        "metadata_path": context,
        "run_id": str(metadata["run_id"]),
        "adapter_name": str(metadata["adapter"]["adapter_name"]),
        "target_profile": str(metadata["target"]["target_profile"]),
        "case_count": int(metadata["case_selection"]["case_count"]),
        "live_run_in_quality_gate": metadata["quality_gate"]["live_run_in_quality_gate"],
    }


def validate_adapter(value: Any, context: str) -> None:
    validate_required_object(value, REQUIRED_ADAPTER_FIELDS, context)
    require_non_empty_string(value["adapter_name"], f"{context}.adapter_name")
    require_non_empty_string(value["adapter_version"], f"{context}.adapter_version")
    require_enum(value["adapter_type"], ALLOWED_ADAPTER_TYPES, f"{context}.adapter_type")


def validate_target(value: Any, context: str, repo_root: Path) -> None:
    validate_required_object(value, REQUIRED_TARGET_FIELDS, context)
    target_profile = require_non_empty_string(value["target_profile"], f"{context}.target_profile")
    if target_profile not in target_profile_names():
        allowed = ", ".join(target_profile_names())
        raise AdapterRunMetadataValidationError(f"{context}.target_profile must be one of: {allowed}")

    profile_path = require_existing_repo_path(value["profile_path"], f"{context}.profile_path", repo_root)
    if profile_path.suffix != ".md":
        raise AdapterRunMetadataValidationError(f"{context}.profile_path must point to a Markdown profile")


def validate_case_selection(value: Any, context: str, repo_root: Path) -> None:
    validate_required_object(value, REQUIRED_CASE_SELECTION_FIELDS, context)
    source_paths = require_string_list(value["case_source_paths"], f"{context}.case_source_paths")
    case_ids = require_string_list(value["case_ids"], f"{context}.case_ids")
    case_count = require_non_negative_int(value["case_count"], f"{context}.case_count")

    if case_count != len(case_ids):
        raise AdapterRunMetadataValidationError(
            f"{context}.case_count must match the number of case_ids ({len(case_ids)})"
        )

    for index, source_path in enumerate(source_paths):
        resolved_path = require_existing_repo_path(source_path, f"{context}.case_source_paths[{index}]", repo_root)
        if resolved_path.suffix != ".jsonl":
            raise AdapterRunMetadataValidationError(f"{context}.case_source_paths[{index}] must point to JSONL")

    known_case_ids = {str(case["case_id"]) for case in load_cases(CASE_PATHS)}
    unknown_case_ids = sorted(set(case_ids) - known_case_ids)
    if unknown_case_ids:
        raise AdapterRunMetadataValidationError(
            f"{context}.case_ids contains unknown case IDs: {', '.join(unknown_case_ids)}"
        )


def validate_sandbox(value: Any, context: str) -> None:
    validate_required_object(value, REQUIRED_SANDBOX_FIELDS, context)
    require_enum(value["execution_mode"], ALLOWED_EXECUTION_MODES, f"{context}.execution_mode")
    require_enum(value["network_access"], ALLOWED_NETWORK_ACCESS, f"{context}.network_access")
    require_enum(value["tool_execution"], ALLOWED_TOOL_EXECUTION, f"{context}.tool_execution")
    require_enum(value["risk_level"], ALLOWED_RISK_LEVELS, f"{context}.risk_level")

    require_bool(value["human_approval_required"], f"{context}.human_approval_required")
    if value["human_approval_required"] is not True:
        raise AdapterRunMetadataValidationError(f"{context}.human_approval_required must be true")

    for field_name in ["external_actions", "credentials_required"]:
        require_bool(value[field_name], f"{context}.{field_name}")
        if value[field_name] is not False:
            raise AdapterRunMetadataValidationError(f"{context}.{field_name} must be false for M6 metadata")


def validate_outputs(value: Any, context: str, repo_root: Path) -> None:
    validate_required_object(value, REQUIRED_OUTPUT_FIELDS, context)
    raw_output_path = require_repo_path(value["raw_output_path"], f"{context}.raw_output_path", repo_root)
    normalized_output_path = require_repo_path(
        value["normalized_output_path"],
        f"{context}.normalized_output_path",
        repo_root,
    )
    scored_trace_path = require_repo_path(value["scored_trace_path"], f"{context}.scored_trace_path", repo_root)
    require_enum(
        value["commit_policy"],
        {"reviewed_public_safe_outputs_only"},
        f"{context}.commit_policy",
    )

    require_path_under(raw_output_path, repo_root / "traces/raw", f"{context}.raw_output_path")
    require_path_under(scored_trace_path, repo_root / "traces/scored", f"{context}.scored_trace_path")
    require_path_under(normalized_output_path, repo_root / "traces/external", f"{context}.normalized_output_path")

    for path, path_context in [
        (raw_output_path, f"{context}.raw_output_path"),
        (scored_trace_path, f"{context}.scored_trace_path"),
    ]:
        if not path.name.endswith(".local.jsonl"):
            raise AdapterRunMetadataValidationError(f"{path_context} must end with .local.jsonl")

    if normalized_output_path.name.endswith(".local.jsonl"):
        raise AdapterRunMetadataValidationError(
            f"{context}.normalized_output_path must describe a reviewed public-safe candidate, not a local file"
        )
    if not normalized_output_path.name.endswith(".reviewed.jsonl"):
        raise AdapterRunMetadataValidationError(
            f"{context}.normalized_output_path must end with .reviewed.jsonl"
        )


def validate_review(value: Any, context: str, repo_root: Path) -> None:
    validate_required_object(value, REQUIRED_REVIEW_FIELDS, context)
    checklist_path = require_existing_repo_path(
        value["approval_checklist_path"],
        f"{context}.approval_checklist_path",
        repo_root,
    )
    if checklist_path.suffix != ".md":
        raise AdapterRunMetadataValidationError(f"{context}.approval_checklist_path must point to Markdown")

    require_bool(value["sanitization_required"], f"{context}.sanitization_required")
    if value["sanitization_required"] is not True:
        raise AdapterRunMetadataValidationError(f"{context}.sanitization_required must be true")

    for field_name in ["raw_outputs_committable", "normalized_outputs_committable_after_review"]:
        require_bool(value[field_name], f"{context}.{field_name}")
    if value["raw_outputs_committable"] is not False:
        raise AdapterRunMetadataValidationError(f"{context}.raw_outputs_committable must be false")

    require_non_empty_string(value["notes"], f"{context}.notes")


def validate_quality_gate(value: Any, context: str) -> None:
    validate_required_object(value, REQUIRED_QUALITY_GATE_FIELDS, context)
    require_bool(value["metadata_validation_in_quality_gate"], f"{context}.metadata_validation_in_quality_gate")
    require_bool(value["live_run_in_quality_gate"], f"{context}.live_run_in_quality_gate")
    if value["metadata_validation_in_quality_gate"] is not True:
        raise AdapterRunMetadataValidationError(f"{context}.metadata_validation_in_quality_gate must be true")
    if value["live_run_in_quality_gate"] is not False:
        raise AdapterRunMetadataValidationError(f"{context}.live_run_in_quality_gate must be false")
    require_non_empty_string(value["reason"], f"{context}.reason")


def validate_provenance(value: Any, context: str) -> None:
    validate_required_object(value, REQUIRED_PROVENANCE_FIELDS, context)
    for field_name, expected_value in EXPECTED_PROVENANCE_VALUES.items():
        require_bool(value[field_name], f"{context}.{field_name}")
        if value[field_name] is not expected_value:
            expected_text = str(expected_value).lower()
            raise AdapterRunMetadataValidationError(f"{context}.{field_name} must be {expected_text}")


def validate_required_object(value: Any, required_fields: set[str], context: str) -> None:
    if not isinstance(value, dict):
        raise AdapterRunMetadataValidationError(f"{context} must be an object")

    missing_fields = sorted(required_fields - set(value))
    if missing_fields:
        raise AdapterRunMetadataValidationError(f"{context} missing required fields: {', '.join(missing_fields)}")

    unexpected_fields = sorted(set(value) - required_fields)
    if unexpected_fields:
        raise AdapterRunMetadataValidationError(f"{context} unexpected fields: {', '.join(unexpected_fields)}")


def validate_utc_timestamp(value: Any, context: str) -> None:
    text = require_non_empty_string(value, context)
    if not UTC_TIMESTAMP_PATTERN.fullmatch(text):
        raise AdapterRunMetadataValidationError(f"{context} must use YYYY-MM-DDTHH:MM:SSZ UTC format")
    try:
        datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise AdapterRunMetadataValidationError(f"{context} must be a valid UTC timestamp") from exc


def require_enum(value: Any, allowed_values: set[str], context: str) -> str:
    text = require_non_empty_string(value, context)
    if text not in allowed_values:
        allowed = ", ".join(sorted(allowed_values))
        raise AdapterRunMetadataValidationError(f"{context} must be one of: {allowed}")
    return text


def require_bool(value: Any, context: str) -> bool:
    if not isinstance(value, bool):
        raise AdapterRunMetadataValidationError(f"{context} must be a boolean")
    return value


def require_non_empty_string(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise AdapterRunMetadataValidationError(f"{context} must be a string")
    if not value.strip():
        raise AdapterRunMetadataValidationError(f"{context} must not be empty")
    return value


def require_string_list(value: Any, context: str) -> list[str]:
    if not isinstance(value, list):
        raise AdapterRunMetadataValidationError(f"{context} must be an array")
    if not value:
        raise AdapterRunMetadataValidationError(f"{context} must not be empty")

    values = []
    for index, item in enumerate(value):
        values.append(require_non_empty_string(item, f"{context}[{index}]"))
    return values


def require_non_negative_int(value: Any, context: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AdapterRunMetadataValidationError(f"{context} must be an integer")
    if value < 0:
        raise AdapterRunMetadataValidationError(f"{context} must be >= 0")
    return value


def require_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    raw_path = require_non_empty_string(value, context)
    path = Path(raw_path)
    if path.is_absolute():
        raise AdapterRunMetadataValidationError(f"{context} must be a repository-relative path")

    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise AdapterRunMetadataValidationError(f"{context} must stay within the repository") from exc
    return resolved


def require_existing_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    path = require_repo_path(value, context, repo_root)
    if not path.exists():
        raise AdapterRunMetadataValidationError(f"{context} does not exist: {display_path(path, repo_root)}")
    return path


def require_path_under(path: Path, parent: Path, context: str) -> None:
    try:
        path.relative_to(parent.resolve())
    except ValueError as exc:
        raise AdapterRunMetadataValidationError(
            f"{context} must stay under {display_path(parent.resolve())}"
        ) from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate adapter run metadata examples.")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_METADATA_PATH],
        help="Adapter run metadata JSON files to validate.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    summaries = []

    try:
        for path in args.paths:
            summaries.append(validate_metadata(path))
    except (AdapterRunMetadataValidationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"adapter run metadata files validated: {len(summaries)}")
    for summary in summaries:
        print(
            "metadata: "
            f"{summary['metadata_path']} "
            f"run_id={summary['run_id']} "
            f"adapter={summary['adapter_name']} "
            f"target={summary['target_profile']} "
            f"cases={summary['case_count']}"
        )
    print("adapter run metadata validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
