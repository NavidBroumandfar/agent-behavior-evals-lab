"""Promote reviewed adapter-output candidates into committed fixture shape.

This command copies explicitly reviewed `.reviewed.jsonl` adapter-output
candidates to a stable fixture path under `traces/external/` and can emit a
fixture-manifest entry draft. It does not collect live outputs, run models,
execute agents, or update the manifest automatically.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from trace_writer import write_jsonl
from validate_adapter_outputs import AdapterOutputValidationError, load_adapter_output_records, validate_jsonl_file


REPO_ROOT = Path(__file__).resolve().parents[1]


class ReviewedOutputPromotionError(Exception):
    """Reviewed output promotion error."""


def promote_reviewed_outputs(
    input_path: Path,
    output_path: Path,
    fixture_id: str,
    scored_trace_path: Path,
    report_paths: list[Path],
    manifest_entry_path: Path | None = None,
    force: bool = False,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Promote reviewed adapter outputs and optionally write a manifest entry draft."""

    validate_reviewed_input_path(input_path)
    validate_fixture_output_path(output_path, repo_root)
    validate_repo_output_path(scored_trace_path, repo_root, "scored_trace_path", expected_parent="traces/scored")
    for index, report_path in enumerate(report_paths):
        validate_repo_output_path(report_path, repo_root, f"report_paths[{index}]", expected_parent="reports")
    if manifest_entry_path is not None:
        validate_manifest_entry_output_path(manifest_entry_path, repo_root)

    if output_path.exists() and not force:
        raise ReviewedOutputPromotionError(f"{display_path(output_path, repo_root)} already exists; use force=True")

    try:
        records = load_adapter_output_records(input_path)
    except AdapterOutputValidationError as exc:
        raise ReviewedOutputPromotionError(f"reviewed input failed validation: {exc}") from exc
    validate_promoted_records(records, input_path)
    write_jsonl(records, output_path)

    try:
        validate_jsonl_file(output_path)
    except AdapterOutputValidationError as exc:
        raise ReviewedOutputPromotionError(f"promoted fixture failed validation: {exc}") from exc

    manifest_entry = build_manifest_entry(
        records,
        output_path,
        fixture_id,
        scored_trace_path,
        report_paths,
        repo_root,
    )
    if manifest_entry_path is not None:
        manifest_entry_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_entry_path.write_text(json.dumps(manifest_entry, sort_keys=True, indent=2), encoding="utf-8")

    return {
        "input_path": display_path(input_path, repo_root),
        "output_path": display_path(output_path, repo_root),
        "fixture_id": fixture_id,
        "records_promoted": len(records),
        "manifest_entry_path": display_path(manifest_entry_path, repo_root) if manifest_entry_path else "",
        "manifest_entry": manifest_entry,
    }


def validate_promoted_records(records: list[dict[str, Any]], input_path: Path) -> None:
    """Require reviewed records to carry reviewed-output provenance details."""

    for line_number, record in enumerate(records, start=1):
        context = f"{display_path(input_path)}:{line_number}"
        provenance_details = record.get("provenance_details")
        if not isinstance(provenance_details, dict):
            raise ReviewedOutputPromotionError(f"{context}: provenance_details must be present")

        if provenance_details.get("execution_mode") != "saved_output_only":
            raise ReviewedOutputPromotionError(f"{context}: execution_mode must be saved_output_only")
        if provenance_details.get("data_classification") != "public_safe_fixture":
            raise ReviewedOutputPromotionError(f"{context}: data_classification must be public_safe_fixture")
        if record["provenance"]["public_safe"] is not True:
            raise ReviewedOutputPromotionError(f"{context}: provenance.public_safe must be true")
        if record["provenance"]["live_execution"] is not False:
            raise ReviewedOutputPromotionError(f"{context}: provenance.live_execution must be false")


def build_manifest_entry(
    records: list[dict[str, Any]],
    output_path: Path,
    fixture_id: str,
    scored_trace_path: Path,
    report_paths: list[Path],
    repo_root: Path,
) -> dict[str, Any]:
    """Build a fixture manifest entry draft for a promoted fixture."""

    return {
        "fixture_id": fixture_id,
        "source_path": display_path(output_path, repo_root),
        "source_kind": "promoted_reviewed_text_only_fixture",
        "source_type": "normalized_adapter_output",
        "provenance_class": "reviewed_text_only_saved_output",
        "data_classification": "public_safe_fixture",
        "generated_by": "src/promote_reviewed_outputs.py",
        "validates_with": "src/validate_adapter_outputs.py",
        "imported_by": "src/import_adapter_outputs.py",
        "scored_trace_path": display_path(scored_trace_path, repo_root),
        "expected_record_count": len(records),
        "expected_scored_count": len(records),
        "report_paths": [display_path(path, repo_root) for path in report_paths],
        "quality_gate_included": False,
        "safety_assertions": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
            "credentials_required": False,
        },
        "limitations": [
            "Promoted from reviewed text-only saved outputs.",
            "No live execution is represented by the promoted fixture.",
            "Fixture promotion does not automatically update the manifest.",
        ],
        "notes": "Review the promoted fixture and manifest entry draft before adding either to committed quality-gate fixtures.",
    }


def validate_reviewed_input_path(path: Path) -> None:
    if not path.name.endswith(".reviewed.jsonl"):
        raise ReviewedOutputPromotionError("input path must end with .reviewed.jsonl")


def validate_fixture_output_path(path: Path, repo_root: Path) -> None:
    validate_repo_output_path(path, repo_root, "output_path", expected_parent="traces/external")
    if not path.name.endswith(".jsonl"):
        raise ReviewedOutputPromotionError("output path must end with .jsonl")
    for blocked_suffix in [".local.jsonl", ".private.jsonl", ".reviewed.jsonl"]:
        if path.name.endswith(blocked_suffix):
            raise ReviewedOutputPromotionError(f"output path must not end with {blocked_suffix}")


def validate_manifest_entry_output_path(path: Path, repo_root: Path) -> None:
    resolved = resolve_repo_path(path, repo_root, "manifest_entry_path")
    if not resolved.name.endswith(".manifest_entry.local.json"):
        raise ReviewedOutputPromotionError("manifest entry path must end with .manifest_entry.local.json")


def validate_repo_output_path(path: Path, repo_root: Path, context: str, expected_parent: str) -> None:
    resolved = resolve_repo_path(path, repo_root, context)
    expected_root = (repo_root / expected_parent).resolve()
    try:
        resolved.relative_to(expected_root)
    except ValueError as exc:
        raise ReviewedOutputPromotionError(f"{context} must stay under {expected_parent}") from exc


def resolve_repo_path(path: Path, repo_root: Path, context: str) -> Path:
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (repo_root / path).resolve()

    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ReviewedOutputPromotionError(f"{context} must stay within the repository") from exc
    return resolved


def display_path(path: Path | None, repo_root: Path = REPO_ROOT) -> str:
    if path is None:
        return ""
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote reviewed adapter-output candidates to fixture JSONL.")
    parser.add_argument("--input", required=True, type=Path, help="Reviewed adapter-output JSONL ending in .reviewed.jsonl.")
    parser.add_argument("--output", required=True, type=Path, help="Promoted fixture path under traces/external/.")
    parser.add_argument("--fixture-id", required=True, help="Fixture ID to use in the manifest entry draft.")
    parser.add_argument("--scored-trace-path", required=True, type=Path, help="Future scored trace path under traces/scored/.")
    parser.add_argument(
        "--report-path",
        action="append",
        type=Path,
        default=[],
        help="Report path to include in the manifest entry draft. May be repeated.",
    )
    parser.add_argument(
        "--manifest-entry",
        type=Path,
        default=None,
        help="Optional local manifest-entry draft ending in .manifest_entry.local.json.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite output if it already exists.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    report_paths = args.report_path or [REPO_ROOT / "reports/comparisons/external_fixture_comparison_report.md"]

    try:
        summary = promote_reviewed_outputs(
            args.input,
            args.output,
            args.fixture_id,
            args.scored_trace_path,
            report_paths,
            args.manifest_entry,
            args.force,
        )
    except (AdapterOutputValidationError, ReviewedOutputPromotionError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"input path: {summary['input_path']}")
    print(f"output path: {summary['output_path']}")
    print(f"fixture id: {summary['fixture_id']}")
    print(f"records promoted: {summary['records_promoted']}")
    if summary["manifest_entry_path"]:
        print(f"manifest entry path: {summary['manifest_entry_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
