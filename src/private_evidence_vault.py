"""Validate the M66 private evidence vault boundary.

The vault contract is metadata-only in the deterministic quality gate. It
checks ignored local storage roots, fake private-record metadata, redaction
preconditions, and private-audit report labels without reading raw private
evidence, handling secrets, executing agents, calling providers, or promoting
fixtures.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from reporting_utils import write_json_object, write_text
from schema_validation_utils import display_path, load_json_object, validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "traces/external/private_evidence_vault_manifest.example.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/private_evidence_manifest.schema.json"
DEFAULT_SUMMARY_JSON_PATH = REPO_ROOT / "reports/comparisons/private_evidence_vault_summary.json"
DEFAULT_SUMMARY_REPORT_PATH = REPO_ROOT / "reports/comparisons/private_evidence_vault_summary.md"
GENERATED_AT = "2026-06-21T00:00:00Z"

EXPECTED_QUALITY_GATE = {
    "deterministic_gate_validates_fake_metadata_only": True,
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
    "fake_metadata_only": True,
    "contains_private_data": False,
    "credentials_required": False,
    "raw_private_logs": False,
    "private_workspace_paths": False,
    "real_customer_data": False,
    "live_execution": False,
    "external_actions": False,
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


class PrivateEvidenceVaultError(Exception):
    """Private evidence vault validation error."""


def generate_private_evidence_vault_summary(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    summary_json_path: Path = DEFAULT_SUMMARY_JSON_PATH,
    summary_report_path: Path = DEFAULT_SUMMARY_REPORT_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the M66 manifest and write public-safe boundary reports."""

    manifest = validate_private_evidence_manifest(manifest_path, schema_path, repo_root)
    summary = build_summary(manifest, manifest_path, repo_root)
    write_json_object(summary, summary_json_path)
    write_text(generate_markdown(summary), summary_report_path)
    return summary


def validate_private_evidence_manifest(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the public-safe fake private evidence manifest."""

    schema = load_json_object(schema_path, "private evidence manifest schema", repo_root, PrivateEvidenceVaultError)
    manifest = load_json_object(manifest_path, "private evidence manifest", repo_root, PrivateEvidenceVaultError)
    context = display_path(manifest_path, repo_root)
    validate_schema_value(manifest, schema, context, manifest_path, repo_root, PrivateEvidenceVaultError)
    validate_utc_timestamp(manifest["created_at"], f"{context}.created_at")
    validate_manifest_semantics(manifest, context, repo_root)
    return manifest


def validate_manifest_semantics(manifest: dict[str, Any], context: str, repo_root: Path) -> None:
    if manifest["status"] != "public_safe_private_vault_metadata":
        raise PrivateEvidenceVaultError(f"{context}.status must be public_safe_private_vault_metadata")
    if manifest["evidence_class"] != "private_audit_metadata_public_safe":
        raise PrivateEvidenceVaultError(f"{context}.evidence_class must be private_audit_metadata_public_safe")

    validate_vault_controls(manifest["vault_controls"], f"{context}.vault_controls", repo_root)
    validate_storage_plan(manifest["storage_plan"], f"{context}.storage_plan")
    validate_promotion_controls(manifest["promotion_controls"], f"{context}.promotion_controls")
    validate_audit_report_controls(
        manifest["audit_report_controls"],
        manifest["vault_controls"],
        f"{context}.audit_report_controls",
        repo_root,
    )
    validate_expected_map(manifest["quality_gate"], EXPECTED_QUALITY_GATE, f"{context}.quality_gate")
    validate_expected_map(manifest["safety_assertions"], EXPECTED_SAFETY, f"{context}.safety_assertions")
    validate_private_records(manifest["private_records"], manifest, context, repo_root)


def validate_vault_controls(value: dict[str, Any], context: str, repo_root: Path) -> None:
    vault_root = require_repo_path(value["vault_root"], f"{context}.vault_root", repo_root)
    private_reports_root = require_repo_path(value["private_reports_root"], f"{context}.private_reports_root", repo_root)
    gitignore_path = require_existing_repo_path(value["gitignore_path"], f"{context}.gitignore_path", repo_root)

    require_path_under(vault_root, repo_root, f"{context}.vault_root", allow_equal=False)
    require_path_under(private_reports_root, repo_root / "reports", f"{context}.private_reports_root", allow_equal=False)
    require_gitignore_pattern(gitignore_path, value["vault_root"], f"{context}.vault_root_gitignored")
    require_gitignore_pattern(gitignore_path, value["private_reports_root"], f"{context}.private_reports_root_gitignored")

    expected = {
        "vault_root_gitignored": True,
        "private_reports_root_gitignored": True,
        "raw_private_records_committable": False,
        "private_reports_committable": False,
        "public_derivatives_committable_after_redaction": True,
    }
    validate_expected_map(value, expected, context)


def validate_storage_plan(value: dict[str, Any], context: str) -> None:
    expected = {
        "storage_mode": "ignored_local_directory",
        "encryption_plan": "optional_local_file_encryption_or_os_keychain_wrapped_key",
        "encryption_required_for_real_private_evidence": True,
        "key_material_committable": False,
        "secret_material_in_manifest": False,
        "credentials_required_for_fake_metadata": False,
        "live_secret_handling_in_quality_gate": False,
    }
    validate_expected_map(value, expected, context)


def validate_promotion_controls(value: dict[str, Any], context: str) -> None:
    expected = {
        "promotion_command_status": "validation_only_promotions_blocked_until_m67",
        "redaction_metadata_required": True,
        "reviewer_signoff_required": True,
        "original_private_artifact_remains_local_only": True,
        "promoted_fixture_requires_public_safety_assertions": True,
        "private_evidence_public_ranking_eligible": False,
        "refused_without_redaction_metadata": True,
    }
    validate_expected_map(value, expected, context)


def validate_audit_report_controls(
    value: dict[str, Any],
    vault_controls: dict[str, Any],
    context: str,
    repo_root: Path,
) -> None:
    audit_root = require_repo_path(value["private_audit_report_root"], f"{context}.private_audit_report_root", repo_root)
    private_reports_root = require_repo_path(
        vault_controls["private_reports_root"],
        f"{context}.private_reports_root",
        repo_root,
    )
    if audit_root != private_reports_root:
        raise PrivateEvidenceVaultError(f"{context}.private_audit_report_root must match vault_controls.private_reports_root")

    expected = {
        "required_report_label": "private_audit_report",
        "reports_generated_from_private_evidence_marked_private_audit": True,
        "private_audit_reports_gitignored": True,
        "public_leaderboard_eligible": False,
        "aggregate_export_default": False,
        "local_only_by_default": True,
    }
    validate_expected_map(value, expected, context)


def validate_private_records(
    records: list[dict[str, Any]],
    manifest: dict[str, Any],
    context: str,
    repo_root: Path,
) -> None:
    seen_record_ids: set[str] = set()
    vault_root = require_repo_path(manifest["vault_controls"]["vault_root"], f"{context}.vault_controls.vault_root", repo_root)

    for index, record in enumerate(records):
        record_context = f"{context}.private_records[{index}]"
        record_id = str(record["record_id"])
        if record_id in seen_record_ids:
            raise PrivateEvidenceVaultError(f"{record_context}.record_id duplicate value: {record_id}")
        seen_record_ids.add(record_id)

        artifact_path = require_repo_path(record["artifact_path"], f"{record_context}.artifact_path", repo_root)
        require_path_under(artifact_path, vault_root, f"{record_context}.artifact_path")
        if ".local." not in artifact_path.name:
            raise PrivateEvidenceVaultError(f"{record_context}.artifact_path must be a local-only path")

        if record["artifact_content_in_manifest"] is not False:
            raise PrivateEvidenceVaultError(f"{record_context}.artifact_content_in_manifest must be false")
        if record["public_ranking_eligible"] is not False:
            raise PrivateEvidenceVaultError(f"{record_context}.public_ranking_eligible must be false")
        if record["private_audit_report_label"] != "private_audit_report":
            raise PrivateEvidenceVaultError(f"{record_context}.private_audit_report_label must be private_audit_report")

        validate_expected_map(record["safety_assertions"], EXPECTED_RECORD_SAFETY, f"{record_context}.safety_assertions")
        validate_redaction_metadata(record, record_context, repo_root, vault_root)


def validate_redaction_metadata(record: dict[str, Any], context: str, repo_root: Path, vault_root: Path) -> None:
    redaction = record["redaction_metadata"]
    notes_path = require_repo_path(redaction["redaction_notes_path"], f"{context}.redaction_metadata.redaction_notes_path", repo_root)
    require_path_under(notes_path, vault_root, f"{context}.redaction_metadata.redaction_notes_path")
    if not notes_path.name.endswith(".local.json"):
        raise PrivateEvidenceVaultError(f"{context}.redaction_metadata.redaction_notes_path must end with .local.json")

    derivative_path = require_repo_path(
        redaction["public_safe_derivative_path"],
        f"{context}.redaction_metadata.public_safe_derivative_path",
        repo_root,
    )
    require_path_under(derivative_path, repo_root / "traces/external", f"{context}.redaction_metadata.public_safe_derivative_path")
    if not derivative_path.name.endswith(".reviewed.jsonl"):
        raise PrivateEvidenceVaultError(
            f"{context}.redaction_metadata.public_safe_derivative_path must end with .reviewed.jsonl"
        )
    require_gitignore_pattern(repo_root / ".gitignore", "traces/external/*.reviewed.jsonl", f"{context}.redaction_metadata.public_safe_derivative_path")

    if record["promotion_candidate"] is True and redaction["metadata_present"] is not True:
        raise PrivateEvidenceVaultError(f"{context} refuses promotion without explicit redaction metadata")
    if record["promotion_candidate"] is True and record["promotion_status"] == "not_requested":
        raise PrivateEvidenceVaultError(f"{context}.promotion_status must record a redaction boundary for promotion candidates")
    if record["promotion_candidate"] is False and record["promotion_status"] != "not_requested":
        raise PrivateEvidenceVaultError(f"{context}.promotion_status must be not_requested when promotion_candidate is false")
    if redaction["promotion_allowed"] is not False:
        raise PrivateEvidenceVaultError(f"{context}.redaction_metadata.promotion_allowed must be false until M67")


def validate_promotion_preflight(record: dict[str, Any], context: str) -> None:
    """Validate the redaction prerequisites an explicit promotion command would need."""

    redaction = record["redaction_metadata"]
    if redaction["metadata_present"] is not True:
        raise PrivateEvidenceVaultError(f"{context} refuses promotion without explicit redaction metadata")
    if redaction["reviewer_signoff"] is not True:
        raise PrivateEvidenceVaultError(f"{context} refuses promotion without reviewer signoff")
    if redaction["public_safety_assertions_present"] is not True:
        raise PrivateEvidenceVaultError(f"{context} refuses promotion without public-safety assertions")
    if redaction["promotion_allowed"] is not True:
        raise PrivateEvidenceVaultError(f"{context} refuses promotion because M66 is validation-only")


def build_summary(manifest: dict[str, Any], manifest_path: Path, repo_root: Path) -> dict[str, Any]:
    records = manifest["private_records"]
    promotion_candidates = sum(1 for record in records if record["promotion_candidate"] is True)
    return {
        "summary_id": "m66_private_evidence_vault_summary",
        "generated_at": GENERATED_AT,
        "source_manifest_path": display_path(manifest_path, repo_root),
        "schema_path": display_path(DEFAULT_SCHEMA_PATH, repo_root),
        "manifest_id": manifest["manifest_id"],
        "evidence_class": manifest["evidence_class"],
        "public_safe_fake_metadata_only": True,
        "vault": {
            "vault_root": manifest["vault_controls"]["vault_root"],
            "private_reports_root": manifest["vault_controls"]["private_reports_root"],
            "vault_root_gitignored": manifest["vault_controls"]["vault_root_gitignored"],
            "private_reports_root_gitignored": manifest["vault_controls"]["private_reports_root_gitignored"],
            "raw_private_records_committable": manifest["vault_controls"]["raw_private_records_committable"],
            "private_reports_committable": manifest["vault_controls"]["private_reports_committable"],
        },
        "storage_plan": {
            "storage_mode": manifest["storage_plan"]["storage_mode"],
            "encryption_plan": manifest["storage_plan"]["encryption_plan"],
            "encryption_required_for_real_private_evidence": manifest["storage_plan"][
                "encryption_required_for_real_private_evidence"
            ],
            "key_material_committable": manifest["storage_plan"]["key_material_committable"],
            "secret_material_in_manifest": manifest["storage_plan"]["secret_material_in_manifest"],
        },
        "record_counts": {
            "private_record_metadata_count": len(records),
            "promotion_candidate_count": promotion_candidates,
            "redaction_metadata_present_count": sum(
                1 for record in records if record["redaction_metadata"]["metadata_present"] is True
            ),
            "promotion_allowed_count": sum(
                1 for record in records if record["redaction_metadata"]["promotion_allowed"] is True
            ),
        },
        "promotion_controls": manifest["promotion_controls"],
        "audit_report_controls": manifest["audit_report_controls"],
        "quality_gate": manifest["quality_gate"],
        "safety_assertions": manifest["safety_assertions"],
        "boundaries": [
            "The deterministic gate validates fake metadata only.",
            "Raw private evidence and private audit reports stay under ignored local paths by default.",
            "M66 does not promote private records; promotion is blocked until explicit redaction metadata and a future M67 promotion pipeline exist.",
            "Private audit evidence is not public benchmark or leaderboard evidence.",
            "No credentials, private logs, private workspace paths, real customer data, live execution, provider calls, or external actions are introduced.",
        ],
    }


def generate_markdown(summary: dict[str, Any]) -> str:
    counts = summary["record_counts"]
    vault = summary["vault"]
    storage = summary["storage_plan"]
    audit = summary["audit_report_controls"]
    lines = [
        "# Private Evidence Vault Boundary Summary",
        "",
        "## Summary",
        "",
        "This M66 report is public-safe fake metadata only. It validates local private evidence vault boundaries; it is not a private audit report and does not include private evidence.",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Generated at | `{summary['generated_at']}` |",
        f"| Source manifest | `{summary['source_manifest_path']}` |",
        f"| Evidence class | `{summary['evidence_class']}` |",
        f"| Fake metadata only | `{str(summary['public_safe_fake_metadata_only']).lower()}` |",
        f"| Private record metadata count | {counts['private_record_metadata_count']} |",
        f"| Promotion candidates | {counts['promotion_candidate_count']} |",
        f"| Promotion allowed | {counts['promotion_allowed_count']} |",
        "",
        "## Vault Controls",
        "",
        "| Control | Value |",
        "| --- | --- |",
        f"| Vault root | `{vault['vault_root']}` |",
        f"| Vault root ignored | `{str(vault['vault_root_gitignored']).lower()}` |",
        f"| Private report root | `{vault['private_reports_root']}` |",
        f"| Private report root ignored | `{str(vault['private_reports_root_gitignored']).lower()}` |",
        f"| Raw private records committable | `{str(vault['raw_private_records_committable']).lower()}` |",
        f"| Private reports committable | `{str(vault['private_reports_committable']).lower()}` |",
        "",
        "## Storage Plan",
        "",
        f"- Storage mode: `{storage['storage_mode']}`",
        f"- Encryption plan: `{storage['encryption_plan']}`",
        f"- Encryption required for real private evidence: `{str(storage['encryption_required_for_real_private_evidence']).lower()}`",
        f"- Key material committable: `{str(storage['key_material_committable']).lower()}`",
        f"- Secret material in manifest: `{str(storage['secret_material_in_manifest']).lower()}`",
        "",
        "## Private Audit Report Label",
        "",
        f"- Required label: `{audit['required_report_label']}`",
        f"- Reports generated from private evidence marked private audit: `{str(audit['reports_generated_from_private_evidence_marked_private_audit']).lower()}`",
        f"- Public leaderboard eligible: `{str(audit['public_leaderboard_eligible']).lower()}`",
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
            raise PrivateEvidenceVaultError(f"{context}.{field_name} must equal {expected_value!r}")


def validate_utc_timestamp(value: str, context: str) -> None:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise PrivateEvidenceVaultError(f"{context} must be a UTC timestamp like 2026-06-21T00:00:00Z") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise PrivateEvidenceVaultError(f"{context} must be canonical UTC timestamp text")


def require_existing_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    path = require_repo_path(value, context, repo_root)
    if not path.exists():
        raise PrivateEvidenceVaultError(f"{context} does not exist: {display_path(path, repo_root)}")
    return path


def require_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise PrivateEvidenceVaultError(f"{context} must be a non-empty string")
    path = Path(value)
    if path.is_absolute():
        raise PrivateEvidenceVaultError(f"{context} must be a repository-relative path")
    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise PrivateEvidenceVaultError(f"{context} must stay within the repository") from exc
    return resolved


def require_path_under(path: Path, parent: Path, context: str, allow_equal: bool = True) -> None:
    try:
        relative = path.resolve().relative_to(parent.resolve())
    except ValueError as exc:
        raise PrivateEvidenceVaultError(f"{context} must stay under {display_path(parent)}") from exc
    if not allow_equal and str(relative) == ".":
        raise PrivateEvidenceVaultError(f"{context} must be a child path under {display_path(parent)}")


def require_gitignore_pattern(gitignore_path: Path, expected_pattern: str, context: str) -> None:
    patterns = {
        line.strip()
        for line in gitignore_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    if expected_pattern not in patterns:
        raise PrivateEvidenceVaultError(f"{context} requires .gitignore pattern {expected_pattern!r}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the M66 private evidence vault metadata boundary.")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help="Private evidence vault manifest path.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help="Private evidence manifest schema path.",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=DEFAULT_SUMMARY_JSON_PATH,
        help="Public-safe vault boundary JSON summary output.",
    )
    parser.add_argument(
        "--summary-report",
        type=Path,
        default=DEFAULT_SUMMARY_REPORT_PATH,
        help="Public-safe vault boundary Markdown report output.",
    )
    parser.add_argument(
        "--check-promotion-record",
        help="Validate promotion preflight for one record ID. M66 intentionally refuses committed examples.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        manifest = validate_private_evidence_manifest(args.path, args.schema)
        if args.check_promotion_record:
            for record in manifest["private_records"]:
                if record["record_id"] == args.check_promotion_record:
                    validate_promotion_preflight(record, f"{display_path(args.path)}.{record['record_id']}")
                    break
            else:
                raise PrivateEvidenceVaultError(f"record_id not found: {args.check_promotion_record}")
        summary = generate_private_evidence_vault_summary(args.path, args.schema, args.summary_json, args.summary_report)
    except (OSError, ValueError, PrivateEvidenceVaultError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"private evidence manifest: {summary['source_manifest_path']}")
    print(f"private record metadata: {summary['record_counts']['private_record_metadata_count']}")
    print(f"promotion candidates: {summary['record_counts']['promotion_candidate_count']}")
    print(f"promotion allowed: {summary['record_counts']['promotion_allowed_count']}")
    print("private evidence vault validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
