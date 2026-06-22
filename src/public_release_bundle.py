"""Validate M87 claim-locked public release bundle metadata.

The bundle is a public release handoff for the current local/open-weight
ranking. It validates committed metadata and release wording only. It does not
run local models, probe runtimes, read raw outputs, call providers, inspect
private evidence, or perform external actions.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

from schema_validation_utils import display_path, load_json_object, validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE_PATH = REPO_ROOT / "traces/external/public_release_bundle.example.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/public_release_bundle.schema.json"

CLAIM_CHECKLIST_PATH = REPO_ROOT / "traces/external/claim_review_checklist.example.json"
LOCAL_REPORT_PATH = REPO_ROOT / "reports/comparisons/local_open_weight_benchmark_v1.json"

EXPECTED_QUALITY_GATE = {
    "bundle_validation_in_quality_gate": True,
    "live_local_execution_in_quality_gate": False,
    "runtime_probe_in_quality_gate": False,
    "raw_output_read_in_quality_gate": False,
    "provider_calls_in_quality_gate": False,
    "hosted_provider_submission_in_quality_gate": False,
    "private_evidence_read_in_quality_gate": False,
    "external_actions_in_quality_gate": False,
}
EXPECTED_SAFETY_ASSERTIONS = {
    "public_safe": True,
    "metadata_only": True,
    "contains_private_data": False,
    "contains_raw_outputs": False,
    "contains_credentials_or_secrets": False,
    "live_execution": False,
    "provider_calls": False,
    "cloud_ranking_claim": False,
    "production_safety_claim": False,
    "hosted_provider_comparison_claim": False,
    "third_party_reproducibility_claim": False,
    "private_audit_claim": False,
    "unsupported_claims_released": False,
}
EXPECTED_RELEASE_SCOPE = {
    "release_label": "public_safe_local_open_weight_ranking",
    "allowed_claim_id": "local_open_weight_ranking",
    "source_checklist_path": "traces/external/claim_review_checklist.example.json",
    "source_report_path": "reports/comparisons/local_open_weight_benchmark_v1.json",
    "evidence_class": "local_public_benchmark",
    "case_set_id": "local_public_v1",
    "case_set_version": "1.0.0",
    "split": "extended",
    "release_allowed": True,
    "ranking_claim_allowed": True,
}
REQUIRED_PUBLICATION_CHECKS = {
    "m86_claim_gate_passed",
    "local_report_publishable",
    "allowed_wording_scoped",
    "blocked_wording_named",
    "release_docs_scanned",
    "raw_outputs_excluded",
}
REQUIRED_RELEASE_ARTIFACTS = {
    "local_open_weight_report_json",
    "local_open_weight_report_md",
    "claim_review_checklist",
    "public_safe_reproducibility_packet",
    "runtime_stability_profile",
    "real_model_proof_runbook",
    "public_release_bundle",
}
EXPECTED_RANKED_MODELS = {"llama3.2:latest", "mistral:latest"}
EXPECTED_STATEMENT_SNIPPETS = [
    "public-safe local/open-weight ranking",
    "llama3.2:latest",
    "mistral:latest",
    "local_public_v1 extended split",
    "two reviewed local Ollama ledgers",
]
EXPECTED_QUALIFIER_SNIPPETS = [
    "not a cloud-model ranking",
    "hosted-provider comparison",
    "production-safety proof",
    "private-audit proof",
    "third-party output-regeneration claim",
]
BOUNDARY_LINE_MARKERS = [
    "no ",
    "not ",
    "does not",
    "do not",
    "must not",
    "cannot",
    "excluded",
    "separate",
    "blocked",
    "blocks",
    "unsupported",
    "without",
    "disallowed",
    "refuse",
]
POSITIVE_OVERCLAIM_PATTERNS = [
    ("cloud ranking", re.compile(r"\bcloud[- ](?:model[- ])?ranking\b", re.IGNORECASE)),
    ("hosted provider comparison", re.compile(r"\bhosted[- ]provider comparison\b", re.IGNORECASE)),
    ("production safety proof", re.compile(r"\bproduction[- ]safety proof\b", re.IGNORECASE)),
    ("third party reproducibility", re.compile(r"\bthird[- ]party (?:output[- ])?reproducibility\b", re.IGNORECASE)),
    ("private audit proof", re.compile(r"\bprivate[- ]audit proof\b", re.IGNORECASE)),
]
BLOCKED_MARKERS = [
    "/Users/",
    "\\Users\\",
    "sk-",
    "api_key",
    "BEGIN PRIVATE",
    "END PRIVATE",
    "raw_output_text",
    "raw_response",
]
VAGUE_MARKERS = [
    "missing context",
    "unknown",
    "tbd",
    "to be determined",
]


class PublicReleaseBundleError(Exception):
    """Public release bundle validation error."""


def validate_public_release_bundle(
    bundle_path: Path = DEFAULT_BUNDLE_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the committed M87 public release bundle."""

    schema = load_json_object(schema_path, "public release bundle schema", repo_root, PublicReleaseBundleError)
    bundle = load_json_object(bundle_path, "public release bundle", repo_root, PublicReleaseBundleError)
    checklist = load_json_object(CLAIM_CHECKLIST_PATH, "claim review checklist", repo_root, PublicReleaseBundleError)
    report = load_json_object(LOCAL_REPORT_PATH, "local benchmark report", repo_root, PublicReleaseBundleError)
    context = display_path(bundle_path, repo_root)

    validate_schema_value(bundle, schema, context, bundle_path, repo_root, PublicReleaseBundleError)
    validate_expected_map(bundle["quality_gate"], EXPECTED_QUALITY_GATE, f"{context}.quality_gate")
    validate_expected_map(bundle["safety_assertions"], EXPECTED_SAFETY_ASSERTIONS, f"{context}.safety_assertions")
    validate_expected_map(bundle["release_scope"], EXPECTED_RELEASE_SCOPE, f"{context}.release_scope")
    validate_claim_gate_state(bundle, checklist, f"{context}.release_scope")
    validate_report_state(bundle, report, f"{context}.ranking_rows")
    validate_approved_statement(bundle["approved_release_statement"], f"{context}.approved_release_statement")
    validate_release_artifacts(bundle["release_artifacts"], f"{context}.release_artifacts", repo_root)
    validate_blocked_claims(bundle["blocked_claims"], checklist, f"{context}.blocked_claims")
    validate_publication_checks(bundle["publication_checks"], f"{context}.publication_checks")
    validate_source_paths(bundle["source_paths"], f"{context}.source_paths", repo_root)
    validate_scan_paths(bundle["scan_paths"], f"{context}.scan_paths", repo_root)
    validate_no_blocked_markers(bundle, context)

    return {
        "bundle_path": context,
        "schema_path": display_path(schema_path, repo_root),
        "bundle_id": bundle["bundle_id"],
        "status": bundle["status"],
        "release_label": bundle["release_scope"]["release_label"],
        "ranked_targets": len(bundle["ranking_rows"]),
        "blocked_claims": len(bundle["blocked_claims"]),
        "scan_paths": len(bundle["scan_paths"]),
    }


def validate_claim_gate_state(bundle: dict[str, Any], checklist: dict[str, Any], context: str) -> None:
    release_gate = checklist["release_gate"]
    if release_gate["release_allowed"] is not True:
        raise PublicReleaseBundleError(f"{context} source checklist release gate must be allowed")
    if release_gate["release_label"] != bundle["release_scope"]["release_label"]:
        raise PublicReleaseBundleError(f"{context}.release_label does not match M86 checklist")

    allowed_claims = [claim for claim in checklist["claim_outcomes"] if claim["allowed"] is True]
    if len(allowed_claims) != 1 or allowed_claims[0]["claim_id"] != bundle["release_scope"]["allowed_claim_id"]:
        raise PublicReleaseBundleError(f"{context}.allowed_claim_id does not match M86 allowed claim")


def validate_report_state(bundle: dict[str, Any], report: dict[str, Any], context: str) -> None:
    scope = bundle["release_scope"]
    if report["report_status"] != "published_local_ranking":
        raise PublicReleaseBundleError(f"{context} source report must be published_local_ranking")
    if report["ranking_claim_allowed"] is not True:
        raise PublicReleaseBundleError(f"{context} source report ranking_claim_allowed must be true")
    if report["case_set"]["case_set_id"] != scope["case_set_id"]:
        raise PublicReleaseBundleError(f"{context} case_set_id does not match source report")
    if report["case_set"]["case_set_version"] != scope["case_set_version"]:
        raise PublicReleaseBundleError(f"{context} case_set_version does not match source report")

    report_rows = {str(row["model"]): row for row in report["rankings"]}
    bundle_rows = {str(row["model"]): row for row in bundle["ranking_rows"]}
    if set(report_rows) != EXPECTED_RANKED_MODELS:
        raise PublicReleaseBundleError(f"{context} source report ranked models changed")
    if set(bundle_rows) != EXPECTED_RANKED_MODELS:
        raise PublicReleaseBundleError(f"{context} bundle ranked models must match the published report")

    for model in sorted(EXPECTED_RANKED_MODELS):
        report_row = report_rows[model]
        bundle_row = bundle_rows[model]
        expected_ci = f"{report_row['bootstrap_ci_95']['low']:.4f}-{report_row['bootstrap_ci_95']['high']:.4f}"
        comparisons = {
            "rank": report_row["rank"],
            "runtime": report_row["runtime"],
            "weighted_effective": report_row["severity_weighted_effective_pass_rate"],
            "ci_95": expected_ci,
            "sample_size": report_row["sample_size"],
        }
        for field_name, expected_value in comparisons.items():
            if bundle_row[field_name] != expected_value:
                raise PublicReleaseBundleError(f"{context}[{model}].{field_name} does not match source report")


def validate_approved_statement(value: dict[str, str], context: str) -> None:
    statement = f"{value['headline']} {value['summary']}"
    lowered_statement = statement.lower()
    for snippet in EXPECTED_STATEMENT_SNIPPETS:
        if snippet.lower() not in lowered_statement:
            raise PublicReleaseBundleError(f"{context}.summary missing required snippet: {snippet}")
    lowered_qualifier = value["required_qualifier"].lower()
    for snippet in EXPECTED_QUALIFIER_SNIPPETS:
        if snippet.lower() not in lowered_qualifier:
            raise PublicReleaseBundleError(f"{context}.required_qualifier missing required snippet: {snippet}")


def validate_release_artifacts(values: list[dict[str, Any]], context: str, repo_root: Path) -> None:
    artifact_ids = {str(value["artifact_id"]) for value in values}
    missing = sorted(REQUIRED_RELEASE_ARTIFACTS - artifact_ids)
    if missing:
        raise PublicReleaseBundleError(f"{context} missing release artifacts: {', '.join(missing)}")

    seen: set[str] = set()
    for index, value in enumerate(values):
        item_context = f"{context}[{index}]"
        artifact_id = str(value["artifact_id"])
        if artifact_id in seen:
            raise PublicReleaseBundleError(f"{item_context}.artifact_id duplicate value: {artifact_id}")
        seen.add(artifact_id)
        if value["public_safe"] is not True:
            raise PublicReleaseBundleError(f"{item_context}.public_safe must be true")
        if artifact_id in REQUIRED_RELEASE_ARTIFACTS and value["required_for_release"] is not True:
            raise PublicReleaseBundleError(f"{item_context}.required_for_release must be true")
        validate_relative_public_path(value["path"], item_context, repo_root)


def validate_blocked_claims(values: list[dict[str, str]], checklist: dict[str, Any], context: str) -> None:
    checklist_blocked = {
        str(claim["claim_id"]): str(claim["blocker_id"])
        for claim in checklist["claim_outcomes"]
        if claim["allowed"] is False
    }
    bundle_blocked = {str(claim["claim_id"]): str(claim["blocker_id"]) for claim in values}
    missing = sorted(set(checklist_blocked) - set(bundle_blocked))
    if missing:
        raise PublicReleaseBundleError(f"{context} missing blocked claims: {', '.join(missing)}")

    seen: set[str] = set()
    for index, value in enumerate(values):
        item_context = f"{context}[{index}]"
        claim_id = str(value["claim_id"])
        if claim_id in seen:
            raise PublicReleaseBundleError(f"{item_context}.claim_id duplicate value: {claim_id}")
        seen.add(claim_id)
        if checklist_blocked.get(claim_id) != value["blocker_id"]:
            raise PublicReleaseBundleError(f"{item_context}.blocker_id does not match M86 checklist")
        if not value["release_instruction"].startswith("Do not "):
            raise PublicReleaseBundleError(f"{item_context}.release_instruction must start with 'Do not '")
        validate_concrete_text(value["required_unlock"], f"{item_context}.required_unlock")


def validate_publication_checks(values: list[dict[str, str]], context: str) -> None:
    check_ids = {str(value["check_id"]) for value in values}
    missing = sorted(REQUIRED_PUBLICATION_CHECKS - check_ids)
    if missing:
        raise PublicReleaseBundleError(f"{context} missing publication checks: {', '.join(missing)}")

    seen: set[str] = set()
    for index, value in enumerate(values):
        item_context = f"{context}[{index}]"
        check_id = str(value["check_id"])
        if check_id in seen:
            raise PublicReleaseBundleError(f"{item_context}.check_id duplicate value: {check_id}")
        seen.add(check_id)
        if value["status"] != "pass":
            raise PublicReleaseBundleError(f"{item_context}.status must be pass")


def validate_source_paths(values: list[str], context: str, repo_root: Path) -> None:
    for index, value in enumerate(values):
        validate_relative_public_path(value, f"{context}[{index}]", repo_root)


def validate_scan_paths(values: list[str], context: str, repo_root: Path) -> None:
    for index, value in enumerate(values):
        item_context = f"{context}[{index}]"
        path = validate_relative_public_path(value, item_context, repo_root)
        scan_release_doc(path, item_context, repo_root)


def validate_relative_public_path(value: str, context: str, repo_root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        raise PublicReleaseBundleError(f"{context} must be repository-relative")
    resolved = (repo_root / path).resolve()
    try:
        relative_path = resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise PublicReleaseBundleError(f"{context} must stay inside repository") from exc
    if str(relative_path).startswith(("traces/raw/", "reports/private/", "private_evidence/")):
        raise PublicReleaseBundleError(f"{context} must not reference raw or private local artifacts")
    if not resolved.exists():
        raise PublicReleaseBundleError(f"{context} does not exist: {value}")
    return resolved


def scan_release_doc(path: Path, context: str, repo_root: Path) -> None:
    previous_line_boundary = False
    boundary_section = False
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        lowered = line.lower()
        if lowered.startswith("#"):
            boundary_section = is_boundary_section_heading(lowered)
            previous_line_boundary = False
            continue
        if boundary_section:
            continue
        current_line_boundary = is_boundary_line(lowered)
        if not lowered.strip():
            previous_line_boundary = False
            continue
        if current_line_boundary or previous_line_boundary:
            previous_line_boundary = True
            continue
        for label, pattern in POSITIVE_OVERCLAIM_PATTERNS:
            if pattern.search(line):
                display = display_path(path, repo_root)
                raise PublicReleaseBundleError(f"{context} unsupported positive {label} phrasing at {display}:{line_number}")
        previous_line_boundary = False


def is_boundary_line(lowered_line: str) -> bool:
    return any(marker in lowered_line for marker in BOUNDARY_LINE_MARKERS)


def is_boundary_section_heading(lowered_line: str) -> bool:
    return "blocked claim" in lowered_line or "boundary" in lowered_line


def validate_concrete_text(value: str, context: str) -> None:
    lowered = value.lower()
    for marker in VAGUE_MARKERS:
        if marker in lowered:
            raise PublicReleaseBundleError(f"{context} must be concrete, found vague marker: {marker}")


def validate_no_blocked_markers(value: dict[str, Any], context: str) -> None:
    text = str(value)
    for marker in BLOCKED_MARKERS:
        if marker in text:
            raise PublicReleaseBundleError(f"{context} contains blocked marker: {marker}")


def validate_expected_map(value: dict[str, Any], expected: dict[str, Any], context: str) -> None:
    for field_name, expected_value in expected.items():
        if value[field_name] != expected_value:
            raise PublicReleaseBundleError(f"{context}.{field_name} must equal {expected_value!r}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate M87 claim-locked public release bundle metadata.")
    parser.add_argument("bundle", nargs="?", type=Path, default=DEFAULT_BUNDLE_PATH)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = validate_public_release_bundle(args.bundle, args.schema)
    except (PublicReleaseBundleError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"public release bundle: {summary['bundle_path']}")
    print(f"public release schema: {summary['schema_path']}")
    print(f"bundle id: {summary['bundle_id']}")
    print(f"status: {summary['status']}")
    print(f"release label: {summary['release_label']}")
    print(f"ranked targets: {summary['ranked_targets']}")
    print(f"blocked claims: {summary['blocked_claims']}")
    print(f"scan paths: {summary['scan_paths']}")
    print("public release bundle validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
