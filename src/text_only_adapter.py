"""Normalize approved final text from a controlled text-only adapter run.

This M33 adapter handles final assistant/model text that was produced outside
the deterministic quality gate and already reviewed as public-safe. It does not
call providers, run local models, execute agents, use credentials, or perform
external actions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from run_eval import CASE_PATHS, load_cases
from target_registry import allowed_adapter_output_profiles
from trace_writer import write_jsonl
from validate_adapter_outputs import AdapterOutputValidationError, validate_jsonl_file
from validate_adapter_run_metadata import (
    AdapterRunMetadataValidationError,
    load_metadata,
    validate_metadata,
)


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_INPUT_FIELDS = {
    "case_id",
    "target_profile",
    "output_text",
    "review_status",
    "provenance",
}
OPTIONAL_INPUT_FIELDS = {
    "source_label",
    "notes",
    "metadata",
}
ALLOWED_INPUT_FIELDS = REQUIRED_INPUT_FIELDS | OPTIONAL_INPUT_FIELDS
REQUIRED_INPUT_PROVENANCE_FIELDS = {
    "public_safe",
    "live_execution",
    "external_actions",
    "contains_private_data",
    "credentials_required",
}
EXPECTED_APPROVED_PROVENANCE = {
    "public_safe": True,
    "live_execution": False,
    "external_actions": False,
    "contains_private_data": False,
    "credentials_required": False,
}


class TextOnlyAdapterError(Exception):
    """Controlled text-only adapter error."""


def adapt_text_only_outputs(metadata_path: Path, input_path: Path, output_path: Path) -> dict[str, Any]:
    """Convert approved final text records into normalized adapter-output JSONL."""

    validate_reviewed_output_path(output_path)
    validate_metadata(metadata_path)
    metadata = load_metadata(metadata_path)
    input_records = load_reviewed_text_records(input_path)
    validate_records_against_metadata(input_records, metadata, input_path)

    adapter_records = [
        adapter_output_from_reviewed_text(record, metadata, index)
        for index, record in enumerate(input_records, start=1)
    ]
    write_jsonl(adapter_records, output_path)

    try:
        validate_jsonl_file(output_path)
    except AdapterOutputValidationError as exc:
        raise TextOnlyAdapterError(f"normalized adapter output failed validation: {exc}") from exc

    return {
        "run_id": metadata["run_id"],
        "input_path": display_path(input_path),
        "output_path": display_path(output_path),
        "adapter_records_written": len(adapter_records),
    }


def load_reviewed_text_records(path: Path) -> list[dict[str, Any]]:
    """Load reviewer-approved final text records."""

    if not path.exists():
        raise TextOnlyAdapterError(f"{display_path(path)}: file does not exist")

    records = []
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise TextOnlyAdapterError(
                    f"{display_path(path)}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc
            validate_reviewed_text_record(record, path, line_number)
            records.append(record)

    if not records:
        raise TextOnlyAdapterError(f"{display_path(path)}: file contains no reviewed text records")
    return records


def validate_reviewed_text_record(record: Any, path: Path, line_number: int) -> None:
    """Validate one reviewed final text record before normalization."""

    context = f"{display_path(path)}:{line_number}"
    if not isinstance(record, dict):
        raise TextOnlyAdapterError(f"{context}: record must be an object")

    missing_fields = sorted(REQUIRED_INPUT_FIELDS - set(record))
    if missing_fields:
        raise TextOnlyAdapterError(f"{context}: missing required fields: {', '.join(missing_fields)}")

    unexpected_fields = sorted(set(record) - ALLOWED_INPUT_FIELDS)
    if unexpected_fields:
        raise TextOnlyAdapterError(f"{context}: unexpected fields: {', '.join(unexpected_fields)}")

    for field_name in ["case_id", "target_profile", "output_text", "review_status"]:
        require_non_empty_string(record[field_name], f"{context}.{field_name}")

    if record["review_status"] != "approved_public_safe":
        raise TextOnlyAdapterError(f"{context}.review_status must be approved_public_safe")

    validate_input_provenance(record["provenance"], f"{context}.provenance")

    for field_name in ["source_label", "notes"]:
        if field_name in record:
            require_non_empty_string(record[field_name], f"{context}.{field_name}")

    if "metadata" in record and not isinstance(record["metadata"], dict):
        raise TextOnlyAdapterError(f"{context}.metadata must be an object")


def validate_input_provenance(value: Any, context: str) -> None:
    """Require explicit public-safe provenance before normalization."""

    if not isinstance(value, dict):
        raise TextOnlyAdapterError(f"{context} must be an object")

    missing_fields = sorted(REQUIRED_INPUT_PROVENANCE_FIELDS - set(value))
    if missing_fields:
        raise TextOnlyAdapterError(f"{context} missing required fields: {', '.join(missing_fields)}")

    unexpected_fields = sorted(set(value) - REQUIRED_INPUT_PROVENANCE_FIELDS)
    if unexpected_fields:
        raise TextOnlyAdapterError(f"{context} unexpected fields: {', '.join(unexpected_fields)}")

    for field_name, expected_value in EXPECTED_APPROVED_PROVENANCE.items():
        if value[field_name] is not expected_value:
            expected_text = str(expected_value).lower()
            raise TextOnlyAdapterError(f"{context}.{field_name} must be {expected_text}")


def validate_records_against_metadata(
    records: list[dict[str, Any]],
    metadata: dict[str, Any],
    input_path: Path,
) -> None:
    """Validate reviewed text records against adapter run metadata."""

    known_case_ids = {str(case["case_id"]) for case in load_cases(CASE_PATHS)}
    metadata_case_ids = {str(case_id) for case_id in metadata["case_selection"]["case_ids"]}
    metadata_target_profile = str(metadata["target"]["target_profile"])
    allowed_profiles = allowed_adapter_output_profiles()
    seen_keys: set[tuple[str, str]] = set()

    for line_number, record in enumerate(records, start=1):
        context = f"{display_path(input_path)}:{line_number}"
        case_id = str(record["case_id"])
        target_profile = str(record["target_profile"])

        if case_id not in known_case_ids:
            raise TextOnlyAdapterError(f"{context}.case_id is not a known eval case: {case_id}")

        if case_id not in metadata_case_ids:
            expected = ", ".join(sorted(metadata_case_ids))
            raise TextOnlyAdapterError(f"{context}.case_id must be one of metadata case IDs: {expected}")

        if target_profile != metadata_target_profile:
            raise TextOnlyAdapterError(
                f"{context}.target_profile must match metadata target_profile {metadata_target_profile!r}"
            )

        if target_profile not in allowed_profiles:
            expected = ", ".join(allowed_profiles)
            raise TextOnlyAdapterError(f"{context}.target_profile must be one of: {expected}")

        key = (case_id, target_profile)
        if key in seen_keys:
            raise TextOnlyAdapterError(
                f"{context}: duplicate output for case_id={case_id!r}, target_profile={target_profile!r}"
            )
        seen_keys.add(key)


def adapter_output_from_reviewed_text(
    record: dict[str, Any],
    metadata: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    """Build one normalized adapter-output record."""

    adapter = metadata["adapter"]
    adapter_metadata = {
        "adapter_run_id": metadata["run_id"],
        "review_status": record["review_status"],
    }
    if "source_label" in record:
        adapter_metadata["source_label"] = record["source_label"]
    if "metadata" in record:
        adapter_metadata["source_metadata"] = record["metadata"]

    notes = "M33 controlled text-only adapter output; final text only, reviewed public-safe before normalization."
    if "notes" in record:
        notes = f"{notes} Reviewer notes: {record['notes']}"

    return {
        "record_id": f"{metadata['run_id']}-TEXT-ONLY-{index:03d}",
        "case_id": record["case_id"],
        "target_profile": record["target_profile"],
        "source_type": "saved_adapter_output",
        "adapter_name": adapter["adapter_name"],
        "adapter_version": adapter["adapter_version"],
        "created_at": metadata["created_at"],
        "output_text": record["output_text"],
        "provenance": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
        },
        "provenance_details": {
            "source_origin": "future_controlled_adapter_output",
            "execution_mode": "saved_output_only",
            "data_classification": "public_safe_fixture",
            "action_evidence": "output_text_only",
            "notes": notes,
        },
        "metadata": adapter_metadata,
    }


def validate_reviewed_output_path(path: Path) -> None:
    """Require a reviewed JSONL candidate filename."""

    if not path.name.endswith(".reviewed.jsonl"):
        raise TextOnlyAdapterError("normalized output path must end with .reviewed.jsonl")


def require_non_empty_string(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise TextOnlyAdapterError(f"{context} must be a string")
    if not value.strip():
        raise TextOnlyAdapterError(f"{context} must not be empty")
    return value


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize approved text-only adapter outputs.")
    parser.add_argument("--metadata", required=True, type=Path, help="Adapter run metadata JSON.")
    parser.add_argument("--input", required=True, type=Path, help="Reviewed final-text JSONL input.")
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Normalized adapter-output JSONL ending in .reviewed.jsonl.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        summary = adapt_text_only_outputs(args.metadata, args.input, args.output)
    except (
        TextOnlyAdapterError,
        AdapterRunMetadataValidationError,
        AdapterOutputValidationError,
        OSError,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"run_id: {summary['run_id']}")
    print(f"input path: {summary['input_path']}")
    print(f"output path: {summary['output_path']}")
    print(f"adapter records written: {summary['adapter_records_written']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
