"""Validate M86 public-safe claim-review and release checklist metadata.

The checklist is a claim boundary gate. It validates committed metadata only and
does not read raw outputs, run local models, submit hosted-provider jobs, inspect
private evidence, call networks, or perform external actions.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from schema_validation_utils import display_path, load_json_object, validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHECKLIST_PATH = REPO_ROOT / "traces/external/claim_review_checklist.example.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/claim_review_checklist.schema.json"

LOCAL_REPORT_PATH = REPO_ROOT / "reports/comparisons/local_open_weight_benchmark_v1.json"
CHARTER_PATH = REPO_ROOT / "benchmarks/evidence_class_charter.json"
RUNBOOK_PATH = REPO_ROOT / "traces/external/real_model_proof_runbook.example.json"
RUNTIME_STABILITY_PATH = REPO_ROOT / "traces/external/runtime_stability_profile.example.json"
HOSTED_PROVIDER_PATH = REPO_ROOT / "traces/external/hosted_provider_batch_metadata.example.json"

EXPECTED_QUALITY_GATE = {
    "checklist_validation_in_quality_gate": True,
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
REQUIRED_SOURCE_IDS = {
    "evidence_class_charter",
    "local_open_weight_report",
    "real_model_proof_runbook",
    "runtime_stability_profile",
    "hosted_provider_batch_metadata",
    "m84_reproducibility_packet",
}
REQUIRED_RELEASE_CHECKS = {
    "evidence_class_matches_report",
    "current_ranked_ledgers_present",
    "only_ranked_targets_are_eligible",
    "hosted_provider_separation_enforced",
    "private_evidence_boundary_enforced",
    "report_status_publishable",
    "reproducibility_boundary_limited",
    "blocked_claims_named",
}
REQUIRED_CLAIMS = {
    "local_open_weight_ranking",
    "cloud_model_ranking",
    "hosted_provider_comparison",
    "production_safety",
    "third_party_reproducibility",
    "private_audit",
    "smoke_control_ranking",
    "gemma4_deferred_target_ranking",
    "raw_output_publication",
}
ALLOWED_CLAIM_ID = "local_open_weight_ranking"
RANKED_MODELS = {
    "deepseek-coder:6.7b-instruct",
    "llama3.2:latest",
    "glm4:latest",
    "codellama:7b-instruct",
    "qwen3.5:2b-q4_K_M",
    "mistral:latest",
}
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
VAGUE_BLOCKER_MARKERS = [
    "missing context",
    "unknown",
    "tbd",
    "to be determined",
]


class ClaimReviewChecklistError(Exception):
    """Claim review checklist validation error."""


def validate_claim_review_checklist(
    checklist_path: Path = DEFAULT_CHECKLIST_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the committed M86 claim-review checklist."""

    schema = load_json_object(schema_path, "claim review checklist schema", repo_root, ClaimReviewChecklistError)
    checklist = load_json_object(checklist_path, "claim review checklist", repo_root, ClaimReviewChecklistError)
    context = display_path(checklist_path, repo_root)

    validate_schema_value(checklist, schema, context, checklist_path, repo_root, ClaimReviewChecklistError)
    validate_expected_map(checklist["quality_gate"], EXPECTED_QUALITY_GATE, f"{context}.quality_gate")
    validate_expected_map(checklist["safety_assertions"], EXPECTED_SAFETY_ASSERTIONS, f"{context}.safety_assertions")
    validate_release_gate(checklist["release_gate"], f"{context}.release_gate")
    validate_release_checks(checklist["release_checks"], f"{context}.release_checks")
    validate_claim_outcomes(checklist["claim_outcomes"], f"{context}.claim_outcomes")
    validate_blocked_gates(checklist["blocked_gates"], checklist["claim_outcomes"], f"{context}.blocked_gates")
    validate_source_paths(checklist["source_paths"], f"{context}.source_paths", repo_root)
    validate_reviewed_sources(checklist["reviewed_sources"], f"{context}.reviewed_sources", repo_root)
    validate_external_source_state(checklist, context, repo_root)
    validate_no_blocked_markers(checklist, context)

    return {
        "checklist_path": context,
        "schema_path": display_path(schema_path, repo_root),
        "checklist_id": checklist["checklist_id"],
        "status": checklist["status"],
        "release_allowed": checklist["release_gate"]["release_allowed"],
        "release_label": checklist["release_gate"]["release_label"],
        "allowed_claims": sum(1 for claim in checklist["claim_outcomes"] if claim["allowed"]),
        "blocked_claims": sum(1 for claim in checklist["claim_outcomes"] if not claim["allowed"]),
        "ranked_targets": len(checklist["ranked_targets"]),
    }


def validate_release_gate(value: dict[str, Any], context: str) -> None:
    if value["release_allowed"] is not True:
        raise ClaimReviewChecklistError(f"{context}.release_allowed must be true for the current local release")
    if value["blocked_claims_must_be_named"] is not True:
        raise ClaimReviewChecklistError(f"{context}.blocked_claims_must_be_named must be true")
    if value["overclaim_release_allowed"] is not False:
        raise ClaimReviewChecklistError(f"{context}.overclaim_release_allowed must be false")


def validate_release_checks(values: list[dict[str, Any]], context: str) -> None:
    check_ids = {str(value["check_id"]) for value in values}
    missing = sorted(REQUIRED_RELEASE_CHECKS - check_ids)
    if missing:
        raise ClaimReviewChecklistError(f"{context} missing release checks: {', '.join(missing)}")

    seen: set[str] = set()
    for index, value in enumerate(values):
        item_context = f"{context}[{index}]"
        check_id = str(value["check_id"])
        if check_id in seen:
            raise ClaimReviewChecklistError(f"{item_context}.check_id duplicate value: {check_id}")
        seen.add(check_id)
        if value["status"] != "pass":
            raise ClaimReviewChecklistError(f"{item_context}.status must be pass")
        if value["blocker_id"] != "none":
            raise ClaimReviewChecklistError(f"{item_context}.blocker_id must be none for passing release checks")


def validate_claim_outcomes(values: list[dict[str, Any]], context: str) -> None:
    claim_ids = {str(value["claim_id"]) for value in values}
    missing = sorted(REQUIRED_CLAIMS - claim_ids)
    if missing:
        raise ClaimReviewChecklistError(f"{context} missing claim outcomes: {', '.join(missing)}")

    allowed_claims = [value for value in values if value["allowed"] is True]
    if [value["claim_id"] for value in allowed_claims] != [ALLOWED_CLAIM_ID]:
        raise ClaimReviewChecklistError(f"{context} must allow only {ALLOWED_CLAIM_ID}")

    seen: set[str] = set()
    for index, value in enumerate(values):
        item_context = f"{context}[{index}]"
        claim_id = str(value["claim_id"])
        if claim_id in seen:
            raise ClaimReviewChecklistError(f"{item_context}.claim_id duplicate value: {claim_id}")
        seen.add(claim_id)

        if claim_id == ALLOWED_CLAIM_ID:
            if value["outcome"] != "allowed" or value["blocker_id"] != "none":
                raise ClaimReviewChecklistError(f"{item_context} allowed local claim must not have a blocker")
            if "local/open-weight" not in value["boundary"]:
                raise ClaimReviewChecklistError(f"{item_context}.boundary must label the allowed scope local/open-weight")
            continue

        if value["outcome"] != "blocked":
            raise ClaimReviewChecklistError(f"{item_context}.outcome must be blocked")
        if value["blocker_id"] == "none":
            raise ClaimReviewChecklistError(f"{item_context}.blocker_id must name a concrete blocker")


def validate_blocked_gates(
    blocked_gates: list[dict[str, Any]], claim_outcomes: list[dict[str, Any]], context: str
) -> None:
    blocked_claims = {value["claim_id"]: value["blocker_id"] for value in claim_outcomes if not value["allowed"]}
    blocker_ids = {str(value["blocker_id"]) for value in blocked_gates}
    missing_blockers = sorted(set(blocked_claims.values()) - blocker_ids)
    if missing_blockers:
        raise ClaimReviewChecklistError(f"{context} missing blockers: {', '.join(missing_blockers)}")

    seen: set[str] = set()
    for index, value in enumerate(blocked_gates):
        item_context = f"{context}[{index}]"
        blocker_id = str(value["blocker_id"])
        if blocker_id in seen:
            raise ClaimReviewChecklistError(f"{item_context}.blocker_id duplicate value: {blocker_id}")
        seen.add(blocker_id)
        claim_id = str(value["claim_id"])
        if blocked_claims.get(claim_id) != blocker_id:
            raise ClaimReviewChecklistError(f"{item_context} must match a blocked claim outcome")
        if value["blocks_current_allowed_release"] is not False:
            raise ClaimReviewChecklistError(f"{item_context}.blocks_current_allowed_release must be false")
        validate_concrete_text(value["concrete_blocker"], f"{item_context}.concrete_blocker")
        validate_concrete_text(value["required_unlock"], f"{item_context}.required_unlock")


def validate_reviewed_sources(values: list[dict[str, Any]], context: str, repo_root: Path) -> None:
    source_ids = {str(value["source_id"]) for value in values}
    missing = sorted(REQUIRED_SOURCE_IDS - source_ids)
    if missing:
        raise ClaimReviewChecklistError(f"{context} missing reviewed sources: {', '.join(missing)}")

    seen: set[str] = set()
    for index, value in enumerate(values):
        item_context = f"{context}[{index}]"
        source_id = str(value["source_id"])
        if source_id in seen:
            raise ClaimReviewChecklistError(f"{item_context}.source_id duplicate value: {source_id}")
        seen.add(source_id)
        validate_relative_public_path(value["path"], item_context, repo_root)


def validate_external_source_state(checklist: dict[str, Any], context: str, repo_root: Path) -> None:
    report = load_json_object(LOCAL_REPORT_PATH, "local benchmark report", repo_root, ClaimReviewChecklistError)
    charter = load_json_object(CHARTER_PATH, "evidence class charter", repo_root, ClaimReviewChecklistError)
    runbook = load_json_object(RUNBOOK_PATH, "real model proof runbook", repo_root, ClaimReviewChecklistError)
    stability = load_json_object(RUNTIME_STABILITY_PATH, "runtime stability profile", repo_root, ClaimReviewChecklistError)
    hosted = load_json_object(HOSTED_PROVIDER_PATH, "hosted provider metadata", repo_root, ClaimReviewChecklistError)

    validate_report_state(checklist["reviewed_report"], checklist["ranked_targets"], report, f"{context}.reviewed_report")
    validate_charter_state(charter, f"{context}.reviewed_sources.evidence_class_charter")
    validate_runbook_state(runbook, f"{context}.reviewed_sources.real_model_proof_runbook")
    validate_stability_state(stability, f"{context}.reviewed_sources.runtime_stability_profile")
    validate_hosted_provider_state(hosted, f"{context}.reviewed_sources.hosted_provider_batch_metadata")


def validate_report_state(
    reviewed_report: dict[str, Any], ranked_targets: list[dict[str, Any]], report: dict[str, Any], context: str
) -> None:
    if report["snapshot_id"] != reviewed_report["snapshot_id"]:
        raise ClaimReviewChecklistError(f"{context}.snapshot_id does not match local report")
    if report["report_status"] != reviewed_report["report_status"]:
        raise ClaimReviewChecklistError(f"{context}.report_status does not match local report")
    if report["ranking_claim_allowed"] != reviewed_report["ranking_claim_allowed"]:
        raise ClaimReviewChecklistError(f"{context}.ranking_claim_allowed does not match local report")
    eligible_count = report["eligibility_summary"]["eligible_ranked_targets"]
    if eligible_count != reviewed_report["eligible_ranked_targets"]:
        raise ClaimReviewChecklistError(f"{context}.eligible_ranked_targets does not match local report")
    if reviewed_report["evidence_class"] != "local_public_benchmark":
        raise ClaimReviewChecklistError(f"{context}.evidence_class must be local_public_benchmark")
    if report["safety_assertions"]["raw_outputs_included"] is not False:
        raise ClaimReviewChecklistError(f"{context} local report must exclude raw outputs")

    report_targets = {
        str(value["model"]): {
            "runtime": value["runtime"],
            "benchmark_split": value["benchmark_split"],
            "sample_size": value["sample_size"],
            "ledger_entry_id": value["ledger_entry_id"],
            "unresolved_review_count": value["unresolved_review_count"],
        }
        for value in report["rankings"]
    }
    if set(report_targets) != RANKED_MODELS:
        raise ClaimReviewChecklistError(f"{context} local report ranked models must match current ranking")

    checklist_targets = {str(value["model"]): value for value in ranked_targets}
    if set(checklist_targets) != RANKED_MODELS:
        raise ClaimReviewChecklistError(f"{context}.ranked_targets must match ranked report models")
    for model in sorted(RANKED_MODELS):
        report_target = report_targets[model]
        checklist_target = checklist_targets[model]
        for field_name in ("runtime", "benchmark_split", "sample_size", "ledger_entry_id"):
            if checklist_target[field_name] != report_target[field_name]:
                raise ClaimReviewChecklistError(f"{context}.ranked_targets[{model}].{field_name} does not match report")
        if checklist_target["ranking_eligible"] is not True:
            raise ClaimReviewChecklistError(f"{context}.ranked_targets[{model}].ranking_eligible must be true")
        if report_target["unresolved_review_count"] != 0:
            raise ClaimReviewChecklistError(f"{context}.ranked_targets[{model}] has unresolved reviews")


def validate_charter_state(charter: dict[str, Any], context: str) -> None:
    local_classes = [
        value
        for value in charter["evidence_classes"]
        if value["evidence_class_id"] == "local_public_benchmark"
    ]
    if len(local_classes) != 1:
        raise ClaimReviewChecklistError(f"{context} must define local_public_benchmark exactly once")
    if local_classes[0]["public_ranking_eligible"] is not True:
        raise ClaimReviewChecklistError(f"{context}.local_public_benchmark must be public ranking eligible")
    if charter["ranking_rules"]["cloud_rankings_require_cloud_evidence"] is not True:
        raise ClaimReviewChecklistError(f"{context} must require cloud evidence for cloud rankings")
    if charter["ranking_rules"]["private_only_evidence_excluded_from_public_rankings"] is not True:
        raise ClaimReviewChecklistError(f"{context} must exclude private-only evidence from public rankings")


def validate_runbook_state(runbook: dict[str, Any], context: str) -> None:
    if runbook["publication_gate"]["local_ranking_claim_allowed"] is not True:
        raise ClaimReviewChecklistError(f"{context}.publication_gate.local_ranking_claim_allowed must be true")
    if runbook["hosted_provider_path"]["mixed_with_local_ranking"] is not False:
        raise ClaimReviewChecklistError(f"{context}.hosted_provider_path.mixed_with_local_ranking must be false")
    excluded = {value["model"]: value for value in runbook["model_lineup"]["excluded_targets"]}
    if excluded["gemma4:latest"]["eligible_for_local_ranking"] is not False:
        raise ClaimReviewChecklistError(f"{context} must keep gemma4:latest ranking-ineligible")
    if excluded["gemma4:31b-cloud"]["eligible_for_local_ranking"] is not False:
        raise ClaimReviewChecklistError(f"{context} must keep cloud-labelled target ranking-ineligible")


def validate_stability_state(stability: dict[str, Any], context: str) -> None:
    validate_expected_map(
        stability["safety_assertions"],
        {
            "metadata_only": True,
            "contains_raw_outputs": False,
            "production_safety_claim": False,
            "third_party_reproducibility_claim": False,
            "ranking_claim_from_interrupted_runs": False,
        },
        f"{context}.safety_assertions",
    )
    model_profiles = {value["model"]: value for value in stability["model_profiles"]}
    for model in sorted(RANKED_MODELS):
        if model_profiles[model]["ranking_eligible"] is not True:
            raise ClaimReviewChecklistError(f"{context} must keep current ranked targets ranking-eligible")
    if model_profiles["gemma4:latest"]["status"] != "deferred_after_swap_activity":
        raise ClaimReviewChecklistError(f"{context} must keep gemma4:latest deferred")


def validate_hosted_provider_state(hosted: dict[str, Any], context: str) -> None:
    if hosted["batch"]["submitted"] is not False:
        raise ClaimReviewChecklistError(f"{context}.batch.submitted must be false")
    if hosted["batch"]["result_file_available"] is not False:
        raise ClaimReviewChecklistError(f"{context}.batch.result_file_available must be false")
    if hosted["separation_boundary"]["separate_from_local_open_weight_rankings"] is not True:
        raise ClaimReviewChecklistError(f"{context} must stay separate from local rankings")
    if hosted["separation_boundary"]["mixed_provider_comparison_allowed"] is not False:
        raise ClaimReviewChecklistError(f"{context}.mixed_provider_comparison_allowed must be false")
    if hosted["quality_gate"]["provider_calls_in_quality_gate"] is not False:
        raise ClaimReviewChecklistError(f"{context}.provider_calls_in_quality_gate must be false")


def validate_source_paths(values: list[str], context: str, repo_root: Path) -> None:
    for index, value in enumerate(values):
        validate_relative_public_path(value, f"{context}[{index}]", repo_root)


def validate_relative_public_path(value: str, context: str, repo_root: Path) -> None:
    path = Path(value)
    if path.is_absolute():
        raise ClaimReviewChecklistError(f"{context} must be repository-relative")
    resolved = (repo_root / path).resolve()
    try:
        relative_path = resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ClaimReviewChecklistError(f"{context} must stay inside repository") from exc
    if str(relative_path).startswith(("traces/raw/", "reports/private/", "private_evidence/")):
        raise ClaimReviewChecklistError(f"{context} must not reference raw or private local artifacts")
    if not resolved.exists():
        raise ClaimReviewChecklistError(f"{context} does not exist: {value}")


def validate_concrete_text(value: str, context: str) -> None:
    lowered = value.lower()
    for marker in VAGUE_BLOCKER_MARKERS:
        if marker in lowered:
            raise ClaimReviewChecklistError(f"{context} must be concrete, found vague marker: {marker}")


def validate_no_blocked_markers(value: dict[str, Any], context: str) -> None:
    text = str(value)
    for marker in BLOCKED_MARKERS:
        if marker in text:
            raise ClaimReviewChecklistError(f"{context} contains blocked marker: {marker}")


def validate_expected_map(value: dict[str, Any], expected: dict[str, Any], context: str) -> None:
    for field_name, expected_value in expected.items():
        if value[field_name] != expected_value:
            raise ClaimReviewChecklistError(f"{context}.{field_name} must equal {expected_value!r}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate M86 claim-review and release checklist metadata.")
    parser.add_argument("checklist", nargs="?", type=Path, default=DEFAULT_CHECKLIST_PATH)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = validate_claim_review_checklist(args.checklist, args.schema)
    except (ClaimReviewChecklistError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"claim review checklist: {summary['checklist_path']}")
    print(f"claim review schema: {summary['schema_path']}")
    print(f"checklist id: {summary['checklist_id']}")
    print(f"status: {summary['status']}")
    print(f"release allowed: {str(summary['release_allowed']).lower()}")
    print(f"release label: {summary['release_label']}")
    print(f"ranked targets: {summary['ranked_targets']}")
    print(f"allowed claims: {summary['allowed_claims']}")
    print(f"blocked claims: {summary['blocked_claims']}")
    print("claim review checklist validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
