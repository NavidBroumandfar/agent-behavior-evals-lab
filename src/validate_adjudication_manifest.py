"""Validate the adjudication fixture manifest contract.

This validator is a deterministic local quality-gate check. It reads only the
committed adjudication manifest, referenced public-safe fixture files, and
referenced scored traces. It does not rescore traces, rewrite files, call
providers, execute agents, collect live outputs, or perform external actions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from schema_validation_utils import display_path, load_json_object, validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "traces/external/adjudication_manifest.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/adjudication_manifest.schema.json"

QUALITY_GATE_COMPATIBLE_REVIEW_STATUSES = {
    "reviewed",
    "needs_discussion",
}


class AdjudicationManifestValidationError(Exception):
    """Manifest validation error with public-safe context."""


def validate_manifest(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the adjudication manifest and return a deterministic summary."""

    schema = load_json_object(schema_path, "schema", repo_root, AdjudicationManifestValidationError)
    manifest = load_json_object(manifest_path, "manifest", repo_root, AdjudicationManifestValidationError)
    return validate_loaded_manifest(manifest, schema, manifest_path, schema_path, repo_root)


def load_validated_manifest(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Load and validate the adjudication manifest, returning the manifest object."""

    schema = load_json_object(schema_path, "schema", repo_root, AdjudicationManifestValidationError)
    manifest = load_json_object(manifest_path, "manifest", repo_root, AdjudicationManifestValidationError)
    validate_loaded_manifest(manifest, schema, manifest_path, schema_path, repo_root)
    return manifest


def validate_loaded_manifest(
    manifest: dict[str, Any],
    schema: dict[str, Any],
    manifest_path: Path,
    schema_path: Path,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate loaded manifest shape and semantics and return a summary."""

    validate_schema_value(
        manifest,
        schema,
        display_path(manifest_path, repo_root),
        manifest_path,
        repo_root,
        AdjudicationManifestValidationError,
    )
    fixtures = manifest["adjudication_fixtures"]
    fixture_ids, profile_names, category_names = validate_fixture_semantics(
        fixtures,
        manifest_path,
        repo_root,
    )
    threshold_count = validate_threshold_semantics(
        manifest.get("quality_gate_thresholds", {}),
        fixture_ids,
        profile_names,
        category_names,
        f"{display_path(manifest_path, repo_root)}.quality_gate_thresholds",
    )

    return {
        "manifest_path": display_path(manifest_path, repo_root),
        "schema_path": display_path(schema_path, repo_root),
        "fixture_count": len(fixtures),
        "quality_gate_fixture_count": sum(1 for fixture in fixtures if fixture["quality_gate_included"] is True),
        "quality_gate_threshold_count": threshold_count,
    }


def validate_fixture_semantics(
    fixtures: list[dict[str, Any]],
    manifest_path: Path,
    repo_root: Path,
) -> tuple[set[str], set[str], set[str]]:
    """Validate fixture references and collect source trace profile/category names."""

    fixture_ids: set[str] = set()
    profile_names: set[str] = set()
    category_names: set[str] = set()
    source_trace_cache: dict[Path, tuple[set[str], set[str]]] = {}

    for index, fixture in enumerate(fixtures):
        context = f"{display_path(manifest_path, repo_root)}.adjudication_fixtures[{index}]"
        fixture_id = str(fixture["fixture_id"])
        if fixture_id in fixture_ids:
            raise AdjudicationManifestValidationError(f"{context}.fixture_id duplicate value: {fixture_id}")
        fixture_ids.add(fixture_id)

        if fixture["quality_gate_included"] is True and fixture["review_status"] not in QUALITY_GATE_COMPATIBLE_REVIEW_STATUSES:
            allowed = ", ".join(sorted(QUALITY_GATE_COMPATIBLE_REVIEW_STATUSES))
            raise AdjudicationManifestValidationError(
                f"{context}.review_status must be one of: {allowed} when quality_gate_included is true"
            )

        fixture_path = require_repo_relative_path(fixture["path"], f"{context}.path", repo_root)
        if not fixture_path.exists():
            raise AdjudicationManifestValidationError(f"{context}.path does not exist: {display_path(fixture_path)}")
        if fixture_path.suffix == ".jsonl":
            validate_line_count(fixture_path, int(fixture["expected_record_count"]), f"{context}.path")

        for source_index, source_path_value in enumerate(fixture["source_trace_paths"]):
            source_path = require_repo_relative_path(
                source_path_value,
                f"{context}.source_trace_paths[{source_index}]",
                repo_root,
            )
            if not source_path.exists():
                raise AdjudicationManifestValidationError(
                    f"{context}.source_trace_paths[{source_index}] does not exist: {display_path(source_path)}"
                )
            if source_path not in source_trace_cache:
                source_trace_cache[source_path] = load_source_trace_metadata(
                    source_path,
                    f"{context}.source_trace_paths[{source_index}]",
                )
            source_profiles, source_categories = source_trace_cache[source_path]
            profile_names.update(source_profiles)
            category_names.update(source_categories)

    return fixture_ids, profile_names, category_names


def validate_threshold_semantics(
    thresholds: dict[str, Any],
    fixture_ids: set[str],
    profile_names: set[str],
    category_names: set[str],
    context: str,
) -> int:
    """Validate threshold map keys against the declared fixture/source universe."""

    threshold_count = 0
    threshold_count += 1 if "min_review_coverage" in thresholds else 0
    threshold_count += 1 if "max_needs_discussion" in thresholds else 0

    profile_thresholds = thresholds.get("min_profile_review_coverage", {})
    threshold_count += len(profile_thresholds)
    validate_threshold_keys(profile_thresholds, profile_names, f"{context}.min_profile_review_coverage", "profile")

    category_thresholds = thresholds.get("min_category_review_coverage", {})
    threshold_count += len(category_thresholds)
    validate_threshold_keys(category_thresholds, category_names, f"{context}.min_category_review_coverage", "category")

    fixture_thresholds = thresholds.get("max_fixture_needs_discussion", {})
    threshold_count += len(fixture_thresholds)
    validate_threshold_keys(fixture_thresholds, fixture_ids, f"{context}.max_fixture_needs_discussion", "fixture")

    return threshold_count


def validate_threshold_keys(
    thresholds: dict[str, Any],
    allowed_keys: set[str],
    context: str,
    label: str,
) -> None:
    for key in sorted(thresholds):
        if not str(key).strip():
            raise AdjudicationManifestValidationError(f"{context} contains an empty {label} threshold key")
        if key not in allowed_keys:
            allowed = ", ".join(sorted(allowed_keys))
            raise AdjudicationManifestValidationError(
                f"{context}.{key} references unknown {label}; expected one of: {allowed}"
            )


def load_source_trace_metadata(path: Path, context: str) -> tuple[set[str], set[str]]:
    """Collect profile and category labels from a scored trace JSONL file."""

    profile_names: set[str] = set()
    category_names: set[str] = set()
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise AdjudicationManifestValidationError(
                    f"{display_path(path)}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc
            if not isinstance(record, dict):
                raise AdjudicationManifestValidationError(f"{display_path(path)}:{line_number}: record must be an object")
            profile_name = record.get("profile_name")
            category = record.get("category")
            if isinstance(profile_name, str) and profile_name:
                profile_names.add(profile_name)
            if isinstance(category, str) and category:
                category_names.add(category)

    if not profile_names:
        raise AdjudicationManifestValidationError(f"{context} contains no profile_name values")
    if not category_names:
        raise AdjudicationManifestValidationError(f"{context} contains no category values")
    return profile_names, category_names


def validate_line_count(path: Path, expected_count: int, context: str) -> None:
    """Validate a JSONL-style non-empty line count."""

    with path.open("r", encoding="utf-8") as input_file:
        actual_count = sum(1 for line in input_file if line.strip())

    if actual_count != expected_count:
        raise AdjudicationManifestValidationError(
            f"{context} expected {expected_count} non-empty JSONL records, found {actual_count} in {display_path(path)}"
        )


def require_repo_relative_path(value: Any, context: str, repo_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise AdjudicationManifestValidationError(f"{context} must be a non-empty string")
    path = Path(value)
    if path.is_absolute():
        raise AdjudicationManifestValidationError(f"{context} must be a repository-relative path")

    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise AdjudicationManifestValidationError(f"{context} must stay within the repository") from exc
    return resolved


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the adjudication fixture manifest contract.")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Adjudication manifest JSON path to validate.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help="Adjudication manifest JSON Schema path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        summary = validate_manifest(args.path, args.schema)
    except (AdjudicationManifestValidationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"adjudication manifest path: {summary['manifest_path']}")
    print(f"adjudication manifest schema: {summary['schema_path']}")
    print(f"adjudication fixture entries: {summary['fixture_count']}")
    print(f"quality-gate fixture entries: {summary['quality_gate_fixture_count']}")
    print(f"quality-gate thresholds: {summary['quality_gate_threshold_count']}")
    print("adjudication manifest validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
