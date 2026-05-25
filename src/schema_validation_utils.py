"""Shared local JSON Schema subset validation helpers.

These helpers intentionally support only the schema features used by the
repository's deterministic local manifest validators. They read local JSON files
and validate in-memory values only; they do not generate artifacts, call
networks, execute tools, or mutate files.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, TypeVar


ErrorT = TypeVar("ErrorT", bound=Exception)
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]


def display_path(path: Path, repo_root: Path = DEFAULT_REPO_ROOT) -> str:
    """Format a path relative to the repo when possible."""

    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def load_json_object(path: Path, label: str, repo_root: Path, error_type: type[ErrorT]) -> dict[str, Any]:
    """Load a JSON object from disk, raising the caller's validation error type."""

    if not path.exists():
        raise error_type(f"{display_path(path, repo_root)}: {label} does not exist")

    try:
        with path.open("r", encoding="utf-8") as input_file:
            value = json.load(input_file)
    except json.JSONDecodeError as exc:
        raise error_type(f"{display_path(path, repo_root)}:{exc.lineno}: invalid JSON: {exc.msg}") from exc

    if not isinstance(value, dict):
        raise error_type(f"{display_path(path, repo_root)}: {label} must be a JSON object")
    return value


def validate_schema_value(
    value: Any,
    schema: dict[str, Any],
    context: str,
    path: Path,
    repo_root: Path,
    error_type: type[ErrorT],
) -> None:
    """Validate a value against the repository's supported JSON Schema subset."""

    expected_type = schema.get("type")
    if expected_type is not None and not matches_type(value, expected_type):
        raise error_type(f"{context} must be {expected_type}, got {type_name(value)}")

    if "const" in schema and value != schema["const"]:
        raise error_type(f"{context} must equal {schema['const']!r}")

    if "enum" in schema and value not in schema["enum"]:
        allowed = ", ".join(str(item) for item in schema["enum"])
        raise error_type(f"{context} must be one of: {allowed}")

    if isinstance(value, dict):
        validate_object(value, schema, context, path, repo_root, error_type)
    if isinstance(value, list):
        validate_array(value, schema, context, path, repo_root, error_type)
    if isinstance(value, str):
        validate_string(value, schema, context, error_type)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        validate_number(value, schema, context, error_type)


def validate_object(
    value: dict[str, Any],
    schema: dict[str, Any],
    context: str,
    path: Path,
    repo_root: Path,
    error_type: type[ErrorT],
) -> None:
    properties = schema.get("properties", {})
    if properties is not None and not isinstance(properties, dict):
        raise error_type(f"{display_path(path, repo_root)} schema properties must be an object")

    required = set(schema.get("required", []))
    missing_fields = sorted(required - set(value))
    if missing_fields:
        raise error_type(f"{context}: missing required fields: {', '.join(missing_fields)}")

    additional_properties = schema.get("additionalProperties", True)
    if additional_properties is False:
        unexpected_fields = sorted(set(value) - set(properties))
        if unexpected_fields:
            raise error_type(f"{context}: unexpected fields: {', '.join(unexpected_fields)}")

    for field_name, field_schema in properties.items():
        if field_name in value:
            validate_schema_value(
                value[field_name],
                field_schema,
                f"{context}.{field_name}",
                path,
                repo_root,
                error_type,
            )

    if isinstance(additional_properties, dict):
        for field_name in sorted(set(value) - set(properties)):
            validate_schema_value(
                value[field_name],
                additional_properties,
                f"{context}.{field_name}",
                path,
                repo_root,
                error_type,
            )


def validate_array(
    value: list[Any],
    schema: dict[str, Any],
    context: str,
    path: Path,
    repo_root: Path,
    error_type: type[ErrorT],
) -> None:
    min_items = schema.get("minItems")
    if min_items is not None and len(value) < min_items:
        raise error_type(f"{context} must contain at least {min_items} item(s)")

    item_schema = schema.get("items")
    if isinstance(item_schema, dict):
        for index, item in enumerate(value):
            validate_schema_value(item, item_schema, f"{context}[{index}]", path, repo_root, error_type)


def validate_string(value: str, schema: dict[str, Any], context: str, error_type: type[ErrorT]) -> None:
    min_length = schema.get("minLength")
    if min_length is not None and len(value) < min_length:
        raise error_type(f"{context} must contain at least {min_length} character(s)")

    pattern = schema.get("pattern")
    if pattern is not None and re.fullmatch(str(pattern), value) is None:
        raise error_type(f"{context} must match pattern {pattern!r}")


def validate_number(value: int | float, schema: dict[str, Any], context: str, error_type: type[ErrorT]) -> None:
    if not math.isfinite(float(value)):
        raise error_type(f"{context} must be finite")

    minimum = schema.get("minimum")
    if minimum is not None and value < minimum:
        raise error_type(f"{context} must be >= {minimum}")

    maximum = schema.get("maximum")
    if maximum is not None and value > maximum:
        raise error_type(f"{context} must be <= {maximum}")


def matches_type(value: Any, expected_type: str) -> bool:
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
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    return False


def type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if value is None:
        return "null"
    return type(value).__name__
