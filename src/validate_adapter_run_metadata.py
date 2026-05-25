"""Validate committed adapter run metadata examples.

M6 prepares for controlled, non-gated adapter experiments without adding live
execution. This validator checks public-safe metadata that describes planned or
saved-output adapter runs. It does not call providers, run local models,
execute agents, contact networks, read credentials, or validate private local
run output.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from run_eval import CASE_PATHS, load_cases
from schema_validation_utils import display_path, load_json_object, validate_schema_value
from target_registry import target_profile_names


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METADATA_PATH = REPO_ROOT / "traces/external/adapter_run_metadata.example.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/adapter_run_metadata.schema.json"

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


def load_metadata(path: Path) -> dict[str, Any]:
    """Load one adapter run metadata JSON file."""

    return load_json_object(path, "metadata", REPO_ROOT, AdapterRunMetadataValidationError)


def validate_metadata(path: Path = DEFAULT_METADATA_PATH, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Validate adapter run metadata and return a concise summary."""

    metadata = load_metadata(path)
    context = display_path(path, repo_root)
    schema = load_json_object(DEFAULT_SCHEMA_PATH, "schema", REPO_ROOT, AdapterRunMetadataValidationError)
    validate_schema_value(metadata, schema, context, path, repo_root, AdapterRunMetadataValidationError)
    validate_utc_timestamp(metadata["created_at"], f"{context}.created_at")

    validate_target(metadata["target"], f"{context}.target", repo_root)
    validate_case_selection(metadata["case_selection"], f"{context}.case_selection", repo_root)
    validate_sandbox(metadata["sandbox"], f"{context}.sandbox")
    validate_outputs(metadata["outputs"], f"{context}.outputs", repo_root)
    validate_review(metadata["review"], f"{context}.review", repo_root)
    validate_quality_gate(metadata["quality_gate"], f"{context}.quality_gate")
    validate_provenance(metadata["provenance"], f"{context}.provenance")

    adapter = metadata["adapter"]
    case_selection = metadata["case_selection"]
    return {
        "metadata_path": context,
        "run_id": str(metadata["run_id"]),
        "adapter_name": str(adapter["adapter_name"]),
        "target_profile": str(metadata["target"]["target_profile"]),
        "case_count": int(case_selection["case_count"]),
        "live_run_in_quality_gate": metadata["quality_gate"]["live_run_in_quality_gate"],
    }


def validate_target(value: Any, context: str, repo_root: Path) -> None:
    target_profile = str(value["target_profile"])
    if target_profile not in target_profile_names():
        allowed = ", ".join(target_profile_names())
        raise AdapterRunMetadataValidationError(f"{context}.target_profile must be one of: {allowed}")

    profile_path = require_existing_repo_path(value["profile_path"], f"{context}.profile_path", repo_root)
    if profile_path.suffix != ".md":
        raise AdapterRunMetadataValidationError(f"{context}.profile_path must point to a Markdown profile")


def validate_case_selection(value: Any, context: str, repo_root: Path) -> None:
    source_paths = [str(source_path) for source_path in value["case_source_paths"]]
    case_ids = [str(case_id) for case_id in value["case_ids"]]
    case_count = int(value["case_count"])

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
    if value["human_approval_required"] is not True:
        raise AdapterRunMetadataValidationError(f"{context}.human_approval_required must be true")

    for field_name in ["external_actions", "credentials_required"]:
        if value[field_name] is not False:
            raise AdapterRunMetadataValidationError(f"{context}.{field_name} must be false for M6 metadata")


def validate_outputs(value: Any, context: str, repo_root: Path) -> None:
    raw_output_path = require_repo_path(value["raw_output_path"], f"{context}.raw_output_path", repo_root)
    normalized_output_path = require_repo_path(
        value["normalized_output_path"],
        f"{context}.normalized_output_path",
        repo_root,
    )
    scored_trace_path = require_repo_path(value["scored_trace_path"], f"{context}.scored_trace_path", repo_root)

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
    checklist_path = require_existing_repo_path(
        value["approval_checklist_path"],
        f"{context}.approval_checklist_path",
        repo_root,
    )
    if checklist_path.suffix != ".md":
        raise AdapterRunMetadataValidationError(f"{context}.approval_checklist_path must point to Markdown")

    if value["sanitization_required"] is not True:
        raise AdapterRunMetadataValidationError(f"{context}.sanitization_required must be true")

    if value["raw_outputs_committable"] is not False:
        raise AdapterRunMetadataValidationError(f"{context}.raw_outputs_committable must be false")


def validate_quality_gate(value: Any, context: str) -> None:
    if value["metadata_validation_in_quality_gate"] is not True:
        raise AdapterRunMetadataValidationError(f"{context}.metadata_validation_in_quality_gate must be true")
    if value["live_run_in_quality_gate"] is not False:
        raise AdapterRunMetadataValidationError(f"{context}.live_run_in_quality_gate must be false")


def validate_provenance(value: Any, context: str) -> None:
    for field_name, expected_value in EXPECTED_PROVENANCE_VALUES.items():
        if value[field_name] is not expected_value:
            expected_text = str(expected_value).lower()
            raise AdapterRunMetadataValidationError(f"{context}.{field_name} must be {expected_text}")


def validate_utc_timestamp(value: Any, context: str) -> None:
    text = require_non_empty_string(value, context)
    if not UTC_TIMESTAMP_PATTERN.fullmatch(text):
        raise AdapterRunMetadataValidationError(f"{context} must use YYYY-MM-DDTHH:MM:SSZ UTC format")
    try:
        datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise AdapterRunMetadataValidationError(f"{context} must be a valid UTC timestamp") from exc


def require_non_empty_string(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise AdapterRunMetadataValidationError(f"{context} must be a string")
    if not value.strip():
        raise AdapterRunMetadataValidationError(f"{context} must not be empty")
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
