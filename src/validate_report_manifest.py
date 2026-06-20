"""Validate the generated report artifact manifest.

This validator checks local report provenance metadata only. It does not
regenerate reports, rescore traces, rewrite files, call providers, execute
agents, collect live outputs, or perform external actions.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from schema_validation_utils import display_path, load_json_object, validate_schema_value


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
EXPECTED_QUALITY_GATE_ARTIFACT_PATHS = {
    "reports/baseline_report.md",
    "reports/comparisons/profile_comparison_report.md",
    "reports/comparisons/baseline_regression_snapshot.json",
    "reports/comparisons/failure_inspection.md",
    "reports/comparisons/manual_output_report.md",
    "reports/comparisons/openclaw_manual_eval_report.md",
    "reports/comparisons/saved_transcript_replay_report.md",
    "reports/comparisons/openclaw_saved_transcript_pilot_report.md",
    "reports/comparisons/external_fixture_comparison_report.md",
    "reports/comparisons/adjudication_summary_report.md",
    "reports/comparisons/adjudicated_aggregate_report.md",
    "reports/comparisons/adjudication_regression_snapshot.json",
    "reports/comparisons/baseline_self_comparison_report.md",
}


class ReportManifestValidationError(Exception):
    """Report manifest validation error with public-safe context."""


def validate_manifest(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the report manifest and return a deterministic summary."""

    schema = load_json_object(schema_path, "schema", repo_root, ReportManifestValidationError)
    manifest = load_json_object(manifest_path, "manifest", repo_root, ReportManifestValidationError)
    validate_schema_value(
        manifest,
        schema,
        display_path(manifest_path, repo_root),
        manifest_path,
        repo_root,
        ReportManifestValidationError,
    )
    artifacts = manifest["report_artifacts"]
    validate_artifacts(artifacts, manifest_path, repo_root)
    validate_quality_gate_artifact_coverage(artifacts, display_path(manifest_path, repo_root))

    return {
        "manifest_path": display_path(manifest_path, repo_root),
        "schema_path": display_path(schema_path, repo_root),
        "artifact_count": len(artifacts),
        "markdown_report_count": sum(1 for artifact in artifacts if artifact["artifact_type"] == "markdown_report"),
        "json_snapshot_count": sum(1 for artifact in artifacts if artifact["artifact_type"] == "json_snapshot"),
        "quality_gate_artifact_count": sum(1 for artifact in artifacts if artifact["quality_gate_included"] is True),
    }


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
        validate_artifact_path_shape(artifact_path, str(artifact["artifact_type"]), f"{context}.path", repo_root)

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


def validate_quality_gate_artifact_coverage(artifacts: list[dict[str, Any]], context: str) -> None:
    """Validate that known quality-gate reports and snapshots are indexed."""

    quality_gate_paths = {
        str(artifact["path"])
        for artifact in artifacts
        if artifact["quality_gate_included"] is True
    }
    missing_paths = sorted(EXPECTED_QUALITY_GATE_ARTIFACT_PATHS - quality_gate_paths)
    if missing_paths:
        raise ReportManifestValidationError(
            f"{context}.report_artifacts missing quality-gate artifacts: {', '.join(missing_paths)}"
        )


def validate_artifact_path_shape(path: Path, artifact_type: str, context: str, repo_root: Path) -> None:
    if artifact_type == "markdown_report":
        if path.suffix != ".md":
            raise ReportManifestValidationError(f"{context} must use .md for markdown_report artifacts")
        if path.stat().st_size == 0:
            raise ReportManifestValidationError(f"{context} must not be empty")
        return

    if artifact_type == "json_snapshot":
        if path.suffix != ".json":
            raise ReportManifestValidationError(f"{context} must use .json for json_snapshot artifacts")
        load_json_object(path, "snapshot", repo_root, ReportManifestValidationError)


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
