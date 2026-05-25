"""Validate the generated report artifact manifest.

This validator checks local report provenance metadata only. It does not
regenerate reports, rescore traces, rewrite files, call providers, execute
agents, collect live outputs, or perform external actions.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "reports/comparisons/report_manifest.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/report_manifest.schema.json"

EXPECTED_SAFE_ASSERTIONS = {
    "public_safe": True,
    "live_execution": False,
    "external_actions": False,
    "contains_private_data": False,
    "credentials_required": False,
}


class ReportManifestValidationError(Exception):
    """Report manifest validation error with public-safe context."""


def display_path(path: Path, repo_root: Path = REPO_ROOT) -> str:
    """Format a path relative to the repo when possible."""

    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def load_json_object(path: Path, label: str) -> dict[str, Any]:
    """Load a JSON object from disk."""

    if not path.exists():
        raise ReportManifestValidationError(f"{display_path(path)}: {label} does not exist")

    try:
        with path.open("r", encoding="utf-8") as input_file:
            value = json.load(input_file)
    except json.JSONDecodeError as exc:
        raise ReportManifestValidationError(
            f"{display_path(path)}:{exc.lineno}: invalid JSON: {exc.msg}"
        ) from exc

    if not isinstance(value, dict):
        raise ReportManifestValidationError(f"{display_path(path)}: {label} must be a JSON object")
    return value


def validate_manifest(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the report manifest and return a deterministic summary."""

    schema = load_json_object(schema_path, "schema")
    manifest = load_json_object(manifest_path, "manifest")
    validate_schema_value(manifest, schema, display_path(manifest_path, repo_root), manifest_path)
    artifacts = manifest["report_artifacts"]
    validate_artifacts(artifacts, manifest_path, repo_root)

    return {
        "manifest_path": display_path(manifest_path, repo_root),
        "schema_path": display_path(schema_path, repo_root),
        "artifact_count": len(artifacts),
        "markdown_report_count": sum(1 for artifact in artifacts if artifact["artifact_type"] == "markdown_report"),
        "json_snapshot_count": sum(1 for artifact in artifacts if artifact["artifact_type"] == "json_snapshot"),
        "quality_gate_artifact_count": sum(1 for artifact in artifacts if artifact["quality_gate_included"] is True),
    }


def validate_schema_value(value: Any, schema: dict[str, Any], context: str, path: Path) -> None:
    """Validate a value against the schema subset used by the report manifest schema."""

    expected_type = schema.get("type")
    if expected_type is not None and not matches_type(value, expected_type):
        raise ReportManifestValidationError(f"{context} must be {expected_type}, got {type_name(value)}")

    if "const" in schema and value != schema["const"]:
        raise ReportManifestValidationError(f"{context} must equal {schema['const']!r}")

    if "enum" in schema and value not in schema["enum"]:
        allowed = ", ".join(str(item) for item in schema["enum"])
        raise ReportManifestValidationError(f"{context} must be one of: {allowed}")

    if isinstance(value, dict):
        validate_object(value, schema, context, path)
    if isinstance(value, list):
        validate_array(value, schema, context, path)
    if isinstance(value, str):
        validate_string(value, schema, context)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        validate_number(value, schema, context)


def validate_object(value: dict[str, Any], schema: dict[str, Any], context: str, path: Path) -> None:
    properties = schema.get("properties", {})
    if properties is not None and not isinstance(properties, dict):
        raise ReportManifestValidationError(f"{display_path(path)} schema properties must be an object")

    required = set(schema.get("required", []))
    missing_fields = sorted(required - set(value))
    if missing_fields:
        raise ReportManifestValidationError(f"{context}: missing required fields: {', '.join(missing_fields)}")

    additional_properties = schema.get("additionalProperties", True)
    if additional_properties is False:
        unexpected_fields = sorted(set(value) - set(properties))
        if unexpected_fields:
            raise ReportManifestValidationError(f"{context}: unexpected fields: {', '.join(unexpected_fields)}")

    for field_name, field_schema in properties.items():
        if field_name in value:
            validate_schema_value(value[field_name], field_schema, f"{context}.{field_name}", path)


def validate_array(value: list[Any], schema: dict[str, Any], context: str, path: Path) -> None:
    min_items = schema.get("minItems")
    if min_items is not None and len(value) < min_items:
        raise ReportManifestValidationError(f"{context} must contain at least {min_items} item(s)")

    item_schema = schema.get("items")
    if isinstance(item_schema, dict):
        for index, item in enumerate(value):
            validate_schema_value(item, item_schema, f"{context}[{index}]", path)


def validate_string(value: str, schema: dict[str, Any], context: str) -> None:
    min_length = schema.get("minLength")
    if min_length is not None and len(value) < min_length:
        raise ReportManifestValidationError(f"{context} must contain at least {min_length} character(s)")

    pattern = schema.get("pattern")
    if pattern is not None and re.fullmatch(str(pattern), value) is None:
        raise ReportManifestValidationError(f"{context} must match pattern {pattern!r}")


def validate_number(value: int | float, schema: dict[str, Any], context: str) -> None:
    if not math.isfinite(float(value)):
        raise ReportManifestValidationError(f"{context} must be finite")

    minimum = schema.get("minimum")
    if minimum is not None and value < minimum:
        raise ReportManifestValidationError(f"{context} must be >= {minimum}")

    maximum = schema.get("maximum")
    if maximum is not None and value > maximum:
        raise ReportManifestValidationError(f"{context} must be <= {maximum}")


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


def validate_artifacts(artifacts: list[dict[str, Any]], manifest_path: Path, repo_root: Path) -> None:
    """Validate report artifact references and cross-artifact snapshot dependencies."""

    seen_artifact_ids: set[str] = set()
    seen_artifact_paths: set[str] = set()
    artifact_type_by_path = {str(artifact["path"]): str(artifact["artifact_type"]) for artifact in artifacts}

    for index, artifact in enumerate(artifacts):
        context = f"{display_path(manifest_path, repo_root)}.report_artifacts[{index}]"
        artifact_id = str(artifact["artifact_id"])
        if artifact_id in seen_artifact_ids:
            raise ReportManifestValidationError(f"{context}.artifact_id duplicate value: {artifact_id}")
        seen_artifact_ids.add(artifact_id)

        artifact_path_value = str(artifact["path"])
        if artifact_path_value in seen_artifact_paths:
            raise ReportManifestValidationError(f"{context}.path duplicate value: {artifact_path_value}")
        seen_artifact_paths.add(artifact_path_value)

        artifact_path = require_existing_repo_path(artifact_path_value, f"{context}.path", repo_root)
        validate_artifact_path_shape(artifact_path, str(artifact["artifact_type"]), f"{context}.path")

        generated_by_path = require_existing_repo_path(artifact["generated_by"], f"{context}.generated_by", repo_root)
        if generated_by_path.suffix != ".py":
            raise ReportManifestValidationError(f"{context}.generated_by must point to a Python script")

        for input_index, input_path in enumerate(artifact["input_paths"]):
            require_existing_repo_path(input_path, f"{context}.input_paths[{input_index}]", repo_root)

        for snapshot_index, snapshot_path in enumerate(artifact["snapshot_dependency_paths"]):
            resolved_snapshot_path = require_existing_repo_path(
                snapshot_path,
                f"{context}.snapshot_dependency_paths[{snapshot_index}]",
                repo_root,
            )
            if resolved_snapshot_path.suffix != ".json":
                raise ReportManifestValidationError(
                    f"{context}.snapshot_dependency_paths[{snapshot_index}] must point to a JSON snapshot"
                )
            if artifact_type_by_path.get(str(snapshot_path)) != "json_snapshot":
                raise ReportManifestValidationError(
                    f"{context}.snapshot_dependency_paths[{snapshot_index}] must reference a json_snapshot artifact"
                )

        validate_safety_assertions(artifact["safety_assertions"], f"{context}.safety_assertions")


def validate_artifact_path_shape(path: Path, artifact_type: str, context: str) -> None:
    if artifact_type == "markdown_report":
        if path.suffix != ".md":
            raise ReportManifestValidationError(f"{context} must use .md for markdown_report artifacts")
        if path.stat().st_size == 0:
            raise ReportManifestValidationError(f"{context} must not be empty")
        return

    if artifact_type == "json_snapshot":
        if path.suffix != ".json":
            raise ReportManifestValidationError(f"{context} must use .json for json_snapshot artifacts")
        load_json_object(path, "snapshot")


def validate_safety_assertions(value: dict[str, Any], context: str) -> None:
    for field_name, expected_value in EXPECTED_SAFE_ASSERTIONS.items():
        actual_value = value[field_name]
        if actual_value is not expected_value:
            raise ReportManifestValidationError(f"{context}.{field_name} must equal {expected_value!r}")


def require_existing_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ReportManifestValidationError(f"{context} must be a non-empty string")
    path = Path(value)
    if path.is_absolute():
        raise ReportManifestValidationError(f"{context} must be a repository-relative path")

    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ReportManifestValidationError(f"{context} must stay within the repository") from exc

    if not resolved.exists():
        raise ReportManifestValidationError(f"{context} does not exist: {display_path(resolved, repo_root)}")
    return resolved


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the generated report artifact manifest.")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Report manifest JSON path to validate.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help="Report manifest JSON Schema path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        summary = validate_manifest(args.path, args.schema)
    except (ReportManifestValidationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"report manifest path: {summary['manifest_path']}")
    print(f"report manifest schema: {summary['schema_path']}")
    print(f"report artifacts: {summary['artifact_count']}")
    print(f"markdown reports: {summary['markdown_report_count']}")
    print(f"json snapshots: {summary['json_snapshot_count']}")
    print(f"quality-gate artifacts: {summary['quality_gate_artifact_count']}")
    print("report manifest validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
