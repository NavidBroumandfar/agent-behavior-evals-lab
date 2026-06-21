"""Generate M68 private audit report artifacts from metadata.

The deterministic quality gate uses fake public-safe private-evidence metadata
only. It validates the private audit report contract and writes local-only
JSON/Markdown reports under ignored paths by default, plus committed
public-safe aggregate boundary summaries. It does not read raw private
evidence, handle credentials, call providers, execute agents, run models, use
browser/email/network/shell tools, perform external actions, or run gated LLM
review.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from private_evidence_vault import validate_private_evidence_manifest
from reporting_utils import write_json_object, write_text
from schema_validation_utils import display_path, load_json_object, validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METADATA_PATH = REPO_ROOT / "traces/external/private_audit_report_metadata.example.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/private_audit_report.schema.json"
DEFAULT_SUMMARY_JSON_PATH = REPO_ROOT / "reports/comparisons/private_audit_report_boundary_summary.json"
DEFAULT_SUMMARY_REPORT_PATH = REPO_ROOT / "reports/comparisons/private_audit_report_boundary_summary.md"
GENERATED_AT = "2026-06-21T00:00:00Z"

EXPECTED_REPORT_CONTROLS = {
    "private_report_label_required": True,
    "reports_generated_from_private_evidence_marked_private_audit": True,
    "local_only_by_default": True,
    "private_reports_gitignored": True,
    "private_reports_committable": False,
    "report_contains_raw_private_evidence": False,
    "report_contains_credentials_or_secrets": False,
    "report_contains_private_workspace_paths": False,
    "report_contains_real_customer_data": False,
    "gated_llm_review_required": False,
    "public_leaderboard_eligible": False,
    "production_safety_claim": False,
    "third_party_reproducibility_claim": False,
    "private_audit_overclaim": False,
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
    "gated_llm_review_in_quality_gate": False,
}
EXPECTED_SAFETY = {
    "public_safe_input_metadata": True,
    "contains_raw_private_evidence": False,
    "contains_credentials_or_secrets": False,
    "contains_private_workspace_paths": False,
    "contains_real_customer_data": False,
    "live_provider_model_runtime_execution": False,
    "browser_email_network_shell_external_actions": False,
    "public_leaderboard_claim": False,
    "production_safety_claim": False,
    "third_party_reproducibility_claim": False,
    "private_audit_overclaim": False,
}
EXPECTED_AGGREGATE_EXPORT = {
    "enabled_by_default": False,
    "public_safe_by_default": True,
    "aggregate_only": True,
    "per_record_private_details_in_export": False,
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
GENERATED_REPORT_BLOCKED_STRINGS = [
    "private_evidence/",
    "/Users/",
    "\\Users\\",
    "sk-",
    "BEGIN PRIVATE",
    "END PRIVATE",
    "raw_runtime_log",
    "hidden_prompt",
]


class PrivateAuditReportError(Exception):
    """Private audit report validation error."""


def generate_private_audit_report(
    metadata_path: Path = DEFAULT_METADATA_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    summary_json_path: Path | None = None,
    summary_report_path: Path | None = None,
    write_private_outputs: bool = True,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate metadata, write local private reports, and write summaries."""

    context = validate_private_audit_report_metadata(metadata_path, schema_path, repo_root)
    metadata = context["metadata"]
    source_vault = context["source_vault_manifest"]
    private_report = build_private_report(metadata, source_vault, metadata_path, repo_root)
    validate_generated_private_report(private_report, display_path(metadata_path, repo_root))

    private_json_path = require_repo_path(
        metadata["output_defaults"]["json_path"],
        f"{display_path(metadata_path, repo_root)}.output_defaults.json_path",
        repo_root,
    )
    private_markdown_path = require_repo_path(
        metadata["output_defaults"]["markdown_path"],
        f"{display_path(metadata_path, repo_root)}.output_defaults.markdown_path",
        repo_root,
    )
    if write_private_outputs:
        write_json_object(private_report, private_json_path)
        write_text(generate_private_markdown(private_report), private_markdown_path)

    summary = build_summary(
        metadata,
        source_vault,
        private_report,
        metadata_path,
        repo_root,
        private_outputs_written=write_private_outputs,
    )

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
    write_text(generate_summary_markdown(summary), report_output)
    return summary


def validate_private_audit_report_metadata(
    metadata_path: Path = DEFAULT_METADATA_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate fake public-safe private audit report metadata."""

    schema = load_json_object(schema_path, "private audit report schema", repo_root, PrivateAuditReportError)
    metadata = load_json_object(metadata_path, "private audit report metadata", repo_root, PrivateAuditReportError)
    context = display_path(metadata_path, repo_root)
    validate_schema_value(metadata, schema, context, metadata_path, repo_root, PrivateAuditReportError)
    validate_utc_timestamp(metadata["created_at"], f"{context}.created_at")

    source_vault_path = require_existing_repo_path(
        metadata["source_vault_manifest_path"],
        f"{context}.source_vault_manifest_path",
        repo_root,
    )
    source_vault = validate_private_evidence_manifest(source_vault_path, repo_root=repo_root)
    validate_metadata_semantics(metadata, source_vault, context, repo_root)
    return {
        "metadata": metadata,
        "source_vault_manifest": source_vault,
    }


def validate_metadata_semantics(
    metadata: dict[str, Any],
    source_vault: dict[str, Any],
    context: str,
    repo_root: Path,
) -> None:
    if metadata["status"] != "public_safe_private_audit_report_fixture":
        raise PrivateAuditReportError(f"{context}.status must be public_safe_private_audit_report_fixture")
    if metadata["report_label"] != "private_audit_report":
        raise PrivateAuditReportError(f"{context}.report_label must be private_audit_report")
    if metadata["report_classification"] != "private_audit_report":
        raise PrivateAuditReportError(f"{context}.report_classification must be private_audit_report")

    validate_expected_map(metadata["report_controls"], EXPECTED_REPORT_CONTROLS, f"{context}.report_controls")
    validate_expected_map(metadata["quality_gate"], EXPECTED_QUALITY_GATE, f"{context}.quality_gate")
    validate_expected_map(metadata["safety_assertions"], EXPECTED_SAFETY, f"{context}.safety_assertions")
    validate_expected_map(
        metadata["aggregate_export_policy"],
        EXPECTED_AGGREGATE_EXPORT,
        f"{context}.aggregate_export_policy",
    )
    validate_output_paths(metadata, source_vault, context, repo_root)
    validate_report_sections(metadata["report_sections"], f"{context}.report_sections")
    validate_included_records(metadata["included_private_record_ids"], source_vault, context)


def validate_output_paths(
    metadata: dict[str, Any],
    source_vault: dict[str, Any],
    context: str,
    repo_root: Path,
) -> None:
    outputs = metadata["output_defaults"]
    private_report_root = require_repo_path(outputs["private_report_root"], f"{context}.output_defaults.private_report_root", repo_root)
    source_private_report_root = require_repo_path(
        source_vault["vault_controls"]["private_reports_root"],
        f"{context}.source_vault_manifest.vault_controls.private_reports_root",
        repo_root,
    )
    if private_report_root != source_private_report_root:
        raise PrivateAuditReportError(f"{context}.output_defaults.private_report_root must match source vault private report root")

    require_path_under(private_report_root, repo_root / "reports", f"{context}.output_defaults.private_report_root", allow_equal=False)
    require_gitignore_pattern(repo_root / ".gitignore", outputs["private_report_root"], f"{context}.output_defaults.private_report_root")

    private_json_path = require_repo_path(outputs["json_path"], f"{context}.output_defaults.json_path", repo_root)
    private_markdown_path = require_repo_path(outputs["markdown_path"], f"{context}.output_defaults.markdown_path", repo_root)
    require_path_under(private_json_path, private_report_root, f"{context}.output_defaults.json_path")
    require_path_under(private_markdown_path, private_report_root, f"{context}.output_defaults.markdown_path")
    if not private_json_path.name.endswith(".local.json"):
        raise PrivateAuditReportError(f"{context}.output_defaults.json_path must end with .local.json")
    if not private_markdown_path.name.endswith(".local.md"):
        raise PrivateAuditReportError(f"{context}.output_defaults.markdown_path must end with .local.md")

    summary_json_path = require_repo_path(outputs["summary_json_path"], f"{context}.output_defaults.summary_json_path", repo_root)
    summary_markdown_path = require_repo_path(
        outputs["summary_markdown_path"],
        f"{context}.output_defaults.summary_markdown_path",
        repo_root,
    )
    aggregate_output_path = require_repo_path(
        metadata["aggregate_export_policy"]["output_path"],
        f"{context}.aggregate_export_policy.output_path",
        repo_root,
    )
    if aggregate_output_path != summary_json_path:
        raise PrivateAuditReportError(f"{context}.aggregate_export_policy.output_path must match summary_json_path")
    validate_summary_output_path(summary_json_path, "summary_json_path", repo_root)
    validate_summary_output_path(summary_markdown_path, "summary_markdown_path", repo_root)


def validate_report_sections(sections: list[dict[str, Any]], context: str) -> None:
    seen_section_ids: set[str] = set()
    for index, section in enumerate(sections):
        section_context = f"{context}[{index}]"
        section_id = section["section_id"]
        if section_id in seen_section_ids:
            raise PrivateAuditReportError(f"{section_context}.section_id duplicate value: {section_id}")
        seen_section_ids.add(section_id)
        if section["source"] != "metadata_only":
            raise PrivateAuditReportError(f"{section_context}.source must be metadata_only")
        if section["aggregate_only"] is not True:
            raise PrivateAuditReportError(f"{section_context}.aggregate_only must be true")
        if section["raw_private_evidence_allowed"] is not False:
            raise PrivateAuditReportError(f"{section_context}.raw_private_evidence_allowed must be false")
        if section["private_values_allowed"] is not False:
            raise PrivateAuditReportError(f"{section_context}.private_values_allowed must be false")


def validate_included_records(record_ids: list[str], source_vault: dict[str, Any], context: str) -> None:
    available_records = {record["record_id"]: record for record in source_vault["private_records"]}
    seen_record_ids: set[str] = set()
    for index, record_id in enumerate(record_ids):
        record_context = f"{context}.included_private_record_ids[{index}]"
        if record_id in seen_record_ids:
            raise PrivateAuditReportError(f"{record_context} duplicate value: {record_id}")
        seen_record_ids.add(record_id)
        record = available_records.get(record_id)
        if record is None:
            raise PrivateAuditReportError(f"{record_context} must reference source vault private_records")
        if record["private_audit_report_label"] != "private_audit_report":
            raise PrivateAuditReportError(f"{record_context} source record must be labeled private_audit_report")
        if record["artifact_content_in_manifest"] is not False:
            raise PrivateAuditReportError(f"{record_context} source record must not include artifact content")
        if record["public_ranking_eligible"] is not False:
            raise PrivateAuditReportError(f"{record_context} source record must not be public ranking eligible")
        validate_expected_map(record["safety_assertions"], EXPECTED_RECORD_SAFETY, f"{record_context}.safety_assertions")


def build_private_report(
    metadata: dict[str, Any],
    source_vault: dict[str, Any],
    metadata_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    """Build the local-only private report object from fake metadata."""

    records_by_id = {record["record_id"]: record for record in source_vault["private_records"]}
    selected_records = [records_by_id[record_id] for record_id in metadata["included_private_record_ids"]]
    redaction_status_counts = Counter(record["redaction_metadata"]["redaction_status"] for record in selected_records)
    retention_counts = Counter(record["retention_class"] for record in selected_records)
    source_runtime_counts = Counter(record["source_runtime"] for record in selected_records)
    source_kind_counts = Counter(record["source_kind"] for record in selected_records)

    return {
        "report_id": "m68_private_audit_report",
        "report_label": metadata["report_label"],
        "report_classification": metadata["report_classification"],
        "generated_at": GENERATED_AT,
        "source_metadata": {
            "metadata_fixture_path": display_path(metadata_path, repo_root),
            "source_vault_manifest_path": metadata["source_vault_manifest_path"],
            "source_metadata_classification": metadata["source_metadata_classification"],
            "fake_metadata_only": True,
            "raw_private_artifacts_read": False,
        },
        "output_boundary": {
            "private_report_root": metadata["output_defaults"]["private_report_root"],
            "json_path": metadata["output_defaults"]["json_path"],
            "markdown_path": metadata["output_defaults"]["markdown_path"],
            "local_only_by_default": True,
            "private_reports_committable": False,
            "artifact_paths_included": False,
            "private_path_values_redacted": True,
        },
        "record_summary": {
            "private_record_metadata_count": len(selected_records),
            "promotion_candidate_count": sum(1 for record in selected_records if record["promotion_candidate"] is True),
            "reviewer_signoff_count": sum(1 for record in selected_records if record["redaction_metadata"]["reviewer_signoff"] is True),
            "public_ranking_eligible": False,
            "source_runtimes": dict(sorted(source_runtime_counts.items())),
            "source_kinds": dict(sorted(source_kind_counts.items())),
            "retention_classes": dict(sorted(retention_counts.items())),
            "redaction_statuses": dict(sorted(redaction_status_counts.items())),
        },
        "records": [
            {
                "record_id": record["record_id"],
                "source_runtime": record["source_runtime"],
                "source_kind": record["source_kind"],
                "declared_evidence_class": record["declared_evidence_class"],
                "retention_class": record["retention_class"],
                "promotion_candidate": record["promotion_candidate"],
                "promotion_status": record["promotion_status"],
                "redaction_status": record["redaction_metadata"]["redaction_status"],
                "reviewer_signoff": record["redaction_metadata"]["reviewer_signoff"],
                "private_audit_report_label": record["private_audit_report_label"],
                "artifact_reference": "local_private_artifact_redacted",
                "artifact_path_included": False,
                "raw_private_evidence_included": False,
                "credentials_or_secrets_included": False,
                "private_workspace_path_included": False,
                "real_customer_data_included": False,
                "public_ranking_eligible": False,
            }
            for record in selected_records
        ],
        "report_sections": metadata["report_sections"],
        "aggregate_export_policy": metadata["aggregate_export_policy"],
        "report_controls": metadata["report_controls"],
        "quality_gate": metadata["quality_gate"],
        "safety_assertions": metadata["safety_assertions"],
        "boundaries": [
            "The private audit report is labeled private_audit_report.",
            "The deterministic gate builds this report from fake metadata only.",
            "Private report outputs are local-only and ignored by Git by default.",
            "Raw private evidence, credentials, secrets, private workspace paths, real customer data, and raw runtime logs are not included.",
            "The report is not public leaderboard evidence, production-safety proof, third-party reproducibility evidence, or a gated LLM review.",
        ],
    }


def validate_generated_private_report(report: dict[str, Any], context: str) -> None:
    if report["report_label"] != "private_audit_report":
        raise PrivateAuditReportError(f"{context}.generated_report.report_label must be private_audit_report")
    if report["report_classification"] != "private_audit_report":
        raise PrivateAuditReportError(f"{context}.generated_report.report_classification must be private_audit_report")
    if report["source_metadata"]["raw_private_artifacts_read"] is not False:
        raise PrivateAuditReportError(f"{context}.generated_report must not read raw private artifacts")
    if report["output_boundary"]["artifact_paths_included"] is not False:
        raise PrivateAuditReportError(f"{context}.generated_report must not include artifact paths")
    validate_expected_map(report["report_controls"], EXPECTED_REPORT_CONTROLS, f"{context}.generated_report.report_controls")
    validate_expected_map(report["quality_gate"], EXPECTED_QUALITY_GATE, f"{context}.generated_report.quality_gate")
    validate_expected_map(report["safety_assertions"], EXPECTED_SAFETY, f"{context}.generated_report.safety_assertions")

    for index, record in enumerate(report["records"]):
        record_context = f"{context}.generated_report.records[{index}]"
        if record["private_audit_report_label"] != "private_audit_report":
            raise PrivateAuditReportError(f"{record_context}.private_audit_report_label must be private_audit_report")
        for field_name in [
            "artifact_path_included",
            "raw_private_evidence_included",
            "credentials_or_secrets_included",
            "private_workspace_path_included",
            "real_customer_data_included",
            "public_ranking_eligible",
        ]:
            if record[field_name] is not False:
                raise PrivateAuditReportError(f"{record_context}.{field_name} must be false")

    report_text = json.dumps(report, sort_keys=True)
    for blocked in GENERATED_REPORT_BLOCKED_STRINGS:
        if blocked in report_text:
            raise PrivateAuditReportError(f"{context}.generated_report contains blocked private marker: {blocked}")


def build_summary(
    metadata: dict[str, Any],
    source_vault: dict[str, Any],
    private_report: dict[str, Any],
    metadata_path: Path,
    repo_root: Path,
    private_outputs_written: bool,
) -> dict[str, Any]:
    """Build committed public-safe aggregate summary metadata."""

    record_summary = private_report["record_summary"]
    return {
        "summary_id": "m68_private_audit_report_boundary_summary",
        "generated_at": GENERATED_AT,
        "source_metadata_path": display_path(metadata_path, repo_root),
        "source_vault_manifest_path": metadata["source_vault_manifest_path"],
        "schema_path": display_path(DEFAULT_SCHEMA_PATH, repo_root),
        "report_label": metadata["report_label"],
        "report_classification": metadata["report_classification"],
        "public_safe_fake_metadata_only": True,
        "private_outputs": {
            "private_report_root": metadata["output_defaults"]["private_report_root"],
            "json_path": metadata["output_defaults"]["json_path"],
            "markdown_path": metadata["output_defaults"]["markdown_path"],
            "outputs_written": private_outputs_written,
            "local_only_by_default": True,
            "private_reports_gitignored": True,
            "private_reports_committable": False,
        },
        "record_counts": {
            "source_vault_private_record_metadata_count": len(source_vault["private_records"]),
            "included_private_record_metadata_count": record_summary["private_record_metadata_count"],
            "promotion_candidate_count": record_summary["promotion_candidate_count"],
            "reviewer_signoff_count": record_summary["reviewer_signoff_count"],
        },
        "aggregate_counts": {
            "source_runtimes": record_summary["source_runtimes"],
            "source_kinds": record_summary["source_kinds"],
            "retention_classes": record_summary["retention_classes"],
            "redaction_statuses": record_summary["redaction_statuses"],
        },
        "aggregate_export_policy": metadata["aggregate_export_policy"],
        "report_controls": metadata["report_controls"],
        "quality_gate": metadata["quality_gate"],
        "safety_assertions": metadata["safety_assertions"],
        "private_artifacts_read": False,
        "raw_private_evidence_included": False,
        "credentials_or_secrets_included": False,
        "private_workspace_paths_included": False,
        "real_customer_data_included": False,
        "public_leaderboard_eligible": False,
        "production_safety_claim": False,
        "third_party_reproducibility_claim": False,
        "private_audit_overclaim": False,
        "boundaries": [
            "Committed M68 summaries are aggregate-only and public-safe.",
            "Local private audit JSON/Markdown outputs are generated under the ignored reports/private/ root by default.",
            "Reports generated from private evidence must be labeled private_audit_report.",
            "The deterministic gate uses fake metadata only and does not ingest or read raw private evidence.",
            "No credentials, secrets, private workspace paths, real customer data, live execution, provider calls, browser/email/network/shell actions, external actions, or gated LLM review are introduced.",
            "Private audit reports do not make public leaderboard, production-safety, third-party reproducibility, or private-audit overclaims.",
        ],
    }


def generate_private_markdown(report: dict[str, Any]) -> str:
    record_summary = report["record_summary"]
    lines = [
        "# Private Audit Report",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Generated at | `{report['generated_at']}` |",
        f"| Report label | `{report['report_label']}` |",
        f"| Report classification | `{report['report_classification']}` |",
        f"| Fake metadata only | `{str(report['source_metadata']['fake_metadata_only']).lower()}` |",
        f"| Raw private artifacts read | `{str(report['source_metadata']['raw_private_artifacts_read']).lower()}` |",
        f"| Private record metadata count | {record_summary['private_record_metadata_count']} |",
        f"| Promotion candidates | {record_summary['promotion_candidate_count']} |",
        f"| Reviewer signoffs | {record_summary['reviewer_signoff_count']} |",
        f"| Public ranking eligible | `{str(record_summary['public_ranking_eligible']).lower()}` |",
        "",
        "## Metadata Inventory",
        "",
        "| Record ID | Runtime | Kind | Retention | Redaction | Promotion |",
        "| --- | --- | --- | --- | --- | --- |",
        *[
            (
                f"| `{record['record_id']}` | `{record['source_runtime']}` | `{record['source_kind']}` | "
                f"`{record['retention_class']}` | `{record['redaction_status']}` | `{record['promotion_status']}` |"
            )
            for record in report["records"]
        ],
        "",
        "## Boundaries",
        "",
        "\n".join(f"- {boundary}" for boundary in report["boundaries"]),
        "",
    ]
    return "\n".join(lines)


def generate_summary_markdown(summary: dict[str, Any]) -> str:
    counts = summary["record_counts"]
    private_outputs = summary["private_outputs"]
    lines = [
        "# Private Audit Report Boundary Summary",
        "",
        "## Summary",
        "",
        "This M68 summary is public-safe fake metadata only. The generated private audit report defaults to ignored local paths; committed artifacts remain aggregate-only.",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Generated at | `{summary['generated_at']}` |",
        f"| Source metadata | `{summary['source_metadata_path']}` |",
        f"| Report label | `{summary['report_label']}` |",
        f"| Private report root | `{private_outputs['private_report_root']}` |",
        f"| Private reports committable | `{str(private_outputs['private_reports_committable']).lower()}` |",
        f"| Private outputs written | `{str(private_outputs['outputs_written']).lower()}` |",
        f"| Included private record metadata | {counts['included_private_record_metadata_count']} |",
        f"| Promotion candidates | {counts['promotion_candidate_count']} |",
        f"| Reviewer signoffs | {counts['reviewer_signoff_count']} |",
        f"| Private artifacts read | `{str(summary['private_artifacts_read']).lower()}` |",
        f"| Public leaderboard eligible | `{str(summary['public_leaderboard_eligible']).lower()}` |",
        "",
        "## Aggregate Export Boundary",
        "",
        f"- Enabled by default: `{str(summary['aggregate_export_policy']['enabled_by_default']).lower()}`",
        f"- Public-safe by default: `{str(summary['aggregate_export_policy']['public_safe_by_default']).lower()}`",
        f"- Aggregate only: `{str(summary['aggregate_export_policy']['aggregate_only']).lower()}`",
        f"- Per-record private details in export: `{str(summary['aggregate_export_policy']['per_record_private_details_in_export']).lower()}`",
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
            raise PrivateAuditReportError(f"{context}.{field_name} must equal {expected_value!r}")


def validate_utc_timestamp(value: str, context: str) -> None:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise PrivateAuditReportError(f"{context} must be a UTC timestamp like 2026-06-21T00:00:00Z") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise PrivateAuditReportError(f"{context} must be canonical UTC timestamp text")


def validate_summary_output_path(path: Path, context: str, repo_root: Path) -> None:
    require_path_under(path, repo_root / "reports/comparisons", context)
    if context == "summary_json_path" and path.suffix != ".json":
        raise PrivateAuditReportError(f"{context} must point to a JSON file")
    if context == "summary_markdown_path" and path.suffix != ".md":
        raise PrivateAuditReportError(f"{context} must point to a Markdown file")


def require_existing_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    path = require_repo_path(value, context, repo_root)
    if not path.exists():
        raise PrivateAuditReportError(f"{context} does not exist: {display_path(path, repo_root)}")
    return path


def require_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise PrivateAuditReportError(f"{context} must be a non-empty string")
    path = Path(value)
    if path.is_absolute():
        raise PrivateAuditReportError(f"{context} must be a repository-relative path")
    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise PrivateAuditReportError(f"{context} must stay within the repository") from exc
    return resolved


def require_path_under(path: Path, parent: Path, context: str, allow_equal: bool = True) -> None:
    try:
        relative = path.resolve().relative_to(parent.resolve())
    except ValueError as exc:
        raise PrivateAuditReportError(f"{context} must stay under {display_path(parent)}") from exc
    if not allow_equal and str(relative) == ".":
        raise PrivateAuditReportError(f"{context} must be a child path under {display_path(parent)}")


def require_gitignore_pattern(gitignore_path: Path, expected_pattern: str, context: str) -> None:
    patterns = {
        line.strip()
        for line in gitignore_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if expected_pattern not in patterns:
        raise PrivateAuditReportError(f"{context} requires .gitignore pattern {expected_pattern!r}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and generate M68 private audit report metadata.")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DEFAULT_METADATA_PATH,
        help="Private audit report metadata request path.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help="Private audit report metadata schema path.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=DEFAULT_SUMMARY_JSON_PATH,
        help="Public-safe boundary summary JSON output.",
    )
    parser.add_argument(
        "--summary-report",
        type=Path,
        default=DEFAULT_SUMMARY_REPORT_PATH,
        help="Public-safe boundary summary Markdown output.",
    )
    parser.add_argument(
        "--skip-private-output",
        action="store_true",
        help="Validate and write summaries without writing ignored private report outputs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = generate_private_audit_report(
            args.path,
            args.schema,
            args.summary_json,
            args.summary_report,
            write_private_outputs=not args.skip_private_output,
        )
    except (OSError, ValueError, PrivateAuditReportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"private audit metadata: {summary['source_metadata_path']}")
    print(f"private audit report label: {summary['report_label']}")
    print(f"included private record metadata: {summary['record_counts']['included_private_record_metadata_count']}")
    print(f"private outputs written: {str(summary['private_outputs']['outputs_written']).lower()}")
    print("private audit report validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
