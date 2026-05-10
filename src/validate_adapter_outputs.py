"""Validate normalized adapter-output JSONL fixtures.

This validates saved target-side adapter outputs before any importer or scorer
uses them. It is intentionally standard-library only and does not call models,
run adapters, execute OpenClaw, contact networks, or write files.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = REPO_ROOT / "traces/external/adapter_outputs.example.jsonl"

REQUIRED_FIELDS = {
    "record_id",
    "case_id",
    "target_profile",
    "source_type",
    "adapter_name",
    "created_at",
    "output_text",
    "provenance",
}
OPTIONAL_FIELDS = {
    "adapter_version",
    "metadata",
}
ALLOWED_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS

ALLOWED_SOURCE_TYPES = {
    "saved_adapter_output",
    "manual_adapter_output",
    "saved_transcript_output",
    "dry_run_adapter_output",
}

REQUIRED_PROVENANCE_FIELDS = {
    "public_safe",
    "live_execution",
    "external_actions",
    "contains_private_data",
}
EXPECTED_PROVENANCE_VALUES = {
    "public_safe": True,
    "live_execution": False,
    "external_actions": False,
    "contains_private_data": False,
}

UTC_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class AdapterOutputValidationError(Exception):
    """Validation error with file path and line number context."""

    def __init__(self, path: Path, line_number: int, reason: str):
        self.path = path
        self.line_number = line_number
        self.reason = reason
        super().__init__(f"{display_path(path)}:{line_number}: {reason}")


def display_path(path: Path) -> str:
    """Format a path relative to the repo when possible."""

    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_adapter_output_records(path: Path) -> list[dict[str, Any]]:
    """Load and validate normalized adapter-output records."""

    if not path.exists():
        raise AdapterOutputValidationError(path, 0, "file does not exist")

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise AdapterOutputValidationError(path, line_number, f"invalid JSON: {exc.msg}") from exc

            validate_adapter_output_record(record, path, line_number)
            records.append(record)

    if not records:
        raise AdapterOutputValidationError(path, 0, "file contains no adapter output records")

    return records


def validate_jsonl_file(path: Path) -> int:
    """Validate every normalized adapter-output record and return the count."""

    return len(load_adapter_output_records(path))


def validate_adapter_output_record(record: Any, path: Path, line_number: int) -> None:
    """Validate one normalized adapter-output record."""

    if not isinstance(record, dict):
        raise AdapterOutputValidationError(path, line_number, "record must be a JSON object")

    missing_fields = sorted(REQUIRED_FIELDS - set(record))
    if missing_fields:
        raise AdapterOutputValidationError(path, line_number, f"missing required fields: {', '.join(missing_fields)}")

    unexpected_fields = sorted(set(record) - ALLOWED_FIELDS)
    if unexpected_fields:
        raise AdapterOutputValidationError(path, line_number, f"unexpected fields: {', '.join(unexpected_fields)}")

    validate_non_empty_string_fields(record, path, line_number)
    validate_source_type(record["source_type"], path, line_number)
    validate_created_at(record["created_at"], path, line_number)
    validate_provenance(record["provenance"], path, line_number)

    if "metadata" in record and not isinstance(record["metadata"], dict):
        raise AdapterOutputValidationError(path, line_number, "metadata must be an object")


def validate_non_empty_string_fields(record: dict[str, Any], path: Path, line_number: int) -> None:
    """Validate string field types and reject empty required text values."""

    for field_name in [
        "record_id",
        "case_id",
        "target_profile",
        "source_type",
        "adapter_name",
        "created_at",
        "output_text",
    ]:
        value = record[field_name]
        if not isinstance(value, str):
            raise AdapterOutputValidationError(path, line_number, f"{field_name} must be a string")
        if not value.strip():
            raise AdapterOutputValidationError(path, line_number, f"{field_name} must not be empty")

    if "adapter_version" in record:
        value = record["adapter_version"]
        if not isinstance(value, str):
            raise AdapterOutputValidationError(path, line_number, "adapter_version must be a string")
        if not value.strip():
            raise AdapterOutputValidationError(path, line_number, "adapter_version must not be empty")


def validate_source_type(value: str, path: Path, line_number: int) -> None:
    """Validate source_type against the M4.1 allowed values."""

    if value not in ALLOWED_SOURCE_TYPES:
        allowed = ", ".join(sorted(ALLOWED_SOURCE_TYPES))
        raise AdapterOutputValidationError(path, line_number, f"source_type must be one of: {allowed}")


def validate_created_at(value: str, path: Path, line_number: int) -> None:
    """Validate the fixed UTC timestamp shape used by adapter-output fixtures."""

    if not UTC_TIMESTAMP_PATTERN.fullmatch(value):
        raise AdapterOutputValidationError(path, line_number, "created_at must use YYYY-MM-DDTHH:MM:SSZ UTC format")

    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise AdapterOutputValidationError(path, line_number, "created_at must be a valid UTC timestamp") from exc


def validate_provenance(value: Any, path: Path, line_number: int) -> None:
    """Validate public-safe, non-live provenance for M4.1 fixtures."""

    if not isinstance(value, dict):
        raise AdapterOutputValidationError(path, line_number, "provenance must be an object")

    missing_fields = sorted(REQUIRED_PROVENANCE_FIELDS - set(value))
    if missing_fields:
        raise AdapterOutputValidationError(
            path,
            line_number,
            f"provenance missing required fields: {', '.join(missing_fields)}",
        )

    unexpected_fields = sorted(set(value) - REQUIRED_PROVENANCE_FIELDS)
    if unexpected_fields:
        raise AdapterOutputValidationError(
            path,
            line_number,
            f"provenance unexpected fields: {', '.join(unexpected_fields)}",
        )

    for field_name in sorted(REQUIRED_PROVENANCE_FIELDS):
        field_value = value[field_name]
        if not isinstance(field_value, bool):
            raise AdapterOutputValidationError(path, line_number, f"provenance.{field_name} must be a boolean")

        expected_value = EXPECTED_PROVENANCE_VALUES[field_name]
        if field_value is not expected_value:
            expected_text = str(expected_value).lower()
            raise AdapterOutputValidationError(
                path,
                line_number,
                f"provenance.{field_name} must be {expected_text} for M4.1 fixtures",
            )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate normalized adapter-output JSONL fixtures.")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_INPUT_PATH],
        help="Adapter-output JSONL files to validate.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    total_count = 0
    try:
        for path in args.paths:
            total_count += validate_jsonl_file(path)
    except AdapterOutputValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"adapter output records validated: {total_count}")
    print("adapter output validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
