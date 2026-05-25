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
from typing import Any, Callable

try:
    from .schema_validation_utils import validate_schema_value
except ImportError:  # pragma: no cover - exercised when run as a script.
    from schema_validation_utils import validate_schema_value


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
        super().__init__(f"{display_path(path)}:{line_number}: {reason}")


def display_path(path: Path) -> str:
    """Format a path relative to the repo when possible."""

    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


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


def validate_eval_case_record(record: dict[str, Any], source: str, line_number: int) -> None:
    """Validate one eval case record using the repo eval-case schema."""

    validate_record(record, load_json_file(EVAL_CASE_SCHEMA_PATH), Path(source), line_number)


def validate_trace_record(record: dict[str, Any], source: str, line_number: int) -> None:
    """Validate one scored trace record using the repo trace schema."""

    validate_record(record, load_json_file(TRACE_SCHEMA_PATH), Path(source), line_number)


def validate_all() -> tuple[int, int]:
    """Validate all current eval cases and scored traces."""

    eval_case_schema = load_json_file(EVAL_CASE_SCHEMA_PATH)
    trace_schema = load_json_file(TRACE_SCHEMA_PATH)

    eval_case_count = 0
    for path in EVAL_CASE_PATHS:
        eval_case_count += load_and_validate_jsonl(path, eval_case_schema)

    trace_count = 0
    for path in TRACE_PATHS:
        trace_count += load_and_validate_jsonl(path, trace_schema)

    return eval_case_count, trace_count


def validate_record(record: Any, schema: dict[str, Any], path: Path, line_number: int) -> None:
    """Validate one record against the supported schema subset."""

    if not isinstance(record, dict):
        raise ValidationError(path, line_number, "record must be a JSON object")

    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise ValidationError(path, line_number, "schema properties must be an object")

    validate_schema_value(record, schema, "", path, REPO_ROOT, validation_error_for_line(path, line_number))


def validation_error_for_line(path: Path, line_number: int) -> Callable[[str], ValidationError]:
    """Build line-aware validation errors for shared schema checks."""

    def build_error(reason: str) -> ValidationError:
        return ValidationError(path, line_number, reason)

    return build_error


def main() -> int:
    try:
        eval_case_count, trace_count = validate_all()
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"eval cases validated: {eval_case_count}")
    print(f"scored trace records validated: {trace_count}")
    print("schema validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
