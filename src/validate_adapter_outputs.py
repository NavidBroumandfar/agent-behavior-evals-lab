"""Validate normalized adapter-output JSONL fixtures.

This validates saved target-side adapter outputs before any importer or scorer
uses them. It is intentionally standard-library only and does not call models,
run adapters, execute OpenClaw, contact networks, or write files.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from schema_validation_utils import load_json_object, validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = REPO_ROOT / "traces/external/adapter_outputs.example.jsonl"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/adapter_output.schema.json"

EXPECTED_PROVENANCE_VALUES = {
    "public_safe": True,
    "external_actions": False,
    "contains_private_data": False,
}
LIVE_LOCAL_PROVENANCE_VALUES = {
    "source_origin": "live_local_model",
    "execution_mode": "live_local_text_only",
    "data_classification": "public_safe_fixture",
    "action_evidence": "output_text_only",
}
# Sandbox live runs: a local model drives mock tools; every call is recorded,
# nothing real executes.
LIVE_SANDBOX_PROVENANCE_VALUES = {
    "source_origin": "live_local_model",
    "execution_mode": "live_local_sandbox_tools",
    "data_classification": "public_safe_fixture",
    "action_evidence": "trace_or_transcript_reference",
}
LIVE_LOCAL_SOURCE_METADATA = {
    "harness_id": "live_local_text_only_harness",
    "tools_enabled": False,
    "external_actions_allowed": False,
    "credentials_required": False,
    "quality_gate_execution": False,
    "run_status": "succeeded",
}
LIVE_SANDBOX_SOURCE_METADATA = {
    "harness_id": "sandbox_tool_harness",
    "tools_enabled": True,
    "mock_tools_only": True,
    "external_actions_allowed": False,
    "quality_gate_execution": False,
    "run_status": "succeeded",
}

BLOCKED_CURRENT_EXECUTION_MODES = {
    "future_live_execution_not_in_quality_gate",
}
BLOCKED_CURRENT_DATA_CLASSIFICATIONS = {
    "private_or_sensitive_blocked",
}


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


def load_adapter_output_records(path: Path, *, allow_live_local: bool = False) -> list[dict[str, Any]]:
    """Load and validate normalized adapter-output records."""

    if not path.exists():
        raise AdapterOutputValidationError(path, 0, "file does not exist")

    schema = load_json_object(
        DEFAULT_SCHEMA_PATH,
        "schema",
        REPO_ROOT,
        validation_error_without_line(DEFAULT_SCHEMA_PATH),
    )
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

            validate_adapter_output_record(record, path, line_number, schema, allow_live_local=allow_live_local)
            records.append(record)

    if not records:
        raise AdapterOutputValidationError(path, 0, "file contains no adapter output records")

    return records


def validate_jsonl_file(path: Path, *, allow_live_local: bool = False) -> int:
    """Validate every normalized adapter-output record and return the count."""

    return len(load_adapter_output_records(path, allow_live_local=allow_live_local))


def validate_adapter_output_record(
    record: Any,
    path: Path,
    line_number: int,
    schema: dict[str, Any] | None = None,
    *,
    allow_live_local: bool = False,
) -> None:
    """Validate one normalized adapter-output record."""

    schema = schema if schema is not None else load_json_object(
        DEFAULT_SCHEMA_PATH,
        "schema",
        REPO_ROOT,
        validation_error_without_line(DEFAULT_SCHEMA_PATH),
    )
    validate_schema_value(record, schema, "", path, REPO_ROOT, validation_error_for_line(path, line_number))
    validate_created_at(record["created_at"], path, line_number)
    validate_provenance_safety(record["provenance"], path, line_number, allow_live_local=allow_live_local)
    if "provenance_details" in record:
        validate_provenance_detail_safety(record["provenance_details"], path, line_number)
    validate_live_local_detail_safety(record, path, line_number, allow_live_local=allow_live_local)


def validate_created_at(value: str, path: Path, line_number: int) -> None:
    """Validate the fixed UTC timestamp shape used by adapter-output fixtures."""

    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise AdapterOutputValidationError(path, line_number, "created_at must be a valid UTC timestamp") from exc


def validate_provenance_safety(
    value: dict[str, Any],
    path: Path,
    line_number: int,
    *,
    allow_live_local: bool,
) -> None:
    """Keep public-safe, non-live provenance explicit in the adapter-output validator."""

    for field_name in sorted(EXPECTED_PROVENANCE_VALUES):
        expected_value = EXPECTED_PROVENANCE_VALUES[field_name]
        if value[field_name] is not expected_value:
            expected_text = str(expected_value).lower()
            raise AdapterOutputValidationError(
                path,
                line_number,
                f"provenance.{field_name} must be {expected_text} for current gated fixtures",
            )
    if value["live_execution"] is True and not allow_live_local:
        raise AdapterOutputValidationError(
            path,
            line_number,
            "provenance.live_execution=true requires explicit --allow-live-local validation",
        )
    if value["live_execution"] is not True and value["live_execution"] is not False:
        raise AdapterOutputValidationError(path, line_number, "provenance.live_execution must be a boolean")


def validate_provenance_detail_safety(value: dict[str, Any], path: Path, line_number: int) -> None:
    """Keep future-only provenance detail blocks explicit in the adapter-output validator."""

    if value["execution_mode"] in BLOCKED_CURRENT_EXECUTION_MODES:
        raise AdapterOutputValidationError(
            path,
            line_number,
            "provenance_details.execution_mode=future_live_execution_not_in_quality_gate "
            "is future-only and rejected for current gated fixture validation",
        )

    if value["data_classification"] in BLOCKED_CURRENT_DATA_CLASSIFICATIONS:
        raise AdapterOutputValidationError(
            path,
            line_number,
            "provenance_details.data_classification=private_or_sensitive_blocked "
            "is future-only and rejected for current gated fixture validation",
        )


def validate_live_local_detail_safety(
    record: dict[str, Any],
    path: Path,
    line_number: int,
    *,
    allow_live_local: bool,
) -> None:
    """Require exact live-local provenance details when live execution is opted in."""

    if record["provenance"]["live_execution"] is not True:
        return
    if not allow_live_local:
        return
    if "provenance_details" not in record:
        raise AdapterOutputValidationError(path, line_number, "live-local adapter outputs must include provenance_details")

    details = record["provenance_details"]
    if details.get("execution_mode") == "live_local_sandbox_tools":
        expected_details = LIVE_SANDBOX_PROVENANCE_VALUES
        expected_metadata = LIVE_SANDBOX_SOURCE_METADATA
        mode_label = "live-sandbox"
    else:
        expected_details = LIVE_LOCAL_PROVENANCE_VALUES
        expected_metadata = LIVE_LOCAL_SOURCE_METADATA
        mode_label = "live-local"

    for field_name, expected_value in expected_details.items():
        if details[field_name] != expected_value:
            raise AdapterOutputValidationError(
                path,
                line_number,
                f"provenance_details.{field_name} must be {expected_value} for {mode_label} adapter outputs",
            )

    metadata = record.get("metadata", {})
    if not isinstance(metadata, dict):
        raise AdapterOutputValidationError(path, line_number, "metadata must be an object")
    source_metadata = metadata.get("source_metadata", {})
    if not isinstance(source_metadata, dict):
        raise AdapterOutputValidationError(path, line_number, "metadata.source_metadata must be an object")

    for field_name, expected_value in expected_metadata.items():
        if source_metadata.get(field_name) != expected_value:
            raise AdapterOutputValidationError(
                path,
                line_number,
                f"metadata.source_metadata.{field_name} must be {expected_value!r} for {mode_label} adapter outputs",
            )


def validation_error_for_line(path: Path, line_number: int) -> Callable[[str], AdapterOutputValidationError]:
    """Build line-aware adapter-output validation errors for shared schema checks."""

    def build_error(reason: str) -> AdapterOutputValidationError:
        return AdapterOutputValidationError(path, line_number, reason)

    return build_error


def validation_error_without_line(path: Path) -> Callable[[str], AdapterOutputValidationError]:
    """Build schema-file validation errors without a JSONL record line."""

    def build_error(reason: str) -> AdapterOutputValidationError:
        return AdapterOutputValidationError(path, 0, reason)

    return build_error


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate normalized adapter-output JSONL fixtures.")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_INPUT_PATH],
        help="Adapter-output JSONL files to validate.",
    )
    parser.add_argument(
        "--allow-live-local",
        action="store_true",
        help="Allow reviewed live-local text-only outputs outside the deterministic quality gate.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    total_count = 0
    try:
        for path in args.paths:
            total_count += validate_jsonl_file(path, allow_live_local=args.allow_live_local)
    except AdapterOutputValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"adapter output records validated: {total_count}")
    print("adapter output validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
