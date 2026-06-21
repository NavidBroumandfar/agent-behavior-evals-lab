"""Validate the M67 redaction and promotion pipeline.

M67 validates public-safe promoted derivatives from private-evidence metadata.
It reads committed fake metadata, redaction notes, and promoted public-safe
adapter outputs only. It does not ingest private evidence, read raw private
artifacts, handle credentials, run models, execute agents, call providers, or
perform external actions.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from private_evidence_vault import validate_private_evidence_manifest
from reporting_utils import write_json_object, write_text
from schema_validation_utils import display_path, load_json_object, validate_schema_value
from validate_adapter_outputs import load_adapter_output_records


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE_PATH = REPO_ROOT / "traces/external/redaction_promotion_candidates.example.json"
DEFAULT_CANDIDATE_SCHEMA_PATH = REPO_ROOT / "schemas/promotion_candidate.schema.json"
DEFAULT_REDACTION_NOTE_SCHEMA_PATH = REPO_ROOT / "schemas/redaction_note.schema.json"
DEFAULT_SUMMARY_JSON_PATH = REPO_ROOT / "reports/comparisons/redaction_promotion_pipeline_summary.json"
DEFAULT_SUMMARY_REPORT_PATH = REPO_ROOT / "reports/comparisons/redaction_promotion_pipeline_summary.md"
GENERATED_AT = "2026-06-21T00:00:00Z"

EXPECTED_CHECKLIST = {
    "source_record_in_private_vault": True,
    "original_artifact_local_only": True,
    "redaction_note_present": True,
    "reviewer_signoff_present": True,
    "public_safety_assertions_present": True,
    "promoted_output_validates": True,
    "no_raw_private_values_retained": True,
    "no_hidden_prompts_retained": True,
    "no_private_paths_retained": True,
    "no_credentials_retained": True,
}
EXPECTED_QUALITY_GATE = {
    "deterministic_gate_validates_public_safe_derivatives_only": True,
    "private_evidence_ingestion_in_quality_gate": False,
    "raw_private_data_read_in_quality_gate": False,
    "live_execution_in_quality_gate": False,
    "credential_handling_in_quality_gate": False,
    "provider_calls_in_quality_gate": False,
    "external_actions_in_quality_gate": False,
    "writes_private_data_to_committed_fixtures": False,
}
EXPECTED_SAFETY = {
    "public_safe": True,
    "promoted_derivatives_only": True,
    "source_private_metadata_only": True,
    "contains_private_data": False,
    "credentials_required": False,
    "raw_private_logs": False,
    "private_workspace_paths": False,
    "hidden_prompts": False,
    "account_data": False,
    "real_customer_data": False,
    "live_execution": False,
    "external_actions": False,
}
EXPECTED_CANDIDATE_SAFETY = {
    "public_safe": True,
    "contains_secrets": False,
    "contains_account_data": False,
    "contains_private_paths": False,
    "contains_hidden_prompts": False,
    "contains_raw_runtime_logs": False,
    "contains_real_customer_data": False,
    "external_actions": False,
    "live_execution": False,
}
EXPECTED_NOTE_SAFETY = {
    "public_safe": True,
    "no_secret_values": True,
    "no_account_data": True,
    "no_private_paths": True,
    "no_hidden_prompts": True,
    "no_raw_runtime_logs": True,
    "no_real_customer_data": True,
    "original_private_artifact_local_only": True,
    "public_derivative_contains_private_data": False,
}
PROMOTED_OUTPUT_BLOCKED_STRINGS = [
    "private_evidence/",
    "/Users/",
    "\\Users\\",
    "sk-",
    "BEGIN PRIVATE",
    "END PRIVATE",
    "raw_runtime_log",
    "hidden_prompt",
]


class RedactionPromotionPipelineError(Exception):
    """Redaction and promotion validation error."""


def generate_redaction_promotion_summary(
    candidate_path: Path = DEFAULT_CANDIDATE_PATH,
    candidate_schema_path: Path = DEFAULT_CANDIDATE_SCHEMA_PATH,
    redaction_note_schema_path: Path = DEFAULT_REDACTION_NOTE_SCHEMA_PATH,
    summary_json_path: Path | None = None,
    summary_report_path: Path | None = None,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the M67 pipeline and write deterministic public-safe summaries."""

    context = validate_redaction_promotion_pipeline(
        candidate_path,
        candidate_schema_path,
        redaction_note_schema_path,
        repo_root,
    )
    manifest = context["candidate_manifest"]
    summary = build_summary(manifest, context, candidate_path, repo_root)

    json_output = summary_json_path or require_repo_path(
        manifest["summary_outputs"]["json_path"],
        f"{display_path(candidate_path, repo_root)}.summary_outputs.json_path",
        repo_root,
    )
    report_output = summary_report_path or require_repo_path(
        manifest["summary_outputs"]["markdown_path"],
        f"{display_path(candidate_path, repo_root)}.summary_outputs.markdown_path",
        repo_root,
    )
    validate_summary_output_path(json_output, "json_path", repo_root)
    validate_summary_output_path(report_output, "markdown_path", repo_root)

    write_json_object(summary, json_output)
    write_text(generate_markdown(summary), report_output)
    return summary


def validate_redaction_promotion_pipeline(
    candidate_path: Path = DEFAULT_CANDIDATE_PATH,
    candidate_schema_path: Path = DEFAULT_CANDIDATE_SCHEMA_PATH,
    redaction_note_schema_path: Path = DEFAULT_REDACTION_NOTE_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate promotion candidates, redaction notes, and promoted outputs."""

    candidate_manifest = load_and_validate_candidate_manifest(candidate_path, candidate_schema_path, repo_root)
    context = display_path(candidate_path, repo_root)
    source_vault_path = require_existing_repo_path(
        candidate_manifest["source_vault_manifest_path"],
        f"{context}.source_vault_manifest_path",
        repo_root,
    )
    source_vault = validate_private_evidence_manifest(source_vault_path, repo_root=repo_root)

    redaction_notes_path = require_existing_repo_path(
        candidate_manifest["redaction_notes_path"],
        f"{context}.redaction_notes_path",
        repo_root,
    )
    promoted_output_path = require_existing_repo_path(
        candidate_manifest["promoted_output_path"],
        f"{context}.promoted_output_path",
        repo_root,
    )

    redaction_notes = load_redaction_notes(redaction_notes_path, redaction_note_schema_path, repo_root)
    promoted_records = load_adapter_output_records(promoted_output_path)

    validate_manifest_semantics(candidate_manifest, context, repo_root)
    validate_candidate_links(candidate_manifest, source_vault, redaction_notes, promoted_records, context, repo_root)
    validate_promoted_records(promoted_records, candidate_manifest, context)

    return {
        "candidate_manifest": candidate_manifest,
        "source_vault_manifest": source_vault,
        "redaction_notes": redaction_notes,
        "promoted_records": promoted_records,
        "redaction_notes_path": display_path(redaction_notes_path, repo_root),
        "promoted_output_path": display_path(promoted_output_path, repo_root),
    }


def load_and_validate_candidate_manifest(
    candidate_path: Path,
    candidate_schema_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    schema = load_json_object(candidate_schema_path, "promotion candidate schema", repo_root, RedactionPromotionPipelineError)
    manifest = load_json_object(candidate_path, "promotion candidate manifest", repo_root, RedactionPromotionPipelineError)
    context = display_path(candidate_path, repo_root)
    validate_schema_value(manifest, schema, context, candidate_path, repo_root, RedactionPromotionPipelineError)
    validate_utc_timestamp(manifest["created_at"], f"{context}.created_at")
    return manifest


def load_redaction_notes(
    redaction_notes_path: Path,
    redaction_note_schema_path: Path,
    repo_root: Path,
) -> list[dict[str, Any]]:
    schema = load_json_object(
        redaction_note_schema_path,
        "redaction note schema",
        repo_root,
        RedactionPromotionPipelineError,
    )
    notes: list[dict[str, Any]] = []
    with redaction_notes_path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                note = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise RedactionPromotionPipelineError(
                    f"{display_path(redaction_notes_path, repo_root)}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc
            if not isinstance(note, dict):
                raise RedactionPromotionPipelineError(
                    f"{display_path(redaction_notes_path, repo_root)}:{line_number}: note must be an object"
                )
            validate_schema_value(
                note,
                schema,
                f"{display_path(redaction_notes_path, repo_root)}:{line_number}",
                redaction_notes_path,
                repo_root,
                RedactionPromotionPipelineError,
            )
            validate_utc_timestamp(note["created_at"], f"{display_path(redaction_notes_path, repo_root)}:{line_number}.created_at")
            notes.append(note)

    if not notes:
        raise RedactionPromotionPipelineError(f"{display_path(redaction_notes_path, repo_root)} contains no notes")
    return notes


def validate_manifest_semantics(manifest: dict[str, Any], context: str, repo_root: Path) -> None:
    if manifest["status"] != "public_safe_promotion_fixture":
        raise RedactionPromotionPipelineError(f"{context}.status must be public_safe_promotion_fixture")
    validate_expected_map(manifest["redaction_checklist"], EXPECTED_CHECKLIST, f"{context}.redaction_checklist")
    validate_expected_map(manifest["quality_gate"], EXPECTED_QUALITY_GATE, f"{context}.quality_gate")
    validate_expected_map(manifest["safety_assertions"], EXPECTED_SAFETY, f"{context}.safety_assertions")

    redaction_notes_path = require_repo_path(manifest["redaction_notes_path"], f"{context}.redaction_notes_path", repo_root)
    promoted_output_path = require_repo_path(manifest["promoted_output_path"], f"{context}.promoted_output_path", repo_root)
    require_path_under(redaction_notes_path, repo_root / "traces/external", f"{context}.redaction_notes_path")
    require_path_under(promoted_output_path, repo_root / "traces/external", f"{context}.promoted_output_path")
    if not redaction_notes_path.name.endswith(".example.jsonl"):
        raise RedactionPromotionPipelineError(f"{context}.redaction_notes_path must end with .example.jsonl")
    if not promoted_output_path.name.endswith(".example.jsonl"):
        raise RedactionPromotionPipelineError(f"{context}.promoted_output_path must end with .example.jsonl")


def validate_candidate_links(
    manifest: dict[str, Any],
    source_vault: dict[str, Any],
    redaction_notes: list[dict[str, Any]],
    promoted_records: list[dict[str, Any]],
    context: str,
    repo_root: Path,
) -> None:
    private_records_by_id = {record["record_id"]: record for record in source_vault["private_records"]}
    notes_by_id = {}
    for note in redaction_notes:
        note_id = note["note_id"]
        if note_id in notes_by_id:
            raise RedactionPromotionPipelineError(f"duplicate redaction note id: {note_id}")
        notes_by_id[note_id] = note

    promoted_records_by_id = {}
    for record in promoted_records:
        record_id = record["record_id"]
        if record_id in promoted_records_by_id:
            raise RedactionPromotionPipelineError(f"duplicate promoted record id: {record_id}")
        promoted_records_by_id[record_id] = record

    seen_candidate_ids: set[str] = set()
    for index, candidate in enumerate(manifest["candidates"]):
        candidate_context = f"{context}.candidates[{index}]"
        candidate_id = candidate["candidate_id"]
        if candidate_id in seen_candidate_ids:
            raise RedactionPromotionPipelineError(f"{candidate_context}.candidate_id duplicate value: {candidate_id}")
        seen_candidate_ids.add(candidate_id)

        validate_expected_map(candidate["safety_assertions"], EXPECTED_CANDIDATE_SAFETY, f"{candidate_context}.safety_assertions")

        private_record = private_records_by_id.get(candidate["source_private_record_id"])
        if private_record is None:
            raise RedactionPromotionPipelineError(
                f"{candidate_context}.source_private_record_id must reference the source vault manifest"
            )
        if candidate["source_artifact_path"] != private_record["artifact_path"]:
            raise RedactionPromotionPipelineError(f"{candidate_context}.source_artifact_path must match private vault metadata")
        source_artifact_path = require_repo_path(candidate["source_artifact_path"], f"{candidate_context}.source_artifact_path", repo_root)
        require_path_under(source_artifact_path, repo_root / "private_evidence", f"{candidate_context}.source_artifact_path")
        if ".local." not in source_artifact_path.name:
            raise RedactionPromotionPipelineError(f"{candidate_context}.source_artifact_path must stay local-only")

        note = notes_by_id.get(candidate["redaction_note_id"])
        if note is None:
            raise RedactionPromotionPipelineError(f"{candidate_context}.redaction_note_id must reference a redaction note")
        validate_note_matches_candidate(note, candidate, candidate_context, repo_root)

        promoted_record = promoted_records_by_id.get(candidate["promoted_record_id"])
        if promoted_record is None:
            raise RedactionPromotionPipelineError(f"{candidate_context}.promoted_record_id must reference a promoted output record")
        validate_record_matches_candidate(promoted_record, candidate, manifest, candidate_context)


def validate_note_matches_candidate(
    note: dict[str, Any],
    candidate: dict[str, Any],
    context: str,
    repo_root: Path,
) -> None:
    if note["candidate_id"] != candidate["candidate_id"]:
        raise RedactionPromotionPipelineError(f"{context}.redaction_note_id candidate mismatch")
    if note["source_private_record_id"] != candidate["source_private_record_id"]:
        raise RedactionPromotionPipelineError(f"{context}.redaction_note_id source record mismatch")
    if note["reviewer_id"] != candidate["reviewer_id"]:
        raise RedactionPromotionPipelineError(f"{context}.reviewer_id must match redaction note reviewer")
    if note["reviewer_signoff"] is not True or candidate["reviewer_signoff"] is not True:
        raise RedactionPromotionPipelineError(f"{context} promotion requires reviewer sign-off")
    if note["redaction_status"] != "reviewed_public_safe":
        raise RedactionPromotionPipelineError(f"{context}.redaction_note_id must be reviewed_public_safe")
    if note["public_derivative_path"] != candidate["public_safe_derivative_path"]:
        raise RedactionPromotionPipelineError(f"{context}.public_safe_derivative_path must match redaction note")
    if note["original_artifact_reference"]["artifact_path"] != candidate["source_artifact_path"]:
        raise RedactionPromotionPipelineError(f"{context}.source_artifact_path must match redaction note original artifact")

    validate_expected_map(note["safety_assertions"], EXPECTED_NOTE_SAFETY, f"{context}.redaction_note.safety_assertions")
    for action_index, action in enumerate(note["redaction_actions"]):
        if action["raw_value_retained"] is not False:
            raise RedactionPromotionPipelineError(f"{context}.redaction_actions[{action_index}].raw_value_retained must be false")

    derivative_path = require_repo_path(candidate["public_safe_derivative_path"], f"{context}.public_safe_derivative_path", repo_root)
    require_path_under(derivative_path, repo_root / "traces/external", f"{context}.public_safe_derivative_path")


def validate_record_matches_candidate(
    record: dict[str, Any],
    candidate: dict[str, Any],
    manifest: dict[str, Any],
    context: str,
) -> None:
    if candidate["public_safe_derivative_path"] != manifest["promoted_output_path"]:
        raise RedactionPromotionPipelineError(f"{context}.public_safe_derivative_path must match promoted_output_path")
    if record["provenance"]["public_safe"] is not True:
        raise RedactionPromotionPipelineError(f"{context}.promoted_record.provenance.public_safe must be true")
    if record["provenance"]["live_execution"] is not False:
        raise RedactionPromotionPipelineError(f"{context}.promoted_record.provenance.live_execution must be false")
    if record["provenance"]["contains_private_data"] is not False:
        raise RedactionPromotionPipelineError(f"{context}.promoted_record.provenance.contains_private_data must be false")

    details = record.get("provenance_details", {})
    if details.get("data_classification") != "public_safe_fixture":
        raise RedactionPromotionPipelineError(f"{context}.promoted_record must be a public_safe_fixture")
    if details.get("execution_mode") != "saved_output_only":
        raise RedactionPromotionPipelineError(f"{context}.promoted_record execution_mode must be saved_output_only")

    redaction_metadata = record.get("metadata", {}).get("redaction", {})
    expected_metadata = {
        "source_private_record_id": candidate["source_private_record_id"],
        "redaction_note_id": candidate["redaction_note_id"],
        "promotion_candidate_id": candidate["candidate_id"],
        "source_evidence_class": "private_audit",
        "target_evidence_class": "promoted_public_evidence",
        "original_private_artifact_local_only": True,
        "reviewer_signoff": True,
        "public_ranking_eligible": False,
    }
    for field_name, expected_value in expected_metadata.items():
        if redaction_metadata.get(field_name) != expected_value:
            raise RedactionPromotionPipelineError(
                f"{context}.promoted_record.metadata.redaction.{field_name} must equal {expected_value!r}"
            )


def validate_promoted_records(
    promoted_records: list[dict[str, Any]],
    manifest: dict[str, Any],
    context: str,
) -> None:
    candidate_record_ids = {candidate["promoted_record_id"] for candidate in manifest["candidates"]}
    promoted_record_ids = {record["record_id"] for record in promoted_records}
    if promoted_record_ids != candidate_record_ids:
        missing = sorted(candidate_record_ids - promoted_record_ids)
        extra = sorted(promoted_record_ids - candidate_record_ids)
        raise RedactionPromotionPipelineError(f"{context}.promoted_output records mismatch; missing={missing}, extra={extra}")

    for record in promoted_records:
        public_text = json.dumps(record, sort_keys=True)
        for blocked in PROMOTED_OUTPUT_BLOCKED_STRINGS:
            if blocked in public_text:
                raise RedactionPromotionPipelineError(
                    f"{context}.promoted_output contains blocked private marker: {blocked}"
                )


def build_summary(
    manifest: dict[str, Any],
    validation_context: dict[str, Any],
    candidate_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    redaction_notes = validation_context["redaction_notes"]
    promoted_records = validation_context["promoted_records"]
    return {
        "summary_id": "m67_redaction_promotion_pipeline_summary",
        "generated_at": GENERATED_AT,
        "source_candidate_path": display_path(candidate_path, repo_root),
        "source_vault_manifest_path": manifest["source_vault_manifest_path"],
        "redaction_notes_path": manifest["redaction_notes_path"],
        "promoted_output_path": manifest["promoted_output_path"],
        "pipeline_id": manifest["pipeline_id"],
        "status": manifest["status"],
        "candidate_count": len(manifest["candidates"]),
        "redaction_note_count": len(redaction_notes),
        "promoted_record_count": len(promoted_records),
        "reviewer_signoff_count": sum(1 for candidate in manifest["candidates"] if candidate["reviewer_signoff"] is True),
        "promotion_decisions": sorted({candidate["promotion_decision"] for candidate in manifest["candidates"]}),
        "public_ranking_eligible": False,
        "private_artifacts_read": False,
        "private_evidence_ingested": False,
        "redaction_checklist": manifest["redaction_checklist"],
        "quality_gate": manifest["quality_gate"],
        "safety_assertions": manifest["safety_assertions"],
        "boundaries": [
            "Original private artifacts remain under ignored local paths and are not read by the deterministic gate.",
            "Promotion requires reviewer signoff, redaction notes, and public-safety assertions.",
            "Promoted outputs validate as public-safe adapter-output records.",
            "Promoted private evidence is not public ranking evidence by default.",
            "No credentials, account data, private paths, hidden prompts, raw runtime logs, real customer data, live execution, provider calls, or external actions are introduced.",
        ],
    }


def generate_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Redaction And Promotion Pipeline Summary",
        "",
        "## Summary",
        "",
        "This M67 report validates public-safe promoted derivatives from fake private evidence metadata. It does not read private artifacts or perform private evidence ingestion.",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Generated at | `{summary['generated_at']}` |",
        f"| Candidate manifest | `{summary['source_candidate_path']}` |",
        f"| Redaction notes | `{summary['redaction_notes_path']}` |",
        f"| Promoted output | `{summary['promoted_output_path']}` |",
        f"| Candidates | {summary['candidate_count']} |",
        f"| Redaction notes | {summary['redaction_note_count']} |",
        f"| Promoted records | {summary['promoted_record_count']} |",
        f"| Reviewer signoffs | {summary['reviewer_signoff_count']} |",
        f"| Private artifacts read | `{str(summary['private_artifacts_read']).lower()}` |",
        f"| Public ranking eligible | `{str(summary['public_ranking_eligible']).lower()}` |",
        "",
        "## Redaction Checklist",
        "",
        "\n".join(
            f"- `{field_name}`: `{str(value).lower()}`"
            for field_name, value in summary["redaction_checklist"].items()
        ),
        "",
        "## Boundaries",
        "",
        "\n".join(f"- {boundary}" for boundary in summary["boundaries"]),
        "",
    ]
    return "\n".join(lines)


def validate_expected_map(value: dict[str, Any], expected: dict[str, Any], context: str) -> None:
    for field_name, expected_value in expected.items():
        if value[field_name] != expected_value:
            raise RedactionPromotionPipelineError(f"{context}.{field_name} must equal {expected_value!r}")


def validate_utc_timestamp(value: str, context: str) -> None:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise RedactionPromotionPipelineError(f"{context} must be a UTC timestamp like 2026-06-21T00:00:00Z") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise RedactionPromotionPipelineError(f"{context} must be canonical UTC timestamp text")


def validate_summary_output_path(path: Path, context: str, repo_root: Path) -> None:
    require_path_under(path, repo_root / "reports/comparisons", context)
    if context == "json_path" and path.suffix != ".json":
        raise RedactionPromotionPipelineError(f"{context} must point to a JSON file")
    if context == "markdown_path" and path.suffix != ".md":
        raise RedactionPromotionPipelineError(f"{context} must point to a Markdown file")


def require_existing_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    path = require_repo_path(value, context, repo_root)
    if not path.exists():
        raise RedactionPromotionPipelineError(f"{context} does not exist: {display_path(path, repo_root)}")
    return path


def require_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise RedactionPromotionPipelineError(f"{context} must be a non-empty string")
    path = Path(value)
    if path.is_absolute():
        raise RedactionPromotionPipelineError(f"{context} must be a repository-relative path")
    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise RedactionPromotionPipelineError(f"{context} must stay within the repository") from exc
    return resolved


def require_path_under(path: Path, parent: Path, context: str) -> None:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError as exc:
        raise RedactionPromotionPipelineError(f"{context} must stay under {display_path(parent)}") from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the M67 redaction and promotion pipeline.")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DEFAULT_CANDIDATE_PATH,
        help="Promotion candidate manifest path.",
    )
    parser.add_argument(
        "--candidate-schema",
        type=Path,
        default=DEFAULT_CANDIDATE_SCHEMA_PATH,
        help="Promotion candidate schema path.",
    )
    parser.add_argument(
        "--redaction-note-schema",
        type=Path,
        default=DEFAULT_REDACTION_NOTE_SCHEMA_PATH,
        help="Redaction note schema path.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=DEFAULT_SUMMARY_JSON_PATH,
        help="Summary JSON output path.",
    )
    parser.add_argument(
        "--summary-report",
        type=Path,
        default=DEFAULT_SUMMARY_REPORT_PATH,
        help="Summary Markdown output path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = generate_redaction_promotion_summary(
            args.path,
            args.candidate_schema,
            args.redaction_note_schema,
            args.summary_json,
            args.summary_report,
        )
    except (OSError, ValueError, RedactionPromotionPipelineError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"promotion candidate manifest: {summary['source_candidate_path']}")
    print(f"redaction notes: {summary['redaction_note_count']}")
    print(f"promoted records: {summary['promoted_record_count']}")
    print(f"private artifacts read: {str(summary['private_artifacts_read']).lower()}")
    print("redaction promotion pipeline validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
