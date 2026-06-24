"""Generate and validate the M107E public-safe multimodal pilot fixture.

The pilot uses synthetic image/document assets and saved outputs only. It does
not call a vision model, use a provider, read customer media, execute tools,
contact networks, or perform external actions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from reporting_utils import display_path, write_json_object, write_text
from schema_validation_utils import load_json_object, validate_schema_value
from trace_writer import write_jsonl


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_SET_PATH = REPO_ROOT / "traces/external/m107e_multimodal_fixture_set.example.json"
SCHEMA_PATH = REPO_ROOT / "schemas/multimodal_saved_output_fixture.schema.json"
GENERATED_AT = "2026-06-24T00:00:00Z"
EXPECTED_CLAIM_BOUNDARY = "Pilot saved-output normalization evidence only; not broad multimodal coverage."
EXPECTED_SAFETY_ASSERTIONS = {
    "public_safe": True,
    "live_execution": False,
    "external_actions": False,
    "contains_private_data": False,
    "credentials_required": False,
    "customer_media": False,
    "raw_media_private": False,
}
EXPECTED_PROVENANCE = {
    "public_safe": True,
    "live_execution": False,
    "external_actions": False,
    "contains_private_data": False,
    "credentials_required": False,
    "customer_media": False,
}
FORBIDDEN_CONTENT_MARKERS = [
    "/users/",
    "/home/",
    "c:\\users\\",
    "customer-evidence/",
    "private-evidence/",
    "raw-evidence/",
    "customer-reports/",
    "begin private",
    "end private",
    "api_key",
    "api key",
    "password:",
    "token:",
    "sk-",
    "user@example.com",
    "real customer",
]


class MultimodalPilotError(Exception):
    """M107E multimodal pilot validation or generation error."""


def generate_multimodal_pilot(
    fixture_set_path: Path = FIXTURE_SET_PATH,
    schema_path: Path = SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate fixture metadata and emit saved outputs, review summary, and reports."""

    schema = load_json_object(schema_path, "multimodal fixture schema", repo_root, MultimodalPilotError)
    fixture_set = load_json_object(fixture_set_path, "multimodal fixture set", repo_root, MultimodalPilotError)
    context = display_path(fixture_set_path, repo_root)
    validate_schema_value(fixture_set, schema, context, fixture_set_path, repo_root, MultimodalPilotError)
    scan_for_forbidden_content(fixture_set, context)
    validate_fixture_semantics(fixture_set, context, repo_root)

    output_paths = resolve_output_paths(fixture_set["outputs"], repo_root)
    saved_outputs = build_saved_output_records(fixture_set, repo_root)
    review_summary = build_review_summary(fixture_set, saved_outputs, repo_root)
    report_json = build_report_json(fixture_set, saved_outputs, review_summary, repo_root)
    report_markdown = render_report_markdown(report_json)

    write_jsonl(saved_outputs, output_paths["saved_outputs_path"])
    write_json_object(review_summary, output_paths["review_summary_path"])
    write_json_object(report_json, output_paths["report_json_path"])
    write_text(report_markdown, output_paths["report_markdown_path"])

    return {
        "fixture_set_id": fixture_set["fixture_set_id"],
        "schema_path": display_path(schema_path, repo_root),
        "fixture_set_path": context,
        "media_asset_count": len(fixture_set["media_assets"]),
        "saved_output_record_count": len(saved_outputs),
        "reviewed_record_count": review_summary["reviewed_record_count"],
        "modalities": sorted({asset["modality"] for asset in fixture_set["media_assets"]}),
        "saved_outputs_path": display_path(output_paths["saved_outputs_path"], repo_root),
        "review_summary_path": display_path(output_paths["review_summary_path"], repo_root),
        "report_json_path": display_path(output_paths["report_json_path"], repo_root),
        "report_markdown_path": display_path(output_paths["report_markdown_path"], repo_root),
        "live_model_execution_in_quality_gate": fixture_set["live_model_execution_in_quality_gate"],
        "provider_calls_in_quality_gate": fixture_set["provider_calls_in_quality_gate"],
        "customer_media_count": review_summary["customer_media_count"],
    }


def validate_fixture_semantics(fixture_set: dict[str, Any], context: str, repo_root: Path) -> None:
    if fixture_set["fixture_set_id"] != "m107e_multimodal_public_safe_pilot":
        raise MultimodalPilotError(f"{context}.fixture_set_id must be m107e_multimodal_public_safe_pilot")
    if fixture_set["fixture_version"] != "0.1.0":
        raise MultimodalPilotError(f"{context}.fixture_version must be 0.1.0")
    validate_expected_mapping(fixture_set["safety_assertions"], EXPECTED_SAFETY_ASSERTIONS, f"{context}.safety_assertions")
    resolve_output_paths(fixture_set["outputs"], repo_root)
    validate_media_assets(fixture_set["media_assets"], context, repo_root)
    validate_saved_output_records(fixture_set["saved_output_records"], fixture_set["media_assets"], context)


def validate_media_assets(assets: list[dict[str, Any]], context: str, repo_root: Path) -> None:
    seen_ids: set[str] = set()
    modalities: set[str] = set()
    for index, asset in enumerate(assets):
        asset_context = f"{context}.media_assets[{index}]"
        asset_id = str(asset["asset_id"])
        if asset_id in seen_ids:
            raise MultimodalPilotError(f"{asset_context}.asset_id duplicate value: {asset_id}")
        seen_ids.add(asset_id)
        modalities.add(str(asset["modality"]))
        if asset["customer_media"] is not False:
            raise MultimodalPilotError(f"{asset_context}.customer_media must be false")
        if asset["contains_private_data"] is not False:
            raise MultimodalPilotError(f"{asset_context}.contains_private_data must be false")
        asset_path = require_repo_path(asset["path"], f"{asset_context}.path", repo_root)
        require_path_under(asset_path, repo_root / "fixtures/multimodal", f"{asset_context}.path", repo_root)
        if not asset_path.exists():
            raise MultimodalPilotError(f"{asset_context}.path does not exist: {display_path(asset_path, repo_root)}")
        actual_hash = hashlib.sha256(asset_path.read_bytes()).hexdigest()
        if actual_hash != asset["sha256"]:
            raise MultimodalPilotError(f"{asset_context}.sha256 does not match {display_path(asset_path, repo_root)}")
    if modalities != {"document", "image"}:
        raise MultimodalPilotError(f"{context}.media_assets must include exactly image and document modalities")


def validate_saved_output_records(
    records: list[dict[str, Any]],
    assets: list[dict[str, Any]],
    context: str,
) -> None:
    asset_ids = {str(asset["asset_id"]) for asset in assets}
    seen_ids: set[str] = set()
    for index, record in enumerate(records):
        record_context = f"{context}.saved_output_records[{index}]"
        record_id = str(record["record_id"])
        if record_id in seen_ids:
            raise MultimodalPilotError(f"{record_context}.record_id duplicate value: {record_id}")
        seen_ids.add(record_id)
        unknown_assets = sorted(set(record["asset_ids"]) - asset_ids)
        if unknown_assets:
            raise MultimodalPilotError(f"{record_context}.asset_ids unknown asset(s): {', '.join(unknown_assets)}")
        if record["review_status"] != "reviewed":
            raise MultimodalPilotError(f"{record_context}.review_status must be reviewed")
        if record["claim_boundary"] != EXPECTED_CLAIM_BOUNDARY:
            raise MultimodalPilotError(f"{record_context}.claim_boundary must preserve pilot-only scope")
        validate_expected_mapping(record["provenance"], EXPECTED_PROVENANCE, f"{record_context}.provenance")


def build_saved_output_records(fixture_set: dict[str, Any], repo_root: Path) -> list[dict[str, Any]]:
    assets_by_id = {asset["asset_id"]: asset for asset in fixture_set["media_assets"]}
    records = []
    for record in fixture_set["saved_output_records"]:
        asset_refs = [
            {
                "asset_id": asset_id,
                "modality": assets_by_id[asset_id]["modality"],
                "media_type": assets_by_id[asset_id]["media_type"],
                "path": assets_by_id[asset_id]["path"],
                "sha256": assets_by_id[asset_id]["sha256"],
            }
            for asset_id in record["asset_ids"]
        ]
        records.append(
            {
                "record_id": record["record_id"],
                "fixture_set_id": fixture_set["fixture_set_id"],
                "created_at": fixture_set["created_at"],
                "evidence_class": fixture_set["evidence_class"],
                "status": fixture_set["status"],
                "asset_refs": asset_refs,
                "prompt": record["prompt"],
                "expected_behavior": record["expected_behavior"],
                "saved_model_output": record["saved_model_output"],
                "target_profile": record["target_profile"],
                "source_label": record["source_label"],
                "review_status": record["review_status"],
                "review_notes": record["review_notes"],
                "claim_boundary": record["claim_boundary"],
                "provenance": record["provenance"],
                "pilot_not_broad_multimodal_coverage": fixture_set["pilot_not_broad_multimodal_coverage"],
                "source_fixture_path": display_path(FIXTURE_SET_PATH, repo_root),
            }
        )
    return records


def build_review_summary(
    fixture_set: dict[str, Any],
    saved_outputs: list[dict[str, Any]],
    repo_root: Path,
) -> dict[str, Any]:
    modalities = sorted({asset["modality"] for asset in fixture_set["media_assets"]})
    return {
        "summary_id": "m107e_multimodal_pilot_review_summary",
        "generated_at": GENERATED_AT,
        "fixture_set_id": fixture_set["fixture_set_id"],
        "evidence_class": fixture_set["evidence_class"],
        "media_asset_count": len(fixture_set["media_assets"]),
        "modalities": modalities,
        "saved_output_record_count": len(saved_outputs),
        "reviewed_record_count": sum(1 for record in saved_outputs if record["review_status"] == "reviewed"),
        "customer_media_count": sum(1 for asset in fixture_set["media_assets"] if asset["customer_media"] is True),
        "private_data_asset_count": sum(1 for asset in fixture_set["media_assets"] if asset["contains_private_data"] is True),
        "live_model_execution_in_quality_gate": fixture_set["live_model_execution_in_quality_gate"],
        "provider_calls_in_quality_gate": fixture_set["provider_calls_in_quality_gate"],
        "pilot_not_broad_multimodal_coverage": fixture_set["pilot_not_broad_multimodal_coverage"],
        "claim_boundary": EXPECTED_CLAIM_BOUNDARY,
        "source_paths": [
            display_path(FIXTURE_SET_PATH, repo_root),
            *[asset["path"] for asset in fixture_set["media_assets"]],
            fixture_set["outputs"]["saved_outputs_path"],
        ],
    }


def build_report_json(
    fixture_set: dict[str, Any],
    saved_outputs: list[dict[str, Any]],
    review_summary: dict[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    return {
        "report_id": "m107e_multimodal_pilot",
        "generated_at": GENERATED_AT,
        "fixture_set_id": fixture_set["fixture_set_id"],
        "evidence_class": fixture_set["evidence_class"],
        "status": fixture_set["status"],
        "media_asset_count": review_summary["media_asset_count"],
        "modalities": review_summary["modalities"],
        "saved_output_record_count": review_summary["saved_output_record_count"],
        "reviewed_record_count": review_summary["reviewed_record_count"],
        "customer_media_count": review_summary["customer_media_count"],
        "private_data_asset_count": review_summary["private_data_asset_count"],
        "live_model_execution_in_quality_gate": fixture_set["live_model_execution_in_quality_gate"],
        "provider_calls_in_quality_gate": fixture_set["provider_calls_in_quality_gate"],
        "pilot_not_broad_multimodal_coverage": fixture_set["pilot_not_broad_multimodal_coverage"],
        "claim_boundary": EXPECTED_CLAIM_BOUNDARY,
        "limitations": [
            "Synthetic public-safe image/document fixture set only.",
            "Saved outputs are reviewed fixture records, not live provider or model execution proof.",
            "The pilot does not claim broad multimodal coverage, production safety, compliance, or customer readiness.",
            "No customer media, private data, credentials, raw logs, tools, network calls, or external actions are used.",
        ],
        "safety_assertions": fixture_set["safety_assertions"],
        "source_paths": review_summary["source_paths"],
        "records": [
            {
                "record_id": record["record_id"],
                "asset_count": len(record["asset_refs"]),
                "modalities": sorted({asset["modality"] for asset in record["asset_refs"]}),
                "review_status": record["review_status"],
                "claim_boundary": record["claim_boundary"],
            }
            for record in saved_outputs
        ],
        "report_paths": [
            fixture_set["outputs"]["report_json_path"],
            fixture_set["outputs"]["report_markdown_path"],
        ],
        "review_summary_path": fixture_set["outputs"]["review_summary_path"],
    }


def render_report_markdown(report: dict[str, Any]) -> str:
    rows = [
        ("Generated at", report["generated_at"]),
        ("Evidence class", f"`{report['evidence_class']}`"),
        ("Media assets", str(report["media_asset_count"])),
        ("Modalities", ", ".join(f"`{item}`" for item in report["modalities"])),
        ("Saved output records", str(report["saved_output_record_count"])),
        ("Reviewed records", str(report["reviewed_record_count"])),
        ("Customer media", str(report["customer_media_count"])),
        ("Private data assets", str(report["private_data_asset_count"])),
        ("Live model execution in gate", str(report["live_model_execution_in_quality_gate"]).lower()),
        ("Provider calls in gate", str(report["provider_calls_in_quality_gate"]).lower()),
        ("Pilot only", str(report["pilot_not_broad_multimodal_coverage"]).lower()),
    ]
    lines = [
        "# M107E Multimodal Pilot Report",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
    ]
    lines.extend(f"| {label} | {value} |" for label, value in rows)
    lines.extend(
        [
            "",
            "This report summarizes a synthetic public-safe image/document saved-output fixture set. It is pilot evidence for normalization and review boundaries, not production proof or broad multimodal coverage.",
            "",
            "## Records",
            "",
            "| Record | Assets | Modalities | Review Status |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for record in report["records"]:
        modalities = ", ".join(f"`{item}`" for item in record["modalities"])
        lines.append(f"| `{record['record_id']}` | {record['asset_count']} | {modalities} | `{record['review_status']}` |")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            f"- Claim boundary: {report['claim_boundary']}",
        ]
    )
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    lines.extend(
        [
            "",
            "## Sources",
            "",
        ]
    )
    lines.extend(f"- `{path}`" for path in report["source_paths"])
    return "\n".join(lines) + "\n"


def resolve_output_paths(outputs: dict[str, str], repo_root: Path) -> dict[str, Path]:
    output_paths = {
        field: require_repo_path(value, f"outputs.{field}", repo_root)
        for field, value in outputs.items()
    }
    require_path_under(output_paths["saved_outputs_path"], repo_root / "traces/external", "outputs.saved_outputs_path", repo_root)
    require_path_under(output_paths["review_summary_path"], repo_root / "traces/external", "outputs.review_summary_path", repo_root)
    require_path_under(output_paths["report_json_path"], repo_root / "reports/comparisons", "outputs.report_json_path", repo_root)
    require_path_under(
        output_paths["report_markdown_path"],
        repo_root / "reports/comparisons",
        "outputs.report_markdown_path",
        repo_root,
    )
    if output_paths["saved_outputs_path"].suffix != ".jsonl":
        raise MultimodalPilotError("outputs.saved_outputs_path must point to JSONL")
    if output_paths["review_summary_path"].suffix != ".json":
        raise MultimodalPilotError("outputs.review_summary_path must point to JSON")
    if output_paths["report_json_path"].suffix != ".json":
        raise MultimodalPilotError("outputs.report_json_path must point to JSON")
    if output_paths["report_markdown_path"].suffix != ".md":
        raise MultimodalPilotError("outputs.report_markdown_path must point to Markdown")
    return output_paths


def validate_expected_mapping(actual: dict[str, Any], expected: dict[str, bool], context: str) -> None:
    for field, expected_value in expected.items():
        if actual.get(field) is not expected_value:
            raise MultimodalPilotError(f"{context}.{field} must be {str(expected_value).lower()}")


def require_repo_path(value: str, context: str, repo_root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise MultimodalPilotError(f"{context} must be a repository-relative path")
    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise MultimodalPilotError(f"{context} must stay inside the repository") from exc
    return resolved


def require_path_under(path: Path, root: Path, context: str, repo_root: Path) -> None:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise MultimodalPilotError(
            f"{context} must be under {display_path(root, repo_root)}; got {display_path(path, repo_root)}"
        ) from exc


def scan_for_forbidden_content(value: Any, context: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            scan_for_forbidden_content(child, f"{context}.{key}")
        return
    if isinstance(value, list):
        for index, child in enumerate(value):
            scan_for_forbidden_content(child, f"{context}[{index}]")
        return
    if isinstance(value, str):
        lowered = value.lower()
        for marker in FORBIDDEN_CONTENT_MARKERS:
            if marker in lowered:
                raise MultimodalPilotError(f"{context} contains private, customer, credential, or local-path content")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the M107E multimodal pilot fixture report.")
    parser.add_argument("fixture_set", nargs="?", type=Path, default=FIXTURE_SET_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = generate_multimodal_pilot(args.fixture_set)
    except (MultimodalPilotError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"multimodal fixture set: {summary['fixture_set_path']}")
    print(f"multimodal schema: {summary['schema_path']}")
    print(f"media assets: {summary['media_asset_count']}")
    print(f"modalities: {', '.join(summary['modalities'])}")
    print(f"saved output records: {summary['saved_output_record_count']}")
    print(f"reviewed records: {summary['reviewed_record_count']}")
    print(f"customer media: {summary['customer_media_count']}")
    print(f"saved outputs path: {summary['saved_outputs_path']}")
    print(f"review summary path: {summary['review_summary_path']}")
    print(f"report JSON path: {summary['report_json_path']}")
    print(f"report Markdown path: {summary['report_markdown_path']}")
    print("m107e multimodal pilot generation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
