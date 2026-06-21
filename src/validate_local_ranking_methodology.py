"""Validate the M59 local ranking methodology and example artifacts.

This validator checks committed public-safe methodology artifacts only. It does
not execute local models, providers, agents, networks, tools, credentials,
private logs, gated LLM review, or external actions, and it rejects publishable
ranking claims for the M59 synthetic example.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from local_ranking_methodology import (
    BOOTSTRAP_RESAMPLES,
    DEFAULT_EXAMPLE_INPUT_PATH,
    DEFAULT_EXAMPLE_SNAPSHOT_PATH,
    DEFAULT_METHODOLOGY_PATH,
    HIGH_RISK_SEVERITIES,
    LOCAL_BENCHMARK_CASE_PATH,
    LOCAL_BENCHMARK_MANIFEST_PATH,
    METHODOLOGY_ID,
    SEVERITY_WEIGHTS,
    compute_example_results,
    sha256_file,
)
from reporting_utils import compare_nested_values
from run_eval import load_cases
from schema_validation_utils import display_path, load_json_object, validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/local_ranking_methodology.schema.json"

EXPECTED_SAFE_ASSERTIONS = {
    "public_safe": True,
    "live_execution": False,
    "external_actions": False,
    "contains_private_data": False,
    "credentials_required": False,
    "private_prompts_included": False,
    "raw_outputs_included": False,
}
REQUIRED_METRIC_IDS = {
    "severity_weighted_effective_pass_rate",
    "severity_weighted_heuristic_pass_rate",
    "unweighted_effective_pass_rate",
    "unresolved_review_count",
    "abstention_count",
    "partial_run_exclusion_count",
}
INPUT_REQUIRED_FIELDS = {
    "input_id",
    "input_kind",
    "generated_at",
    "purpose",
    "case_set",
    "runs",
    "source_paths",
    "safety_assertions",
}
RUN_REQUIRED_FIELDS = {
    "run_id",
    "ledger_entry_id",
    "ledger_contract_reference_path",
    "evidence_class",
    "source_kind",
    "synthetic_example",
    "runtime",
    "model",
    "run_status",
    "benchmark_split",
    "planned_case_count",
    "completed_case_count",
    "skipped_case_count",
    "failed_case_count",
    "ledger_ranking_eligible",
    "public_safe",
    "case_results",
    "safety_assertions",
}
CASE_RESULT_REQUIRED_FIELDS = {
    "case_id",
    "risk_area",
    "severity",
    "severity_weight",
    "heuristic_score",
    "effective_score",
    "review_status",
    "effective_score_source",
    "abstained",
    "excluded",
    "failure_modes",
}
REVIEW_STATUSES = {
    "heuristic_only",
    "reviewed_agree",
    "reviewed_override",
    "needs_discussion",
}


class LocalRankingMethodologyValidationError(Exception):
    """Local ranking methodology validation error."""


def validate_local_ranking_methodology(
    methodology_path: Path = DEFAULT_METHODOLOGY_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    example_input_path: Path = DEFAULT_EXAMPLE_INPUT_PATH,
    example_snapshot_path: Path = DEFAULT_EXAMPLE_SNAPSHOT_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the methodology, fake inputs, and non-publishable example."""

    schema = load_json_object(schema_path, "schema", repo_root, LocalRankingMethodologyValidationError)
    methodology = load_json_object(
        methodology_path,
        "local ranking methodology",
        repo_root,
        LocalRankingMethodologyValidationError,
    )
    validate_schema_value(
        methodology,
        schema,
        display_path(methodology_path, repo_root),
        methodology_path,
        repo_root,
        LocalRankingMethodologyValidationError,
    )
    validate_methodology_semantics(methodology, methodology_path, repo_root)

    example_input = load_json_object(
        example_input_path,
        "local ranking methodology fake input",
        repo_root,
        LocalRankingMethodologyValidationError,
    )
    validate_example_input(example_input, methodology, example_input_path, repo_root)

    example_snapshot = load_json_object(
        example_snapshot_path,
        "local ranking methodology example snapshot",
        repo_root,
        LocalRankingMethodologyValidationError,
    )
    validate_example_snapshot(
        example_snapshot,
        methodology,
        example_input,
        methodology_path,
        example_input_path,
        example_snapshot_path,
        repo_root,
    )

    return {
        "methodology_path": display_path(methodology_path, repo_root),
        "schema_path": display_path(schema_path, repo_root),
        "example_input_path": display_path(example_input_path, repo_root),
        "example_snapshot_path": display_path(example_snapshot_path, repo_root),
        "methodology_id": methodology["methodology_id"],
        "metric_count": len(methodology["metric_definitions"]),
        "example_run_count": len(example_input["runs"]),
        "ranking_claim_allowed": example_snapshot["ranking_claim_allowed"],
    }


def validate_methodology_semantics(methodology: dict[str, Any], methodology_path: Path, repo_root: Path) -> None:
    """Validate semantic ranking guardrails not expressible in the schema."""

    context = display_path(methodology_path, repo_root)
    if methodology["methodology_id"] != METHODOLOGY_ID:
        raise LocalRankingMethodologyValidationError(f"{context}.methodology_id must equal {METHODOLOGY_ID}")
    validate_safety_assertions(methodology["safety_assertions"], f"{context}.safety_assertions")
    validate_source_paths(methodology["source_paths"], f"{context}.source_paths", repo_root)

    if "smoke" in methodology["benchmark_scope"]["publishable_splits"]:
        raise LocalRankingMethodologyValidationError(f"{context}.benchmark_scope.publishable_splits must not include smoke")
    excluded_classes = set(methodology["evidence_requirements"]["excluded_evidence_classes"])
    for required in ["private_audit", "manual_public_sample", "evaluator_health", "cloud_public_benchmark"]:
        if required not in excluded_classes:
            raise LocalRankingMethodologyValidationError(
                f"{context}.evidence_requirements.excluded_evidence_classes must include {required}"
            )
    if methodology["severity_weights"] != SEVERITY_WEIGHTS:
        raise LocalRankingMethodologyValidationError(f"{context}.severity_weights must match the M59 severity policy")
    weights = methodology["severity_weights"]
    if not (weights["low"] < weights["medium"] < weights["high"] < weights["critical"]):
        raise LocalRankingMethodologyValidationError(f"{context}.severity_weights must increase with severity")

    metric_ids = [metric["metric_id"] for metric in methodology["metric_definitions"]]
    duplicate_metric_ids = sorted({metric_id for metric_id in metric_ids if metric_ids.count(metric_id) > 1})
    if duplicate_metric_ids:
        raise LocalRankingMethodologyValidationError(
            f"{context}.metric_definitions duplicate metric_id values: {', '.join(duplicate_metric_ids)}"
        )
    missing_metric_ids = sorted(REQUIRED_METRIC_IDS - set(metric_ids))
    if missing_metric_ids:
        raise LocalRankingMethodologyValidationError(
            f"{context}.metric_definitions missing required metrics: {', '.join(missing_metric_ids)}"
        )
    primary_metrics = [metric for metric in methodology["metric_definitions"] if metric["metric_type"] == "primary"]
    if len(primary_metrics) != 1 or primary_metrics[0]["metric_id"] != "severity_weighted_effective_pass_rate":
        raise LocalRankingMethodologyValidationError(
            f"{context}.metric_definitions must have one primary severity_weighted_effective_pass_rate metric"
        )

    if methodology["uncertainty_policy"]["resample_count"] != BOOTSTRAP_RESAMPLES:
        raise LocalRankingMethodologyValidationError(f"{context}.uncertainty_policy.resample_count must equal {BOOTSTRAP_RESAMPLES}")
    if methodology["partial_run_policy"]["rank_partial_runs"] is not False:
        raise LocalRankingMethodologyValidationError(f"{context}.partial_run_policy.rank_partial_runs must be false")
    if methodology["partial_run_policy"]["minimum_completion_rate"] != 1.0:
        raise LocalRankingMethodologyValidationError(f"{context}.partial_run_policy.minimum_completion_rate must equal 1.0")
    if methodology["human_review_policy"]["high_risk_severities"] != HIGH_RISK_SEVERITIES:
        raise LocalRankingMethodologyValidationError(
            f"{context}.human_review_policy.high_risk_severities must equal {HIGH_RISK_SEVERITIES}"
        )
    if methodology["human_review_policy"]["unresolved_needs_discussion_allowed"] is not False:
        raise LocalRankingMethodologyValidationError(
            f"{context}.human_review_policy.unresolved_needs_discussion_allowed must be false"
        )
    if methodology["publication_policy"]["allow_real_rankings_before_m60"] is not False:
        raise LocalRankingMethodologyValidationError(
            f"{context}.publication_policy.allow_real_rankings_before_m60 must be false"
        )
    if methodology["quality_gate_boundary"]["publishes_real_rankings"] is not False:
        raise LocalRankingMethodologyValidationError(
            f"{context}.quality_gate_boundary.publishes_real_rankings must be false"
        )


def validate_example_input(
    example_input: dict[str, Any],
    methodology: dict[str, Any],
    example_input_path: Path,
    repo_root: Path,
) -> None:
    """Validate the synthetic ledger-like input artifact."""

    context = display_path(example_input_path, repo_root)
    require_exact_fields(example_input, INPUT_REQUIRED_FIELDS, context)
    if example_input["input_kind"] != "synthetic_public_safe_methodology_example":
        raise LocalRankingMethodologyValidationError(f"{context}.input_kind must be synthetic_public_safe_methodology_example")
    validate_safety_assertions(example_input["safety_assertions"], f"{context}.safety_assertions")
    validate_source_paths(example_input["source_paths"], f"{context}.source_paths", repo_root)

    cases_by_id = validate_case_set(example_input["case_set"], context, repo_root)
    runs = example_input["runs"]
    if not isinstance(runs, list) or not runs:
        raise LocalRankingMethodologyValidationError(f"{context}.runs must be a non-empty array")
    seen_run_ids: set[str] = set()
    for index, run in enumerate(runs):
        run_context = f"{context}.runs[{index}]"
        validate_example_run(run, methodology, cases_by_id, run_context, repo_root)
        if run["run_id"] in seen_run_ids:
            raise LocalRankingMethodologyValidationError(f"{run_context}.run_id duplicate value: {run['run_id']}")
        seen_run_ids.add(str(run["run_id"]))


def validate_case_set(case_set: dict[str, Any], context: str, repo_root: Path) -> dict[str, dict[str, Any]]:
    """Validate the example's local_public_v1 smoke case-set reference."""

    case_context = f"{context}.case_set"
    expected_fields = {
        "case_set_id",
        "case_set_version",
        "benchmark_split",
        "case_count",
        "case_path",
        "case_file_sha256",
        "manifest_path",
        "manifest_sha256",
    }
    require_exact_fields(case_set, expected_fields, case_context)
    if case_set["case_set_id"] != "local_public_v1" or case_set["case_set_version"] != "1.0.0":
        raise LocalRankingMethodologyValidationError(f"{case_context} must reference local_public_v1 version 1.0.0")
    if case_set["benchmark_split"] != "smoke":
        raise LocalRankingMethodologyValidationError(f"{case_context}.benchmark_split must be smoke for the M59 example")

    case_path = require_existing_repo_path(case_set["case_path"], f"{case_context}.case_path", repo_root)
    manifest_path = require_existing_repo_path(case_set["manifest_path"], f"{case_context}.manifest_path", repo_root)
    if case_path != LOCAL_BENCHMARK_CASE_PATH:
        raise LocalRankingMethodologyValidationError(f"{case_context}.case_path must equal evals/benchmarks/local_public_v1/cases.jsonl")
    if manifest_path != LOCAL_BENCHMARK_MANIFEST_PATH:
        raise LocalRankingMethodologyValidationError(
            f"{case_context}.manifest_path must equal evals/benchmarks/local_public_v1/manifest.json"
        )
    validate_hash(case_path, case_set["case_file_sha256"], f"{case_context}.case_file_sha256", repo_root)
    validate_hash(manifest_path, case_set["manifest_sha256"], f"{case_context}.manifest_sha256", repo_root)
    manifest = load_json_object(manifest_path, "local benchmark manifest", repo_root, LocalRankingMethodologyValidationError)
    if manifest["case_file_sha256"] != case_set["case_file_sha256"]:
        raise LocalRankingMethodologyValidationError(f"{case_context}.case_file_sha256 must match local_public_v1 manifest")

    smoke_cases = [case for case in load_cases([case_path]) if "smoke" in case.get("benchmark_splits", [])]
    if len(smoke_cases) != int(case_set["case_count"]):
        raise LocalRankingMethodologyValidationError(f"{case_context}.case_count must match smoke split case count")
    return {str(case["case_id"]): case for case in smoke_cases}


def validate_example_run(
    run: dict[str, Any],
    methodology: dict[str, Any],
    cases_by_id: dict[str, dict[str, Any]],
    context: str,
    repo_root: Path,
) -> None:
    """Validate one synthetic run summary."""

    require_exact_fields(run, RUN_REQUIRED_FIELDS, context)
    validate_safety_assertions(run["safety_assertions"], f"{context}.safety_assertions")
    require_existing_repo_path(run["ledger_contract_reference_path"], f"{context}.ledger_contract_reference_path", repo_root)
    if run["source_kind"] != "synthetic_methodology_example" or run["synthetic_example"] is not True:
        raise LocalRankingMethodologyValidationError(f"{context}.source_kind must be a synthetic methodology example")
    if run["evidence_class"] == "private_audit":
        raise LocalRankingMethodologyValidationError(f"{context}.evidence_class private_audit cannot be ranked")
    if run["evidence_class"] != methodology["evidence_requirements"]["ranking_evidence_class"]:
        raise LocalRankingMethodologyValidationError(f"{context}.evidence_class must be local_public_benchmark")
    if run["run_status"] != "succeeded":
        raise LocalRankingMethodologyValidationError(f"{context}.run_status must be succeeded; partial runs are exclusions")
    if run["benchmark_split"] != "smoke":
        raise LocalRankingMethodologyValidationError(f"{context}.benchmark_split must be smoke for the example")
    if run["public_safe"] is not True:
        raise LocalRankingMethodologyValidationError(f"{context}.public_safe must equal true")

    planned = int(run["planned_case_count"])
    completed = int(run["completed_case_count"])
    if planned != len(cases_by_id) or completed != len(cases_by_id):
        raise LocalRankingMethodologyValidationError(f"{context}.completed_case_count must equal the full smoke split")
    if run["skipped_case_count"] != 0 or run["failed_case_count"] != 0:
        raise LocalRankingMethodologyValidationError(f"{context} must not skip or fail synthetic methodology cases")
    if run["ledger_ranking_eligible"] is not True:
        raise LocalRankingMethodologyValidationError(f"{context}.ledger_ranking_eligible must equal true for the fake complete example")

    case_results = run["case_results"]
    if not isinstance(case_results, list) or len(case_results) != len(cases_by_id):
        raise LocalRankingMethodologyValidationError(f"{context}.case_results must contain one result per smoke case")
    seen_case_ids: set[str] = set()
    for index, result in enumerate(case_results):
        result_context = f"{context}.case_results[{index}]"
        validate_case_result(result, methodology, cases_by_id, result_context)
        if result["case_id"] in seen_case_ids:
            raise LocalRankingMethodologyValidationError(f"{result_context}.case_id duplicate value: {result['case_id']}")
        seen_case_ids.add(str(result["case_id"]))
    if seen_case_ids != set(cases_by_id):
        missing = sorted(set(cases_by_id) - seen_case_ids)
        extra = sorted(seen_case_ids - set(cases_by_id))
        raise LocalRankingMethodologyValidationError(
            f"{context}.case_results must match smoke split cases; missing={missing}, extra={extra}"
        )


def validate_case_result(
    result: dict[str, Any],
    methodology: dict[str, Any],
    cases_by_id: dict[str, dict[str, Any]],
    context: str,
) -> None:
    """Validate one synthetic case-result summary."""

    require_exact_fields(result, CASE_RESULT_REQUIRED_FIELDS, context)
    case_id = str(result["case_id"])
    if case_id not in cases_by_id:
        raise LocalRankingMethodologyValidationError(f"{context}.case_id unknown smoke case: {case_id}")
    case = cases_by_id[case_id]
    if result["risk_area"] != case["risk_area"]:
        raise LocalRankingMethodologyValidationError(f"{context}.risk_area must match local_public_v1 case")
    if result["severity"] != case["severity"]:
        raise LocalRankingMethodologyValidationError(f"{context}.severity must match local_public_v1 case")
    expected_weight = methodology["severity_weights"][str(result["severity"])]
    if result["severity_weight"] != expected_weight:
        raise LocalRankingMethodologyValidationError(f"{context}.severity_weight must match methodology severity_weights")
    for field_name in ["heuristic_score", "effective_score"]:
        value = result[field_name]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0 or value > 1:
            raise LocalRankingMethodologyValidationError(f"{context}.{field_name} must be a number from 0 to 1")
    if result["review_status"] not in REVIEW_STATUSES:
        raise LocalRankingMethodologyValidationError(f"{context}.review_status has unsupported value")
    if result["review_status"] == "needs_discussion":
        raise LocalRankingMethodologyValidationError(f"{context}.review_status unresolved review is not allowed")
    if result["effective_score_source"] not in {"heuristic", "human_review"}:
        raise LocalRankingMethodologyValidationError(f"{context}.effective_score_source has unsupported value")
    if result["review_status"] == "heuristic_only" and result["effective_score_source"] != "heuristic":
        raise LocalRankingMethodologyValidationError(f"{context}.effective_score_source must be heuristic for heuristic_only")
    if result["review_status"] in {"reviewed_agree", "reviewed_override"} and result["effective_score_source"] != "human_review":
        raise LocalRankingMethodologyValidationError(f"{context}.effective_score_source must be human_review for reviewed cases")
    if result["abstained"] is True and (result["heuristic_score"] != 0.0 or result["effective_score"] != 0.0):
        raise LocalRankingMethodologyValidationError(f"{context}.abstained cases must score 0")
    if result["excluded"] is not False:
        raise LocalRankingMethodologyValidationError(f"{context}.excluded must be false in the complete example")
    if not isinstance(result["failure_modes"], list):
        raise LocalRankingMethodologyValidationError(f"{context}.failure_modes must be an array")
    if result["effective_score"] < 1.0 and not result["failure_modes"]:
        raise LocalRankingMethodologyValidationError(f"{context}.failure_modes must explain failed synthetic cases")


def validate_example_snapshot(
    snapshot: dict[str, Any],
    methodology: dict[str, Any],
    example_input: dict[str, Any],
    methodology_path: Path,
    example_input_path: Path,
    example_snapshot_path: Path,
    repo_root: Path,
) -> None:
    """Validate generated example metrics and non-publishable status."""

    context = display_path(example_snapshot_path, repo_root)
    expected_fields = {
        "snapshot_id",
        "snapshot_kind",
        "generated_at",
        "publication_status",
        "ranking_claim_allowed",
        "methodology",
        "input",
        "case_set",
        "ranking_policy",
        "example_results",
        "boundaries",
        "safety_assertions",
    }
    require_exact_fields(snapshot, expected_fields, context)
    if snapshot["snapshot_kind"] != "methodology_example_only":
        raise LocalRankingMethodologyValidationError(f"{context}.snapshot_kind must be methodology_example_only")
    if snapshot["publication_status"] != "example_only_not_publishable":
        raise LocalRankingMethodologyValidationError(f"{context}.publication_status must be example_only_not_publishable")
    if snapshot["ranking_claim_allowed"] is not False:
        raise LocalRankingMethodologyValidationError(f"{context}.ranking_claim_allowed must be false")
    validate_safety_assertions(snapshot["safety_assertions"], f"{context}.safety_assertions")
    if snapshot["methodology"]["methodology_sha256"] != sha256_file(methodology_path):
        raise LocalRankingMethodologyValidationError(f"{context}.methodology.methodology_sha256 must match methodology file")
    if snapshot["input"]["input_sha256"] != sha256_file(example_input_path):
        raise LocalRankingMethodologyValidationError(f"{context}.input.input_sha256 must match fake input file")
    if snapshot["case_set"] != example_input["case_set"]:
        raise LocalRankingMethodologyValidationError(f"{context}.case_set must match fake input case_set")
    if snapshot["ranking_policy"]["severity_weights"] != methodology["severity_weights"]:
        raise LocalRankingMethodologyValidationError(f"{context}.ranking_policy.severity_weights must match methodology")
    expected_results = compute_example_results(methodology, example_input)
    differences = compare_nested_values(expected_results, snapshot["example_results"])
    if differences:
        raise LocalRankingMethodologyValidationError(
            f"{context}.example_results are not reproducible: {'; '.join(differences[:3])}"
        )
    if any(result["public_ranking_eligible"] is not False for result in snapshot["example_results"]):
        raise LocalRankingMethodologyValidationError(f"{context}.example_results must remain public_ranking_eligible=false")


def validate_safety_assertions(value: dict[str, Any], context: str) -> None:
    for field_name, expected_value in EXPECTED_SAFE_ASSERTIONS.items():
        if value.get(field_name) is not expected_value:
            raise LocalRankingMethodologyValidationError(f"{context}.{field_name} must equal {expected_value!r}")


def validate_source_paths(source_paths: list[str], context: str, repo_root: Path) -> None:
    for index, source_path in enumerate(source_paths):
        require_existing_repo_path(source_path, f"{context}[{index}]", repo_root)


def validate_hash(path: Path, expected_hash: str, context: str, repo_root: Path) -> None:
    if sha256_file(path) != expected_hash:
        raise LocalRankingMethodologyValidationError(
            f"{context} must match sha256 of {display_path(path, repo_root)}"
        )


def require_exact_fields(value: dict[str, Any], expected_fields: set[str], context: str) -> None:
    missing = sorted(expected_fields - set(value))
    if missing:
        raise LocalRankingMethodologyValidationError(f"{context}: missing required fields: {', '.join(missing)}")
    unexpected = sorted(set(value) - expected_fields)
    if unexpected:
        raise LocalRankingMethodologyValidationError(f"{context}: unexpected fields: {', '.join(unexpected)}")


def require_existing_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise LocalRankingMethodologyValidationError(f"{context} must be a non-empty string")
    path = Path(value)
    if path.is_absolute():
        raise LocalRankingMethodologyValidationError(f"{context} must be repository-relative")
    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise LocalRankingMethodologyValidationError(f"{context} must stay within the repository") from exc
    if not resolved.exists():
        raise LocalRankingMethodologyValidationError(f"{context} does not exist: {display_path(resolved, repo_root)}")
    return resolved


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the M59 local ranking methodology.")
    parser.add_argument("methodology", nargs="?", type=Path, default=DEFAULT_METHODOLOGY_PATH)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument("--example-input", type=Path, default=DEFAULT_EXAMPLE_INPUT_PATH)
    parser.add_argument("--example-snapshot", type=Path, default=DEFAULT_EXAMPLE_SNAPSHOT_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = validate_local_ranking_methodology(
            args.methodology,
            args.schema,
            args.example_input,
            args.example_snapshot,
        )
    except (LocalRankingMethodologyValidationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"local ranking methodology path: {summary['methodology_path']}")
    print(f"local ranking methodology schema: {summary['schema_path']}")
    print(f"fake ledger input path: {summary['example_input_path']}")
    print(f"example snapshot path: {summary['example_snapshot_path']}")
    print(f"methodology id: {summary['methodology_id']}")
    print(f"metrics: {summary['metric_count']}")
    print(f"example runs: {summary['example_run_count']}")
    print(f"ranking claim allowed: {str(summary['ranking_claim_allowed']).lower()}")
    print("local ranking methodology validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
