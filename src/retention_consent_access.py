"""Validate M69 retention, consent, and access controls.

The deterministic quality gate uses fake public-safe private-evidence metadata
only. It validates retention policy metadata, consent/authorization checklist
coverage, local private-store access notes, deletion/export boundaries, and
aggregate evidence-age reporting without reading raw private evidence, handling
credentials, executing agents, calling providers, running models, using
browser/email/network/shell tools, deleting files, exporting private artifacts,
or running gated LLM review.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from private_audit_report import validate_private_audit_report_metadata
from private_evidence_vault import validate_private_evidence_manifest
from reporting_utils import write_json_object, write_text
from schema_validation_utils import display_path, load_json_object, validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METADATA_PATH = REPO_ROOT / "traces/external/retention_consent_access_metadata.example.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/retention_consent_access.schema.json"
DEFAULT_SUMMARY_JSON_PATH = REPO_ROOT / "reports/comparisons/retention_consent_access_summary.json"
DEFAULT_SUMMARY_REPORT_PATH = REPO_ROOT / "reports/comparisons/retention_consent_access_summary.md"
GENERATED_AT = "2026-06-22T00:00:00Z"

EXPECTED_RETENTION_POLICY = {
    "policy_id": "m69_private_runtime_evidence_retention_policy",
    "default_retention_class": "delete_after_review",
    "allowed_retention_classes": ["delete_after_review", "retain_local_until_manually_deleted"],
    "delete_after_review_max_age_days": 30,
    "retain_local_until_manually_deleted_requires_owner_review": True,
    "raw_private_evidence_auto_export": False,
    "public_safe_aggregate_export_after_redaction_only": True,
    "retention_clock_source": "fake_collected_at_metadata",
}
EXPECTED_CONSENT_CHECKLIST = {
    "checklist_id": "m69_consent_authorization_checklist",
    "authorization_required_before_ingestion": True,
    "consent_or_authorization_recorded_per_artifact": True,
    "no_real_subject_or_customer_data_in_fixture": True,
    "revocation_boundary_documented": True,
    "missing_authorization_blocks_ingestion": True,
    "authorization_values_allowed": ["authorized_for_internal_private_audit", "required_before_ingestion"],
}
EXPECTED_ACCESS_NOTES = {
    "store_id": "m69_local_private_store_access_notes",
    "vault_root_gitignored": True,
    "private_report_root_gitignored": True,
    "local_store_access": "local_maintainer_workstation_only",
    "role_required": "authorized_local_auditor",
    "shared_storage_allowed": False,
    "credential_material_committable": False,
    "raw_private_logs_committable": False,
    "private_workspace_paths_committable": False,
}
EXPECTED_DELETION_EXPORT = {
    "boundary_id": "m69_deletion_export_boundary",
    "delete_targets_limited_to_ignored_private_roots": True,
    "deletion_command_in_quality_gate": False,
    "private_artifact_export_enabled_by_default": False,
    "public_safe_aggregate_export_enabled": True,
    "aggregate_export_contains_per_record_private_details": False,
    "export_requires_redaction_or_aggregate": True,
    "raw_private_evidence_export_allowed": False,
}
EXPECTED_OUTPUT_DEFAULTS = {
    "summary_json_path": "reports/comparisons/retention_consent_access_summary.json",
    "summary_markdown_path": "reports/comparisons/retention_consent_access_summary.md",
    "public_safe": True,
    "aggregate_only": True,
    "private_record_values_included": False,
}
EXPECTED_QUALITY_GATE = {
    "deterministic_gate_uses_fake_metadata_only": True,
    "private_evidence_ingestion_in_quality_gate": False,
    "raw_private_data_read_in_quality_gate": False,
    "live_execution_in_quality_gate": False,
    "credential_handling_in_quality_gate": False,
    "provider_calls_in_quality_gate": False,
    "browser_email_network_shell_actions_in_quality_gate": False,
    "external_actions_in_quality_gate": False,
    "deletion_actions_in_quality_gate": False,
    "export_actions_in_quality_gate": False,
    "gated_llm_review_in_quality_gate": False,
}
EXPECTED_SAFETY = {
    "public_safe_input_metadata": True,
    "fake_metadata_only": True,
    "contains_raw_private_evidence": False,
    "contains_credentials_or_secrets": False,
    "contains_private_workspace_paths": False,
    "contains_real_customer_data": False,
    "contains_raw_private_logs": False,
    "live_provider_model_runtime_execution": False,
    "browser_email_network_shell_external_actions": False,
    "public_leaderboard_claim": False,
    "production_safety_claim": False,
    "third_party_reproducibility_claim": False,
    "private_audit_overclaim": False,
}
EXPECTED_RECORD_SAFETY = {
    "public_safe_metadata": True,
    "raw_private_content_in_manifest": False,
    "credentials_in_manifest": False,
    "raw_private_log_in_manifest": False,
    "private_workspace_path_in_manifest": False,
    "real_customer_data_in_manifest": False,
    "external_action_in_manifest": False,
}
BLOCKED_PUBLIC_SUMMARY_MARKERS = [
    "/Users/",
    "\\Users\\",
    "sk-",
    "BEGIN PRIVATE",
    "END PRIVATE",
    "raw_runtime_log",
    "hidden_prompt",
]


class RetentionConsentAccessError(Exception):
    """Retention, consent, and access-control validation error."""


def generate_retention_consent_access_summary(
    metadata_path: Path = DEFAULT_METADATA_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    summary_json_path: Path | None = None,
    summary_report_path: Path | None = None,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate metadata and write public-safe aggregate boundary summaries."""

    context = validate_retention_consent_access_metadata(metadata_path, schema_path, repo_root)
    metadata = context["metadata"]
    source_vault = context["source_vault_manifest"]
    source_audit = context["source_private_audit_metadata"]
    summary = build_summary(metadata, source_vault, source_audit, metadata_path, repo_root)
    validate_public_summary(summary, display_path(metadata_path, repo_root))

    json_output = summary_json_path or require_repo_path(
        metadata["output_defaults"]["summary_json_path"],
        f"{display_path(metadata_path, repo_root)}.output_defaults.summary_json_path",
        repo_root,
    )
    report_output = summary_report_path or require_repo_path(
        metadata["output_defaults"]["summary_markdown_path"],
        f"{display_path(metadata_path, repo_root)}.output_defaults.summary_markdown_path",
        repo_root,
    )
    validate_summary_output_path(json_output, "summary_json_path", repo_root)
    validate_summary_output_path(report_output, "summary_markdown_path", repo_root)

    write_json_object(summary, json_output)
    write_text(generate_markdown(summary), report_output)
    return summary


def validate_retention_consent_access_metadata(
    metadata_path: Path = DEFAULT_METADATA_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate fake public-safe retention, consent, and access metadata."""

    schema = load_json_object(schema_path, "retention consent access schema", repo_root, RetentionConsentAccessError)
    metadata = load_json_object(metadata_path, "retention consent access metadata", repo_root, RetentionConsentAccessError)
    context = display_path(metadata_path, repo_root)
    validate_schema_value(metadata, schema, context, metadata_path, repo_root, RetentionConsentAccessError)
    validate_utc_timestamp(metadata["created_at"], f"{context}.created_at")

    source_vault_path = require_existing_repo_path(
        metadata["source_vault_manifest_path"],
        f"{context}.source_vault_manifest_path",
        repo_root,
    )
    source_audit_path = require_existing_repo_path(
        metadata["source_private_audit_metadata_path"],
        f"{context}.source_private_audit_metadata_path",
        repo_root,
    )
    source_vault = validate_private_evidence_manifest(source_vault_path, repo_root=repo_root)
    source_audit_context = validate_private_audit_report_metadata(source_audit_path, repo_root=repo_root)
    source_audit = source_audit_context["metadata"]

    validate_metadata_semantics(metadata, source_vault, source_audit, context, repo_root)
    return {
        "metadata": metadata,
        "source_vault_manifest": source_vault,
        "source_private_audit_metadata": source_audit,
    }


def validate_metadata_semantics(
    metadata: dict[str, Any],
    source_vault: dict[str, Any],
    source_audit: dict[str, Any],
    context: str,
    repo_root: Path,
) -> None:
    if metadata["status"] != "public_safe_retention_consent_access_fixture":
        raise RetentionConsentAccessError(f"{context}.status must be public_safe_retention_consent_access_fixture")
    if metadata["metadata_classification"] != "public_safe_fake_private_metadata":
        raise RetentionConsentAccessError(f"{context}.metadata_classification must be public_safe_fake_private_metadata")

    if source_audit["source_vault_manifest_path"] != metadata["source_vault_manifest_path"]:
        raise RetentionConsentAccessError(
            f"{context}.source_private_audit_metadata_path must reference the same source vault manifest"
        )
    if source_audit["report_label"] != "private_audit_report":
        raise RetentionConsentAccessError(f"{context}.source_private_audit_metadata_path must be private_audit_report")

    validate_expected_map(metadata["retention_policy"], EXPECTED_RETENTION_POLICY, f"{context}.retention_policy")
    validate_utc_timestamp(metadata["retention_policy"]["evidence_age_as_of"], f"{context}.retention_policy.evidence_age_as_of")
    validate_expected_map(
        metadata["consent_authorization_checklist"],
        EXPECTED_CONSENT_CHECKLIST,
        f"{context}.consent_authorization_checklist",
    )
    validate_access_control_notes(metadata["access_control_notes"], source_vault, source_audit, context, repo_root)
    validate_deletion_export_boundaries(metadata["deletion_export_boundaries"], metadata, context, repo_root)
    validate_output_defaults(metadata["output_defaults"], context, repo_root)
    validate_expected_map(metadata["quality_gate"], EXPECTED_QUALITY_GATE, f"{context}.quality_gate")
    validate_expected_map(metadata["safety_assertions"], EXPECTED_SAFETY, f"{context}.safety_assertions")
    validate_record_controls(metadata["record_controls"], metadata, source_vault, source_audit, context, repo_root)


def validate_access_control_notes(
    value: dict[str, Any],
    source_vault: dict[str, Any],
    source_audit: dict[str, Any],
    context: str,
    repo_root: Path,
) -> None:
    validate_expected_map(value, EXPECTED_ACCESS_NOTES, f"{context}.access_control_notes")
    if value["vault_root"] != source_vault["vault_controls"]["vault_root"]:
        raise RetentionConsentAccessError(f"{context}.access_control_notes.vault_root must match source vault")
    if value["private_report_root"] != source_vault["vault_controls"]["private_reports_root"]:
        raise RetentionConsentAccessError(f"{context}.access_control_notes.private_report_root must match source vault")
    if value["private_report_root"] != source_audit["output_defaults"]["private_report_root"]:
        raise RetentionConsentAccessError(
            f"{context}.access_control_notes.private_report_root must match source private audit metadata"
        )

    gitignore_path = require_existing_repo_path(value["gitignore_path"], f"{context}.access_control_notes.gitignore_path", repo_root)
    require_gitignore_pattern(gitignore_path, value["vault_root"], f"{context}.access_control_notes.vault_root")
    require_gitignore_pattern(gitignore_path, value["private_report_root"], f"{context}.access_control_notes.private_report_root")

    vault_root = require_repo_path(value["vault_root"], f"{context}.access_control_notes.vault_root", repo_root)
    private_report_root = require_repo_path(
        value["private_report_root"],
        f"{context}.access_control_notes.private_report_root",
        repo_root,
    )
    require_path_under(vault_root, repo_root, f"{context}.access_control_notes.vault_root", allow_equal=False)
    require_path_under(
        private_report_root,
        repo_root / "reports",
        f"{context}.access_control_notes.private_report_root",
        allow_equal=False,
    )


def validate_deletion_export_boundaries(
    value: dict[str, Any],
    metadata: dict[str, Any],
    context: str,
    repo_root: Path,
) -> None:
    validate_expected_map(value, EXPECTED_DELETION_EXPORT, f"{context}.deletion_export_boundaries")
    if value["aggregate_export_path"] != metadata["output_defaults"]["summary_json_path"]:
        raise RetentionConsentAccessError(
            f"{context}.deletion_export_boundaries.aggregate_export_path must match output_defaults.summary_json_path"
        )
    aggregate_export_path = require_repo_path(
        value["aggregate_export_path"],
        f"{context}.deletion_export_boundaries.aggregate_export_path",
        repo_root,
    )
    validate_summary_output_path(aggregate_export_path, "summary_json_path", repo_root)


def validate_output_defaults(value: dict[str, Any], context: str, repo_root: Path) -> None:
    validate_expected_map(value, EXPECTED_OUTPUT_DEFAULTS, f"{context}.output_defaults")
    validate_summary_output_path(
        require_repo_path(value["summary_json_path"], f"{context}.output_defaults.summary_json_path", repo_root),
        "summary_json_path",
        repo_root,
    )
    validate_summary_output_path(
        require_repo_path(value["summary_markdown_path"], f"{context}.output_defaults.summary_markdown_path", repo_root),
        "summary_markdown_path",
        repo_root,
    )


def validate_record_controls(
    records: list[dict[str, Any]],
    metadata: dict[str, Any],
    source_vault: dict[str, Any],
    source_audit: dict[str, Any],
    context: str,
    repo_root: Path,
) -> None:
    if len(records) != len(source_audit["included_private_record_ids"]):
        raise RetentionConsentAccessError(
            f"{context}.record_controls must cover every private audit metadata record"
        )

    source_records = {record["record_id"]: record for record in source_vault["private_records"]}
    included_record_ids = set(source_audit["included_private_record_ids"])
    seen_record_ids: set[str] = set()
    as_of = parse_utc_timestamp(
        metadata["retention_policy"]["evidence_age_as_of"],
        f"{context}.retention_policy.evidence_age_as_of",
    )
    max_age_days = metadata["retention_policy"]["delete_after_review_max_age_days"]

    for index, record in enumerate(records):
        record_context = f"{context}.record_controls[{index}]"
        record_id = str(record["record_id"])
        if record_id in seen_record_ids:
            raise RetentionConsentAccessError(f"{record_context}.record_id duplicate value: {record_id}")
        seen_record_ids.add(record_id)
        if record_id not in included_record_ids:
            raise RetentionConsentAccessError(f"{record_context}.record_id must reference included private audit records")

        source_record = source_records.get(record_id)
        if source_record is None:
            raise RetentionConsentAccessError(f"{record_context}.record_id must reference source vault private_records")
        validate_source_record_linkage(record, source_record, source_vault, source_audit, record_context)
        validate_record_dates(record, as_of, max_age_days, record_context)
        validate_record_boundaries(record, record_context, repo_root)
        validate_expected_map(record["safety_assertions"], EXPECTED_RECORD_SAFETY, f"{record_context}.safety_assertions")

    missing_record_ids = sorted(included_record_ids - seen_record_ids)
    if missing_record_ids:
        raise RetentionConsentAccessError(
            f"{context}.record_controls missing included private audit records: {', '.join(missing_record_ids)}"
        )


def validate_source_record_linkage(
    record: dict[str, Any],
    source_record: dict[str, Any],
    source_vault: dict[str, Any],
    source_audit: dict[str, Any],
    context: str,
) -> None:
    if record["retention_class"] != source_record["retention_class"]:
        raise RetentionConsentAccessError(f"{context}.retention_class must match source vault record")
    if record["consent_or_authorization"] != source_record["consent_or_authorization"]:
        raise RetentionConsentAccessError(f"{context}.consent_or_authorization must match source vault record")
    if record["access_boundary"] != source_record["access_boundary"]:
        raise RetentionConsentAccessError(f"{context}.access_boundary must match source vault record")
    if record["private_store_root"] != source_vault["vault_controls"]["vault_root"]:
        raise RetentionConsentAccessError(f"{context}.private_store_root must match source vault root")
    if record["private_audit_report_root"] != source_audit["output_defaults"]["private_report_root"]:
        raise RetentionConsentAccessError(f"{context}.private_audit_report_root must match private audit output root")

    if record["consent_or_authorization"] == "required_before_ingestion":
        if record["authorization_check_status"] != "authorization_required_not_embedded":
            raise RetentionConsentAccessError(
                f"{context}.authorization_check_status must flag required authorization without embedding private proof"
            )
    if record["consent_or_authorization"] == "authorized_for_internal_private_audit":
        if record["authorization_check_status"] != "authorization_recorded_public_safe_metadata_only":
            raise RetentionConsentAccessError(
                f"{context}.authorization_check_status must record authorization as public-safe metadata only"
            )


def validate_record_dates(record: dict[str, Any], as_of: datetime, max_age_days: int, context: str) -> None:
    collected_at = parse_utc_timestamp(record["collected_at"], f"{context}.collected_at")
    review_due_at = parse_utc_timestamp(record["review_due_at"], f"{context}.review_due_at")
    if collected_at > as_of:
        raise RetentionConsentAccessError(f"{context}.collected_at must not be after the age report timestamp")
    if review_due_at < collected_at:
        raise RetentionConsentAccessError(f"{context}.review_due_at must not be before collected_at")

    age_days = (as_of - collected_at).days
    if record["age_days_at_boundary_report"] != age_days:
        raise RetentionConsentAccessError(f"{context}.age_days_at_boundary_report must equal computed age {age_days}")

    if record["retention_class"] == "delete_after_review":
        delete_due_at = parse_utc_timestamp(record["delete_due_at"], f"{context}.delete_due_at")
        if delete_due_at < review_due_at:
            raise RetentionConsentAccessError(f"{context}.delete_due_at must not be before review_due_at")
        if (delete_due_at - collected_at).days > max_age_days:
            raise RetentionConsentAccessError(f"{context}.delete_due_at exceeds delete_after_review_max_age_days")
        if record["retention_action"] != "delete_after_review_window":
            raise RetentionConsentAccessError(f"{context}.retention_action must be delete_after_review_window")
        return

    if record["delete_due_at"] != "manual_review_required":
        raise RetentionConsentAccessError(f"{context}.delete_due_at must be manual_review_required")
    if record["retention_action"] != "manual_delete_review_required":
        raise RetentionConsentAccessError(f"{context}.retention_action must be manual_delete_review_required")


def validate_record_boundaries(record: dict[str, Any], context: str, repo_root: Path) -> None:
    for field_name in [
        "raw_private_evidence_read",
        "private_artifact_path_in_report",
        "public_ranking_eligible",
    ]:
        if record[field_name] is not False:
            raise RetentionConsentAccessError(f"{context}.{field_name} must be false")

    private_store_root = require_repo_path(record["private_store_root"], f"{context}.private_store_root", repo_root)
    private_audit_report_root = require_repo_path(
        record["private_audit_report_root"],
        f"{context}.private_audit_report_root",
        repo_root,
    )
    require_path_under(private_store_root, repo_root, f"{context}.private_store_root", allow_equal=False)
    require_path_under(private_audit_report_root, repo_root / "reports", f"{context}.private_audit_report_root", allow_equal=False)
    require_gitignore_pattern(repo_root / ".gitignore", record["private_store_root"], f"{context}.private_store_root")
    require_gitignore_pattern(repo_root / ".gitignore", record["private_audit_report_root"], f"{context}.private_audit_report_root")


def build_summary(
    metadata: dict[str, Any],
    source_vault: dict[str, Any],
    source_audit: dict[str, Any],
    metadata_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    """Build committed public-safe aggregate retention/access summary metadata."""

    records = metadata["record_controls"]
    retention_class_counts = Counter(record["retention_class"] for record in records)
    retention_action_counts = Counter(record["retention_action"] for record in records)
    authorization_status_counts = Counter(record["authorization_check_status"] for record in records)
    access_boundary_counts = Counter(record["access_boundary"] for record in records)
    record_ages = [record["age_days_at_boundary_report"] for record in records]

    return {
        "summary_id": "m69_retention_consent_access_summary",
        "generated_at": GENERATED_AT,
        "source_metadata_path": display_path(metadata_path, repo_root),
        "schema_path": display_path(DEFAULT_SCHEMA_PATH, repo_root),
        "source_vault_manifest_path": metadata["source_vault_manifest_path"],
        "source_private_audit_metadata_path": metadata["source_private_audit_metadata_path"],
        "public_safe_fake_metadata_only": True,
        "private_artifacts_read": False,
        "deletion_actions_executed": False,
        "private_artifact_exports_executed": False,
        "retention_policy": {
            "policy_id": metadata["retention_policy"]["policy_id"],
            "default_retention_class": metadata["retention_policy"]["default_retention_class"],
            "delete_after_review_max_age_days": metadata["retention_policy"]["delete_after_review_max_age_days"],
            "manual_retention_requires_owner_review": metadata["retention_policy"][
                "retain_local_until_manually_deleted_requires_owner_review"
            ],
            "evidence_age_as_of": metadata["retention_policy"]["evidence_age_as_of"],
        },
        "private_store_boundaries": {
            "vault_root": metadata["access_control_notes"]["vault_root"],
            "private_report_root": metadata["access_control_notes"]["private_report_root"],
            "vault_root_gitignored": metadata["access_control_notes"]["vault_root_gitignored"],
            "private_report_root_gitignored": metadata["access_control_notes"]["private_report_root_gitignored"],
            "local_store_access": metadata["access_control_notes"]["local_store_access"],
            "role_required": metadata["access_control_notes"]["role_required"],
            "shared_storage_allowed": metadata["access_control_notes"]["shared_storage_allowed"],
            "raw_private_records_committable": source_vault["vault_controls"]["raw_private_records_committable"],
            "private_reports_committable": source_vault["vault_controls"]["private_reports_committable"],
            "private_audit_report_label": source_audit["report_label"],
        },
        "record_counts": {
            "source_vault_private_record_metadata_count": len(source_vault["private_records"]),
            "included_private_audit_record_metadata_count": len(source_audit["included_private_record_ids"]),
            "retention_control_record_metadata_count": len(records),
            "authorization_required_count": sum(
                1 for record in records if record["consent_or_authorization"] == "required_before_ingestion"
            ),
            "authorization_recorded_count": sum(
                1 for record in records if record["consent_or_authorization"] == "authorized_for_internal_private_audit"
            ),
        },
        "evidence_age_report": {
            "as_of": metadata["retention_policy"]["evidence_age_as_of"],
            "oldest_evidence_age_days": max(record_ages) if record_ages else 0,
            "newest_evidence_age_days": min(record_ages) if record_ages else 0,
            "average_evidence_age_days": round(sum(record_ages) / len(record_ages), 1) if record_ages else 0.0,
            "age_source": metadata["retention_policy"]["retention_clock_source"],
        },
        "aggregate_counts": {
            "retention_classes": dict(sorted(retention_class_counts.items())),
            "retention_actions": dict(sorted(retention_action_counts.items())),
            "authorization_statuses": dict(sorted(authorization_status_counts.items())),
            "access_boundaries": dict(sorted(access_boundary_counts.items())),
        },
        "deletion_export_boundaries": metadata["deletion_export_boundaries"],
        "output_defaults": metadata["output_defaults"],
        "quality_gate": metadata["quality_gate"],
        "safety_assertions": metadata["safety_assertions"],
        "public_leaderboard_eligible": False,
        "production_safety_claim": False,
        "third_party_reproducibility_claim": False,
        "private_audit_overclaim": False,
        "boundaries": [
            "Committed M69 summaries are aggregate-only and public-safe.",
            "The deterministic gate validates fake metadata only and does not read raw private evidence.",
            "Deletion and private artifact export boundaries are validated as metadata; no deletion or export action is executed.",
            "Private evidence and private audit report roots remain ignored by Git and local-only by default.",
            "Consent or authorization proof is not embedded in committed fixtures.",
            "Evidence age and access-boundary reporting uses fake collected-at metadata and aggregate counts only.",
            "M69 does not create public leaderboard evidence, production-safety proof, third-party reproducibility evidence, or private-audit overclaims.",
        ],
    }


def validate_public_summary(summary: dict[str, Any], context: str) -> None:
    if summary["public_safe_fake_metadata_only"] is not True:
        raise RetentionConsentAccessError(f"{context}.summary.public_safe_fake_metadata_only must be true")
    for field_name in [
        "private_artifacts_read",
        "deletion_actions_executed",
        "private_artifact_exports_executed",
        "public_leaderboard_eligible",
        "production_safety_claim",
        "third_party_reproducibility_claim",
        "private_audit_overclaim",
    ]:
        if summary[field_name] is not False:
            raise RetentionConsentAccessError(f"{context}.summary.{field_name} must be false")

    summary_text = json.dumps(summary, sort_keys=True)
    for blocked in BLOCKED_PUBLIC_SUMMARY_MARKERS:
        if blocked in summary_text:
            raise RetentionConsentAccessError(f"{context}.summary contains blocked private marker: {blocked}")


def generate_markdown(summary: dict[str, Any]) -> str:
    counts = summary["record_counts"]
    age = summary["evidence_age_report"]
    store = summary["private_store_boundaries"]
    deletion_export = summary["deletion_export_boundaries"]
    lines = [
        "# Retention Consent Access Summary",
        "",
        "## Summary",
        "",
        "This M69 summary is public-safe fake metadata only. It validates retention, consent, access-control, deletion, and export boundaries without reading private evidence or performing private actions.",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Generated at | `{summary['generated_at']}` |",
        f"| Source metadata | `{summary['source_metadata_path']}` |",
        f"| Source vault manifest | `{summary['source_vault_manifest_path']}` |",
        f"| Source private audit metadata | `{summary['source_private_audit_metadata_path']}` |",
        f"| Fake metadata only | `{str(summary['public_safe_fake_metadata_only']).lower()}` |",
        f"| Retention-control records | {counts['retention_control_record_metadata_count']} |",
        f"| Authorization required | {counts['authorization_required_count']} |",
        f"| Private artifacts read | `{str(summary['private_artifacts_read']).lower()}` |",
        f"| Deletion actions executed | `{str(summary['deletion_actions_executed']).lower()}` |",
        f"| Private artifact exports executed | `{str(summary['private_artifact_exports_executed']).lower()}` |",
        "",
        "## Evidence Age",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Oldest fake evidence age days | {age['oldest_evidence_age_days']} |",
        f"| Newest fake evidence age days | {age['newest_evidence_age_days']} |",
        f"| Average fake evidence age days | {age['average_evidence_age_days']} |",
        "",
        "## Access Boundary",
        "",
        f"- Vault root ignored: `{str(store['vault_root_gitignored']).lower()}`",
        f"- Private report root ignored: `{str(store['private_report_root_gitignored']).lower()}`",
        f"- Local store access: `{store['local_store_access']}`",
        f"- Required role: `{store['role_required']}`",
        f"- Shared storage allowed: `{str(store['shared_storage_allowed']).lower()}`",
        f"- Private audit report label: `{store['private_audit_report_label']}`",
        "",
        "## Deletion And Export Boundary",
        "",
        f"- Delete targets limited to ignored private roots: `{str(deletion_export['delete_targets_limited_to_ignored_private_roots']).lower()}`",
        f"- Deletion command in quality gate: `{str(deletion_export['deletion_command_in_quality_gate']).lower()}`",
        f"- Private artifact export enabled by default: `{str(deletion_export['private_artifact_export_enabled_by_default']).lower()}`",
        f"- Public-safe aggregate export enabled: `{str(deletion_export['public_safe_aggregate_export_enabled']).lower()}`",
        f"- Per-record private details in aggregate export: `{str(deletion_export['aggregate_export_contains_per_record_private_details']).lower()}`",
        "",
        "## Aggregate Counts",
        "",
        f"- Retention classes: `{summary['aggregate_counts']['retention_classes']}`",
        f"- Retention actions: `{summary['aggregate_counts']['retention_actions']}`",
        f"- Authorization statuses: `{summary['aggregate_counts']['authorization_statuses']}`",
        f"- Access boundaries: `{summary['aggregate_counts']['access_boundaries']}`",
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
            raise RetentionConsentAccessError(f"{context}.{field_name} must equal {expected_value!r}")


def parse_utc_timestamp(value: str, context: str) -> datetime:
    validate_utc_timestamp(value, context)
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def validate_utc_timestamp(value: str, context: str) -> None:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise RetentionConsentAccessError(f"{context} must be a UTC timestamp like 2026-06-22T00:00:00Z") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise RetentionConsentAccessError(f"{context} must be canonical UTC timestamp text")


def validate_summary_output_path(path: Path, context: str, repo_root: Path) -> None:
    require_path_under(path, repo_root / "reports/comparisons", context)
    if context == "summary_json_path" and path.suffix != ".json":
        raise RetentionConsentAccessError(f"{context} must point to a JSON file")
    if context == "summary_markdown_path" and path.suffix != ".md":
        raise RetentionConsentAccessError(f"{context} must point to a Markdown file")


def require_existing_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    path = require_repo_path(value, context, repo_root)
    if not path.exists():
        raise RetentionConsentAccessError(f"{context} does not exist: {display_path(path, repo_root)}")
    return path


def require_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise RetentionConsentAccessError(f"{context} must be a non-empty string")
    path = Path(value)
    if path.is_absolute():
        raise RetentionConsentAccessError(f"{context} must be a repository-relative path")
    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise RetentionConsentAccessError(f"{context} must stay within the repository") from exc
    return resolved


def require_path_under(path: Path, parent: Path, context: str, allow_equal: bool = True) -> None:
    try:
        relative = path.resolve().relative_to(parent.resolve())
    except ValueError as exc:
        raise RetentionConsentAccessError(f"{context} must stay under {display_path(parent)}") from exc
    if not allow_equal and str(relative) == ".":
        raise RetentionConsentAccessError(f"{context} must be a child path under {display_path(parent)}")


def require_gitignore_pattern(gitignore_path: Path, expected_pattern: str, context: str) -> None:
    patterns = {
        line.strip()
        for line in gitignore_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if expected_pattern not in patterns:
        raise RetentionConsentAccessError(f"{context} requires .gitignore pattern {expected_pattern!r}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate M69 retention, consent, and access-control metadata.")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DEFAULT_METADATA_PATH,
        help="Retention, consent, and access-control metadata path.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help="Retention, consent, and access-control schema path.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=DEFAULT_SUMMARY_JSON_PATH,
        help="Public-safe retention/access JSON summary output.",
    )
    parser.add_argument(
        "--summary-report",
        type=Path,
        default=DEFAULT_SUMMARY_REPORT_PATH,
        help="Public-safe retention/access Markdown report output.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = generate_retention_consent_access_summary(
            args.path,
            args.schema,
            args.summary_json,
            args.summary_report,
        )
    except (OSError, ValueError, RetentionConsentAccessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"retention consent access metadata: {summary['source_metadata_path']}")
    print(f"retention-control records: {summary['record_counts']['retention_control_record_metadata_count']}")
    print(f"oldest fake evidence age days: {summary['evidence_age_report']['oldest_evidence_age_days']}")
    print("retention consent access validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
