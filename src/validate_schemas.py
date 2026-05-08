"""Validate current eval case and scored trace JSONL files.

This is a lightweight schema validator for the contracts used in this
repository. It intentionally implements only the JSON Schema subset needed for
the current files: required fields, no additional properties, primitive types,
string arrays, enums, minItems, and numeric bounds.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

EVAL_CASE_SCHEMA_PATH = REPO_ROOT / "schemas/eval_case.schema.json"
TRACE_SCHEMA_PATH = REPO_ROOT / "schemas/trace.schema.json"

EVAL_CASE_PATHS = [
    REPO_ROOT / "evals/cases/safe_task_cases.jsonl",
    REPO_ROOT / "evals/cases/approval_gate_cases.jsonl",
    REPO_ROOT / "evals/cases/refusal_cases.jsonl",
    REPO_ROOT / "evals/cases/uncertainty_cases.jsonl",
]

TRACE_PATHS = [
    REPO_ROOT / "traces/scored/baseline_mock_run.jsonl",
]


class ValidationError(Exception):
    """Validation error with file path and line number context."""

    def __init__(self, path: Path, line_number: int, reason: str):
        self.path = path
        self.line_number = line_number
        self.reason = reason
        super().__init__(f"{path.relative_to(REPO_ROOT)}:{line_number}: {reason}")


def load_json_file(path: Path) -> dict[str, Any]:
    """Load a local JSON file."""

    if not path.exists():
        raise ValidationError(path, 0, "file does not exist")

    try:
        with path.open("r", encoding="utf-8") as input_file:
            value = json.load(input_file)
    except json.JSONDecodeError as exc:
        raise ValidationError(path, exc.lineno, f"invalid JSON: {exc.msg}") from exc

    if not isinstance(value, dict):
        raise ValidationError(path, 1, "schema must be a JSON object")
    return value


def load_and_validate_jsonl(path: Path, schema: dict[str, Any]) -> int:
    """Validate every JSONL record in a file and return the record count."""

    if not path.exists():
        raise ValidationError(path, 0, "file does not exist")

    count = 0
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValidationError(path, line_number, f"invalid JSON: {exc.msg}") from exc

            validate_record(record, schema, path, line_number)
            count += 1

    return count


def validate_record(record: Any, schema: dict[str, Any], path: Path, line_number: int) -> None:
    """Validate one record against the supported schema subset."""

    if not isinstance(record, dict):
        raise ValidationError(path, line_number, "record must be a JSON object")

    required = set(schema.get("required", []))
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise ValidationError(path, line_number, "schema properties must be an object")

    missing_fields = sorted(required - set(record))
    if missing_fields:
        raise ValidationError(path, line_number, f"missing required fields: {', '.join(missing_fields)}")

    if schema.get("additionalProperties") is False:
        unexpected_fields = sorted(set(record) - set(properties))
        if unexpected_fields:
            raise ValidationError(path, line_number, f"unexpected fields: {', '.join(unexpected_fields)}")

    for field_name, field_schema in properties.items():
        if field_name in record:
            validate_field(record[field_name], field_schema, field_name, path, line_number)


def validate_field(
    value: Any,
    field_schema: dict[str, Any],
    field_name: str,
    path: Path,
    line_number: int,
) -> None:
    """Validate one field against the supported field constraints."""

    expected_type = field_schema.get("type")
    if expected_type and not _matches_type(value, expected_type):
        raise ValidationError(
            path,
            line_number,
            f"{field_name} must be {expected_type}, got {_type_name(value)}",
        )

    if "enum" in field_schema and value not in field_schema["enum"]:
        allowed = ", ".join(str(item) for item in field_schema["enum"])
        raise ValidationError(path, line_number, f"{field_name} must be one of: {allowed}")

    if expected_type == "array":
        validate_array_field(value, field_schema, field_name, path, line_number)

    if expected_type == "number":
        minimum = field_schema.get("minimum")
        maximum = field_schema.get("maximum")
        if minimum is not None and value < minimum:
            raise ValidationError(path, line_number, f"{field_name} must be >= {minimum}")
        if maximum is not None and value > maximum:
            raise ValidationError(path, line_number, f"{field_name} must be <= {maximum}")


def validate_array_field(
    value: Any,
    field_schema: dict[str, Any],
    field_name: str,
    path: Path,
    line_number: int,
) -> None:
    """Validate array constraints and item types."""

    if not isinstance(value, list):
        return

    min_items = field_schema.get("minItems")
    if min_items is not None and len(value) < min_items:
        raise ValidationError(path, line_number, f"{field_name} must contain at least {min_items} item(s)")

    item_schema = field_schema.get("items", {})
    item_type = item_schema.get("type") if isinstance(item_schema, dict) else None
    if item_type:
        for index, item in enumerate(value):
            if not _matches_type(item, item_type):
                raise ValidationError(
                    path,
                    line_number,
                    f"{field_name}[{index}] must be {item_type}, got {_type_name(item)}",
                )


def _matches_type(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return False


def _type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, (int, float)):
        return "number"
    if value is None:
        return "null"
    return type(value).__name__


def main() -> int:
    try:
        eval_case_schema = load_json_file(EVAL_CASE_SCHEMA_PATH)
        trace_schema = load_json_file(TRACE_SCHEMA_PATH)

        eval_case_count = 0
        for path in EVAL_CASE_PATHS:
            eval_case_count += load_and_validate_jsonl(path, eval_case_schema)

        trace_count = 0
        for path in TRACE_PATHS:
            trace_count += load_and_validate_jsonl(path, trace_schema)

    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"eval cases validated: {eval_case_count}")
    print(f"scored trace records validated: {trace_count}")
    print("schema validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
