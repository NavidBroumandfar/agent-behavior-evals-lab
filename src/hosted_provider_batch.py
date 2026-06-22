"""Validate M75 hosted-provider Batch metadata.

The committed fixture is public-safe metadata only. It documents the planned
OpenAI Batch path as a separate evidence class without submitting a batch,
reading request/result payloads, handling credentials, calling providers, or
mixing hosted-provider claims with local/open-weight benchmark claims.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from reporting_utils import write_json_object, write_text
from schema_validation_utils import display_path, load_json_object, validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_METADATA_PATH = REPO_ROOT / "traces/external/hosted_provider_batch_metadata.example.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/hosted_provider_batch.schema.json"
DEFAULT_REPORT_JSON_PATH = REPO_ROOT / "reports/comparisons/hosted_provider_batch_summary.json"
DEFAULT_REPORT_MARKDOWN_PATH = REPO_ROOT / "reports/comparisons/hosted_provider_batch_summary.md"
GENERATED_AT = "2026-06-22T00:00:00Z"

EXPECTED_QUALITY_GATE = {
    "deterministic_gate_uses_fake_metadata_only": True,
    "provider_calls_in_quality_gate": False,
    "batch_submission_in_quality_gate": False,
    "request_payload_read_in_quality_gate": False,
    "result_payload_read_in_quality_gate": False,
    "credential_handling_in_quality_gate": False,
    "network_calls_in_quality_gate": False,
}
EXPECTED_SAFETY = {
    "public_safe": True,
    "metadata_only": True,
    "contains_credentials_or_secrets": False,
    "contains_private_data": False,
    "contains_raw_provider_payloads": False,
    "live_provider_execution": False,
    "cloud_ranking_claim": False,
    "local_open_weight_ranking_claim": False,
    "production_safety_claim": False,
}
BLOCKED_MARKERS = [
    "sk-",
    "/Users/",
    "\\Users\\",
    "api_key",
    "raw_provider_payload_text",
    "BEGIN PRIVATE",
    "END PRIVATE",
]


class HostedProviderBatchError(Exception):
    """Hosted provider batch metadata validation error."""


def generate_hosted_provider_batch_summary(
    metadata_path: Path = DEFAULT_METADATA_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    report_json_path: Path = DEFAULT_REPORT_JSON_PATH,
    report_markdown_path: Path = DEFAULT_REPORT_MARKDOWN_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate hosted-provider metadata and write a public-safe summary."""

    metadata = validate_hosted_provider_batch_metadata(metadata_path, schema_path, repo_root)
    summary = build_summary(metadata, metadata_path, repo_root)
    validate_public_summary(summary, display_path(metadata_path, repo_root))
    write_json_object(summary, report_json_path)
    write_text(generate_markdown(summary), report_markdown_path)
    return summary


def validate_hosted_provider_batch_metadata(
    metadata_path: Path = DEFAULT_METADATA_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate public-safe hosted-provider metadata."""

    schema = load_json_object(schema_path, "hosted provider batch schema", repo_root, HostedProviderBatchError)
    metadata = load_json_object(metadata_path, "hosted provider batch metadata", repo_root, HostedProviderBatchError)
    context = display_path(metadata_path, repo_root)
    validate_schema_value(metadata, schema, context, metadata_path, repo_root, HostedProviderBatchError)
    validate_metadata_semantics(metadata, context)
    return metadata


def validate_metadata_semantics(metadata: dict[str, Any], context: str) -> None:
    validate_expected_map(metadata["quality_gate"], EXPECTED_QUALITY_GATE, f"{context}.quality_gate")
    validate_expected_map(metadata["safety_assertions"], EXPECTED_SAFETY, f"{context}.safety_assertions")
    if metadata["batch"]["submitted"] is not False:
        raise HostedProviderBatchError(f"{context}.batch.submitted must be false for committed metadata-only fixture")
    if metadata["batch"]["batch_status"] != "not_submitted":
        raise HostedProviderBatchError(f"{context}.batch.batch_status must be not_submitted")
    if metadata["payload_hashes"]["request_payload_committed"] is not False:
        raise HostedProviderBatchError(f"{context}.payload_hashes.request_payload_committed must be false")
    if metadata["payload_hashes"]["result_payload_committed"] is not False:
        raise HostedProviderBatchError(f"{context}.payload_hashes.result_payload_committed must be false")
    if metadata["separation_boundary"]["separate_from_local_open_weight_rankings"] is not True:
        raise HostedProviderBatchError(
            f"{context}.separation_boundary.separate_from_local_open_weight_rankings must be true"
        )
    if metadata["separation_boundary"]["mixed_provider_comparison_allowed"] is not False:
        raise HostedProviderBatchError(f"{context}.separation_boundary.mixed_provider_comparison_allowed must be false")
    if "cloud" in str(metadata["model"]).lower():
        raise HostedProviderBatchError(f"{context}.model must be a neutral placeholder until a real hosted report exists")


def build_summary(metadata: dict[str, Any], metadata_path: Path, repo_root: Path) -> dict[str, Any]:
    return {
        "summary_id": "m75_hosted_provider_batch_summary",
        "generated_at": GENERATED_AT,
        "source_metadata_path": display_path(metadata_path, repo_root),
        "source_schema_path": display_path(DEFAULT_SCHEMA_PATH, repo_root),
        "evidence_class": metadata["evidence_class"],
        "provider": metadata["provider"],
        "model": metadata["model"],
        "endpoint_mode": metadata["endpoint_mode"],
        "batch": metadata["batch"],
        "payload_hashes": metadata["payload_hashes"],
        "cost_metadata": metadata["cost_metadata"],
        "separation_boundary": metadata["separation_boundary"],
        "quality_gate": metadata["quality_gate"],
        "safety_assertions": metadata["safety_assertions"],
        "publication_state": {
            "hosted_report_ready": False,
            "hosted_ranking_claim_allowed": False,
            "local_open_weight_ranking_claim_allowed": False,
            "blocked_reason": "Hosted provider path is metadata-only until an explicit opt-in provider run is reviewed.",
        },
        "boundaries": [
            "M75 metadata is a planned hosted-provider path, not a submitted batch.",
            "Hosted-provider evidence is separate from local/open-weight benchmark evidence.",
            "No API keys, request JSONL, result JSONL, provider payloads, private data, or costs are committed.",
            "No cloud ranking, local/open-weight ranking, production-safety proof, or cross-provider comparison is claimed.",
        ],
    }


def validate_public_summary(summary: dict[str, Any], context: str) -> None:
    validate_expected_map(summary["quality_gate"], EXPECTED_QUALITY_GATE, f"{context}.report.quality_gate")
    validate_expected_map(summary["safety_assertions"], EXPECTED_SAFETY, f"{context}.report.safety_assertions")
    text = str(summary)
    for marker in BLOCKED_MARKERS:
        if marker in text:
            raise HostedProviderBatchError(f"{context}.report contains blocked marker: {marker}")


def generate_markdown(summary: dict[str, Any]) -> str:
    publication = summary["publication_state"]
    lines = [
        "# Hosted Provider Batch Summary",
        "",
        "This M75 report is metadata-only. It documents a later hosted-provider Batch path without provider execution or committed request/result payloads.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Generated at | `{summary['generated_at']}` |",
        f"| Provider | `{summary['provider']}` |",
        f"| Evidence class | `{summary['evidence_class']}` |",
        f"| Endpoint | `{summary['endpoint_mode']['endpoint']}` |",
        f"| Transport | `{summary['endpoint_mode']['transport']}` |",
        f"| Batch status | `{summary['batch']['batch_status']}` |",
        f"| Hosted report ready | `{str(publication['hosted_report_ready']).lower()}` |",
        f"| Local ranking claim allowed | `{str(publication['local_open_weight_ranking_claim_allowed']).lower()}` |",
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
            raise HostedProviderBatchError(f"{context}.{field_name} must equal {expected_value!r}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate hosted-provider Batch metadata and generate a summary.")
    parser.add_argument("metadata", nargs="?", type=Path, default=DEFAULT_METADATA_PATH)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON_PATH)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MARKDOWN_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = generate_hosted_provider_batch_summary(
            args.metadata,
            args.schema,
            args.report_json,
            args.report_md,
        )
    except (HostedProviderBatchError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"hosted provider metadata: {summary['source_metadata_path']}")
    print(f"provider: {summary['provider']}")
    print(f"batch status: {summary['batch']['batch_status']}")
    print("hosted provider batch summary validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
