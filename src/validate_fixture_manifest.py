"""Validate the deterministic external fixture manifest.

This validator checks the local manifest that indexes controlled public-safe
fixtures. It does not generate files, rescore traces, call providers, run local
models, execute OpenClaw, contact networks, or perform external actions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "traces/external/fixture_manifest.json"

REQUIRED_TOP_LEVEL_FIELDS = {
    "manifest_id",
    "version",
    "generated_at",
    "purpose",
    "scope",
    "non_goals",
    "fixtures",
}

REQUIRED_FIXTURE_FIELDS = {
    "fixture_id",
    "source_path",
    "source_kind",
    "source_type",
    "provenance_class",
    "data_classification",
    "generated_by",
    "validates_with",
    "imported_by",
    "scored_trace_path",
    "report_paths",
    "quality_gate_included",
    "expected_record_count",
    "limitations",
    "notes",
    "safety_assertions",
}

REQUIRED_SAFETY_ASSERTIONS = {
    "public_safe",
    "live_execution",
    "external_actions",
    "contains_private_data",
    "credentials_required",
}

EXPECTED_SAFE_ASSERTIONS = {
    "public_safe": True,
    "live_execution": False,
    "external_actions": False,
    "contains_private_data": False,
    "credentials_required": False,
}

BLOCKED_DATA_CLASSIFICATIONS = {
    "private_or_sensitive_blocked",
    "private",
    "sensitive",
}


class FixtureManifestValidationError(Exception):
    """Manifest validation error with public-safe context."""


def display_path(path: Path, repo_root: Path = REPO_ROOT) -> str:
    """Format a path relative to the repo when possible."""

    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def load_manifest(path: Path) -> dict[str, Any]:
    """Load a manifest JSON file."""

    if not path.exists():
        raise FixtureManifestValidationError(f"{display_path(path)}: file does not exist")

    try:
        with path.open("r", encoding="utf-8") as manifest_file:
            manifest = json.load(manifest_file)
    except json.JSONDecodeError as exc:
        raise FixtureManifestValidationError(
            f"{display_path(path)}:{exc.lineno}: invalid JSON: {exc.msg}"
        ) from exc

    if not isinstance(manifest, dict):
        raise FixtureManifestValidationError(f"{display_path(path)}: manifest must be a JSON object")

    return manifest


def validate_manifest(path: Path = DEFAULT_MANIFEST_PATH, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Validate the fixture manifest and return a small summary."""

    manifest = load_manifest(path)
    validate_top_level_fields(manifest, path, repo_root)

    fixtures = manifest["fixtures"]
    seen_fixture_ids: set[str] = set()
    for index, fixture in enumerate(fixtures):
        context = f"{display_path(path, repo_root)}:fixtures[{index}]"
        validate_fixture_entry(fixture, context, seen_fixture_ids, repo_root)

    return {
        "manifest_path": display_path(path, repo_root),
        "fixture_count": len(fixtures),
        "quality_gate_fixture_count": sum(1 for fixture in fixtures if fixture["quality_gate_included"] is True),
    }


def validate_top_level_fields(manifest: dict[str, Any], path: Path, repo_root: Path = REPO_ROOT) -> None:
    """Validate manifest-level shape."""

    context = display_path(path, repo_root)
    missing_fields = sorted(REQUIRED_TOP_LEVEL_FIELDS - set(manifest))
    if missing_fields:
        raise FixtureManifestValidationError(f"{context}: missing required fields: {', '.join(missing_fields)}")

    if not isinstance(manifest["manifest_id"], str) or manifest["manifest_id"] != "external_fixture_manifest":
        raise FixtureManifestValidationError(f"{context}: manifest_id must be external_fixture_manifest")

    for field_name in ["version", "generated_at", "purpose"]:
        require_non_empty_string(manifest[field_name], f"{context}.{field_name}")

    for field_name in ["scope", "non_goals"]:
        require_string_list(manifest[field_name], f"{context}.{field_name}")

    if not isinstance(manifest["fixtures"], list):
        raise FixtureManifestValidationError(f"{context}.fixtures must be an array")
    if not manifest["fixtures"]:
        raise FixtureManifestValidationError(f"{context}.fixtures must not be empty")


def validate_fixture_entry(
    fixture: Any,
    context: str,
    seen_fixture_ids: set[str],
    repo_root: Path = REPO_ROOT,
) -> None:
    """Validate one fixture entry."""

    if not isinstance(fixture, dict):
        raise FixtureManifestValidationError(f"{context}: fixture entry must be an object")

    missing_fields = sorted(REQUIRED_FIXTURE_FIELDS - set(fixture))
    if missing_fields:
        raise FixtureManifestValidationError(f"{context}: missing required fields: {', '.join(missing_fields)}")

    fixture_id = require_non_empty_string(fixture["fixture_id"], f"{context}.fixture_id")
    if fixture_id in seen_fixture_ids:
        raise FixtureManifestValidationError(f"{context}.fixture_id duplicate value: {fixture_id}")
    seen_fixture_ids.add(fixture_id)

    for field_name in [
        "source_kind",
        "source_type",
        "provenance_class",
        "data_classification",
        "generated_by",
        "validates_with",
        "imported_by",
        "notes",
    ]:
        require_non_empty_string(fixture[field_name], f"{context}.{field_name}")

    if fixture["data_classification"] in BLOCKED_DATA_CLASSIFICATIONS:
        raise FixtureManifestValidationError(
            f"{context}.data_classification must not claim private or sensitive data"
        )

    validate_quality_gate_flag(fixture["quality_gate_included"], f"{context}.quality_gate_included")
    validate_safety_assertions(fixture["safety_assertions"], f"{context}.safety_assertions")
    require_string_list(fixture["limitations"], f"{context}.limitations")

    source_path = require_repo_path(fixture["source_path"], f"{context}.source_path", repo_root)
    if not source_path.exists():
        raise FixtureManifestValidationError(f"{context}.source_path does not exist: {display_path(source_path)}")

    expected_record_count = require_non_negative_int(
        fixture["expected_record_count"],
        f"{context}.expected_record_count",
    )
    if source_path.suffix == ".jsonl":
        validate_line_count(source_path, expected_record_count, f"{context}.source_path")

    scored_trace_path_value = fixture["scored_trace_path"]
    scored_trace_path = require_repo_path(scored_trace_path_value, f"{context}.scored_trace_path", repo_root)
    if not scored_trace_path.exists():
        raise FixtureManifestValidationError(
            f"{context}.scored_trace_path does not exist: {display_path(scored_trace_path)}"
        )
    if "expected_scored_count" in fixture:
        expected_scored_count = require_non_negative_int(
            fixture["expected_scored_count"],
            f"{context}.expected_scored_count",
        )
        if scored_trace_path.suffix == ".jsonl":
            validate_line_count(scored_trace_path, expected_scored_count, f"{context}.scored_trace_path")

    report_paths = fixture["report_paths"]
    if not isinstance(report_paths, list):
        raise FixtureManifestValidationError(f"{context}.report_paths must be an array")
    for report_index, report_path_value in enumerate(report_paths):
        report_path = require_repo_path(report_path_value, f"{context}.report_paths[{report_index}]", repo_root)
        if not report_path.exists():
            raise FixtureManifestValidationError(
                f"{context}.report_paths[{report_index}] does not exist: {display_path(report_path)}"
            )


def validate_quality_gate_flag(value: Any, context: str) -> None:
    if not isinstance(value, bool):
        raise FixtureManifestValidationError(f"{context} must be a boolean")


def validate_safety_assertions(value: Any, context: str) -> None:
    """Validate explicit safety assertions for committed fixture families."""

    if not isinstance(value, dict):
        raise FixtureManifestValidationError(f"{context} must be an object")

    missing_fields = sorted(REQUIRED_SAFETY_ASSERTIONS - set(value))
    if missing_fields:
        raise FixtureManifestValidationError(f"{context} missing required fields: {', '.join(missing_fields)}")

    unexpected_fields = sorted(set(value) - REQUIRED_SAFETY_ASSERTIONS)
    if unexpected_fields:
        raise FixtureManifestValidationError(f"{context} unexpected fields: {', '.join(unexpected_fields)}")

    for field_name, expected_value in EXPECTED_SAFE_ASSERTIONS.items():
        actual_value = value[field_name]
        if not isinstance(actual_value, bool):
            raise FixtureManifestValidationError(f"{context}.{field_name} must be a boolean")
        if actual_value is not expected_value:
            expected_text = str(expected_value).lower()
            raise FixtureManifestValidationError(
                f"{context}.{field_name} must be {expected_text} for committed fixtures"
            )


def validate_line_count(path: Path, expected_count: int, context: str) -> None:
    """Validate a JSONL-style non-empty line count."""

    with path.open("r", encoding="utf-8") as input_file:
        actual_count = sum(1 for line in input_file if line.strip())

    if actual_count != expected_count:
        raise FixtureManifestValidationError(
            f"{context} expected {expected_count} non-empty JSONL records, "
            f"found {actual_count} in {display_path(path)}"
        )


def require_non_empty_string(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise FixtureManifestValidationError(f"{context} must be a string")
    if not value.strip():
        raise FixtureManifestValidationError(f"{context} must not be empty")
    return value


def require_string_list(value: Any, context: str) -> None:
    if not isinstance(value, list):
        raise FixtureManifestValidationError(f"{context} must be an array")
    if not value:
        raise FixtureManifestValidationError(f"{context} must not be empty")
    for index, item in enumerate(value):
        require_non_empty_string(item, f"{context}[{index}]")


def require_non_negative_int(value: Any, context: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise FixtureManifestValidationError(f"{context} must be an integer")
    if value < 0:
        raise FixtureManifestValidationError(f"{context} must be >= 0")
    return value


def require_repo_path(value: Any, context: str, repo_root: Path = REPO_ROOT) -> Path:
    raw_path = require_non_empty_string(value, context)
    path = Path(raw_path)
    if path.is_absolute():
        raise FixtureManifestValidationError(f"{context} must be a repository-relative path")

    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError as exc:
        raise FixtureManifestValidationError(f"{context} must stay within the repository") from exc
    return resolved


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the controlled external fixture manifest.")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Fixture manifest JSON path to validate.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        summary = validate_manifest(args.path)
    except (FixtureManifestValidationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"fixture manifest path: {summary['manifest_path']}")
    print(f"fixture entries validated: {summary['fixture_count']}")
    print(f"quality-gate fixture entries: {summary['quality_gate_fixture_count']}")
    print("fixture manifest validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
