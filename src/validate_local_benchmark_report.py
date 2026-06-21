"""Validate the M60 local/open-weight benchmark report.

The validator checks the public-safe report snapshot and its source hashes. It
does not execute local models, providers, agents, networks, tools, credentials,
private logs, gated LLM review, or external actions.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from local_benchmark_report import (
    DEFAULT_REPORT_PATH,
    DEFAULT_SNAPSHOT_PATH,
    LOCAL_BENCHMARK_CASE_PATH,
    LOCAL_BENCHMARK_MANIFEST_PATH,
    SNAPSHOT_ID,
    sha256_file,
)
from local_ranking_methodology import DEFAULT_METHODOLOGY_PATH
from schema_validation_utils import display_path, load_json_object, validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/local_benchmark_report.schema.json"

EXPECTED_SAFE_ASSERTIONS = {
    "public_safe": True,
    "live_execution": False,
    "external_actions": False,
    "contains_private_data": False,
    "credentials_required": False,
    "private_prompts_included": False,
    "raw_outputs_included": False,
}


class LocalBenchmarkReportValidationError(Exception):
    """Local benchmark report validation error."""


def validate_local_benchmark_report(
    snapshot_path: Path = DEFAULT_SNAPSHOT_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the M60 benchmark report snapshot and return a summary."""

    schema = load_json_object(schema_path, "schema", repo_root, LocalBenchmarkReportValidationError)
    snapshot = load_json_object(snapshot_path, "local benchmark report", repo_root, LocalBenchmarkReportValidationError)
    validate_schema_value(
        snapshot,
        schema,
        display_path(snapshot_path, repo_root),
        snapshot_path,
        repo_root,
        LocalBenchmarkReportValidationError,
    )
    validate_snapshot_semantics(snapshot, snapshot_path, report_path, repo_root)
    return {
        "snapshot_path": display_path(snapshot_path, repo_root),
        "schema_path": display_path(schema_path, repo_root),
        "report_path": display_path(report_path, repo_root),
        "snapshot_id": snapshot["snapshot_id"],
        "report_status": snapshot["report_status"],
        "ranking_claim_allowed": snapshot["ranking_claim_allowed"],
        "rankings": len(snapshot["rankings"]),
        "excluded_evidence": len(snapshot["excluded_evidence"]),
    }


def validate_snapshot_semantics(
    snapshot: dict[str, Any],
    snapshot_path: Path,
    report_path: Path,
    repo_root: Path,
) -> None:
    """Validate report semantics that go beyond schema shape."""

    context = display_path(snapshot_path, repo_root)
    if snapshot["snapshot_id"] != SNAPSHOT_ID:
        raise LocalBenchmarkReportValidationError(f"{context}.snapshot_id must equal {SNAPSHOT_ID}")
    validate_safety_assertions(snapshot["safety_assertions"], f"{context}.safety_assertions")
    validate_source_paths(snapshot["source_paths"], f"{context}.source_paths", repo_root)
    require_existing_repo_path(report_path, "report path", repo_root)

    methodology_path = require_existing_repo_path(
        snapshot["methodology"]["methodology_path"],
        f"{context}.methodology.methodology_path",
        repo_root,
    )
    if methodology_path != DEFAULT_METHODOLOGY_PATH:
        raise LocalBenchmarkReportValidationError(
            f"{context}.methodology.methodology_path must equal benchmarks/local_ranking_methodology.json"
        )
    validate_hash(methodology_path, snapshot["methodology"]["methodology_sha256"], f"{context}.methodology.methodology_sha256", repo_root)

    case_path = require_existing_repo_path(snapshot["case_set"]["case_path"], f"{context}.case_set.case_path", repo_root)
    manifest_path = require_existing_repo_path(snapshot["case_set"]["manifest_path"], f"{context}.case_set.manifest_path", repo_root)
    if case_path != LOCAL_BENCHMARK_CASE_PATH:
        raise LocalBenchmarkReportValidationError(f"{context}.case_set.case_path must reference local_public_v1 cases")
    if manifest_path != LOCAL_BENCHMARK_MANIFEST_PATH:
        raise LocalBenchmarkReportValidationError(f"{context}.case_set.manifest_path must reference local_public_v1 manifest")
    validate_hash(case_path, snapshot["case_set"]["case_file_sha256"], f"{context}.case_set.case_file_sha256", repo_root)
    validate_hash(manifest_path, snapshot["case_set"]["manifest_sha256"], f"{context}.case_set.manifest_sha256", repo_root)
    if "smoke" in snapshot["case_set"]["publishable_splits"]:
        raise LocalBenchmarkReportValidationError(f"{context}.case_set.publishable_splits must not include smoke")

    validate_evidence_sources(snapshot, context, repo_root)
    validate_status_and_rankings(snapshot, context)


def validate_evidence_sources(snapshot: dict[str, Any], context: str, repo_root: Path) -> None:
    source_ids = {source["source_id"] for source in snapshot["evidence_sources"]}
    for index, source in enumerate(snapshot["evidence_sources"]):
        source_context = f"{context}.evidence_sources[{index}]"
        source_path = require_existing_repo_path(source["path"], f"{source_context}.path", repo_root)
        validate_hash(source_path, source["sha256"], f"{source_context}.sha256", repo_root)
        if source["entry_count"] != source["eligible_entry_count"] + source["excluded_entry_count"]:
            raise LocalBenchmarkReportValidationError(f"{source_context} entry counts must balance")

    for index, item in enumerate(snapshot["excluded_evidence"]):
        item_context = f"{context}.excluded_evidence[{index}]"
        if item["source_id"] not in source_ids:
            raise LocalBenchmarkReportValidationError(f"{item_context}.source_id must reference evidence_sources")
        if item["evidence_class"] == "private_audit":
            raise LocalBenchmarkReportValidationError(f"{item_context}.evidence_class private_audit cannot appear in public report")
        if not item["exclusion_reasons"]:
            raise LocalBenchmarkReportValidationError(f"{item_context}.exclusion_reasons must explain exclusion")


def validate_status_and_rankings(snapshot: dict[str, Any], context: str) -> None:
    eligibility = snapshot["eligibility_summary"]
    rankings = snapshot["rankings"]
    if snapshot["report_status"] == "no_rankings_published":
        if snapshot["ranking_claim_allowed"] is not False:
            raise LocalBenchmarkReportValidationError(f"{context}.ranking_claim_allowed must be false without rankings")
        if rankings:
            raise LocalBenchmarkReportValidationError(f"{context}.rankings must be empty when no rankings are published")
        if eligibility["acceptance_criteria_met"] is not False:
            raise LocalBenchmarkReportValidationError(f"{context}.eligibility_summary.acceptance_criteria_met must be false")
        if not eligibility["ranking_publication_blocked_reason"].strip():
            raise LocalBenchmarkReportValidationError(
                f"{context}.eligibility_summary.ranking_publication_blocked_reason must explain the block"
            )
        return

    if snapshot["report_status"] == "published_local_ranking":
        if snapshot["ranking_claim_allowed"] is not True:
            raise LocalBenchmarkReportValidationError(f"{context}.ranking_claim_allowed must be true for published rankings")
        if len(rankings) < eligibility["minimum_real_local_targets_required"]:
            raise LocalBenchmarkReportValidationError(f"{context}.rankings must include enough eligible local targets")
        if eligibility["acceptance_criteria_met"] is not True:
            raise LocalBenchmarkReportValidationError(f"{context}.eligibility_summary.acceptance_criteria_met must be true")
        expected_ranks = list(range(1, len(rankings) + 1))
        observed_ranks = [ranking["rank"] for ranking in rankings]
        if observed_ranks != expected_ranks:
            raise LocalBenchmarkReportValidationError(f"{context}.rankings ranks must be contiguous")
        for index, ranking in enumerate(rankings):
            if ranking["unresolved_review_count"] != 0:
                raise LocalBenchmarkReportValidationError(f"{context}.rankings[{index}].unresolved_review_count must be zero")


def validate_safety_assertions(value: dict[str, Any], context: str) -> None:
    for field_name, expected_value in EXPECTED_SAFE_ASSERTIONS.items():
        if value.get(field_name) is not expected_value:
            raise LocalBenchmarkReportValidationError(f"{context}.{field_name} must equal {expected_value!r}")


def validate_source_paths(source_paths: list[str], context: str, repo_root: Path) -> None:
    for index, source_path in enumerate(source_paths):
        require_existing_repo_path(source_path, f"{context}[{index}]", repo_root)


def validate_hash(path: Path, expected_hash: str, context: str, repo_root: Path) -> None:
    if sha256_file(path) != expected_hash:
        raise LocalBenchmarkReportValidationError(
            f"{context} must match sha256 of {display_path(path, repo_root)}"
        )


def require_existing_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    if isinstance(value, Path):
        path = value
    elif isinstance(value, str) and value.strip():
        path = Path(value)
    else:
        raise LocalBenchmarkReportValidationError(f"{context} must be a non-empty path")
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise LocalBenchmarkReportValidationError(f"{context} must stay within the repository") from exc
    if not resolved.exists():
        raise LocalBenchmarkReportValidationError(f"{context} does not exist: {display_path(resolved, repo_root)}")
    return resolved


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the M60 local/open-weight benchmark report.")
    parser.add_argument("snapshot", nargs="?", type=Path, default=DEFAULT_SNAPSHOT_PATH)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = validate_local_benchmark_report(args.snapshot, args.schema, args.report)
    except (LocalBenchmarkReportValidationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"local benchmark snapshot path: {summary['snapshot_path']}")
    print(f"local benchmark schema: {summary['schema_path']}")
    print(f"local benchmark report path: {summary['report_path']}")
    print(f"snapshot id: {summary['snapshot_id']}")
    print(f"report status: {summary['report_status']}")
    print(f"ranking claim allowed: {str(summary['ranking_claim_allowed']).lower()}")
    print(f"rankings: {summary['rankings']}")
    print(f"excluded evidence: {summary['excluded_evidence']}")
    print("local benchmark report validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
