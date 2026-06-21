"""Validate the benchmark claim charter.

This M54 validator checks evidence-class and claim-boundary metadata for the
local-first benchmark path. It does not run providers, local models, agents,
networks, tools, or external actions.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from schema_validation_utils import display_path, load_json_object, validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHARTER_PATH = REPO_ROOT / "benchmarks/evidence_class_charter.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/benchmark_claim_charter.schema.json"

EXPECTED_EVIDENCE_CLASS_IDS = {
    "evaluator_health",
    "local_public_benchmark",
    "manual_public_sample",
    "cloud_public_benchmark",
    "private_audit",
    "promoted_public_evidence",
    "unsupported_claim",
}
PUBLIC_RANKING_CLASSES = {
    "local_public_benchmark",
    "cloud_public_benchmark",
}


class BenchmarkClaimCharterValidationError(Exception):
    """Benchmark claim charter validation error."""


def validate_charter(
    charter_path: Path = DEFAULT_CHARTER_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the benchmark claim charter and return a deterministic summary."""

    schema = load_json_object(schema_path, "schema", repo_root, BenchmarkClaimCharterValidationError)
    charter = load_json_object(charter_path, "benchmark claim charter", repo_root, BenchmarkClaimCharterValidationError)
    context = display_path(charter_path, repo_root)

    validate_schema_value(charter, schema, context, charter_path, repo_root, BenchmarkClaimCharterValidationError)
    evidence_classes = charter["evidence_classes"]
    validate_evidence_classes(evidence_classes, context)
    validate_ranking_rules(charter["ranking_rules"], evidence_classes, context)
    validate_source_paths(charter["source_paths"], context, repo_root)
    validate_safety_assertions(charter["safety_assertions"], context)

    ranking_eligible = [
        item
        for item in evidence_classes
        if item["public_ranking_eligible"] is True
    ]
    return {
        "charter_path": context,
        "schema_path": display_path(schema_path, repo_root),
        "charter_id": str(charter["charter_id"]),
        "evidence_class_count": len(evidence_classes),
        "public_ranking_eligible_classes": sorted(
            str(item["evidence_class_id"])
            for item in ranking_eligible
        ),
        "private_data_allowed_classes": sorted(
            str(item["evidence_class_id"])
            for item in evidence_classes
            if item["private_data_allowed"] is True
        ),
        "credentials_required_allowed_classes": sorted(
            str(item["evidence_class_id"])
            for item in evidence_classes
            if item["credentials_required_allowed"] is True
        ),
    }


def validate_evidence_classes(evidence_classes: list[dict[str, Any]], context: str) -> None:
    """Validate evidence class policy relationships."""

    observed_ids = [str(item["evidence_class_id"]) for item in evidence_classes]
    duplicate_ids = sorted({item for item in observed_ids if observed_ids.count(item) > 1})
    if duplicate_ids:
        raise BenchmarkClaimCharterValidationError(
            f"{context}.evidence_classes duplicate evidence_class_id values: {', '.join(duplicate_ids)}"
        )
    missing_ids = sorted(EXPECTED_EVIDENCE_CLASS_IDS - set(observed_ids))
    unexpected_ids = sorted(set(observed_ids) - EXPECTED_EVIDENCE_CLASS_IDS)
    if missing_ids:
        raise BenchmarkClaimCharterValidationError(
            f"{context}.evidence_classes missing required classes: {', '.join(missing_ids)}"
        )
    if unexpected_ids:
        raise BenchmarkClaimCharterValidationError(
            f"{context}.evidence_classes unexpected classes: {', '.join(unexpected_ids)}"
        )

    by_id = {str(item["evidence_class_id"]): item for item in evidence_classes}
    for evidence_class_id, evidence_class in by_id.items():
        class_context = f"{context}.evidence_classes[{evidence_class_id}]"
        if evidence_class["public_ranking_eligible"] is True:
            if evidence_class_id not in PUBLIC_RANKING_CLASSES:
                raise BenchmarkClaimCharterValidationError(
                    f"{class_context}.public_ranking_eligible is only allowed for public benchmark classes"
                )
            if evidence_class["private_data_allowed"] is True:
                raise BenchmarkClaimCharterValidationError(
                    f"{class_context}.private_data_allowed must be false for ranking-eligible classes"
                )
            if evidence_class["committed_fixture_allowed"] is not True:
                raise BenchmarkClaimCharterValidationError(
                    f"{class_context}.committed_fixture_allowed must be true for ranking-eligible classes"
                )
        if evidence_class_id == "private_audit":
            if evidence_class["committed_fixture_allowed"] is not False:
                raise BenchmarkClaimCharterValidationError(
                    f"{class_context}.committed_fixture_allowed must be false"
                )
            if evidence_class["private_data_allowed"] is not True:
                raise BenchmarkClaimCharterValidationError(f"{class_context}.private_data_allowed must be true")
            if evidence_class["public_ranking_eligible"] is not False:
                raise BenchmarkClaimCharterValidationError(
                    f"{class_context}.public_ranking_eligible must be false"
                )
        if evidence_class_id == "local_public_benchmark":
            if evidence_class["credentials_required_allowed"] is not False:
                raise BenchmarkClaimCharterValidationError(
                    f"{class_context}.credentials_required_allowed must be false"
                )
        if evidence_class_id == "cloud_public_benchmark":
            if evidence_class["credentials_required_allowed"] is not True:
                raise BenchmarkClaimCharterValidationError(
                    f"{class_context}.credentials_required_allowed must be true"
                )
        if evidence_class_id == "manual_public_sample":
            if evidence_class["public_ranking_eligible"] is not False:
                raise BenchmarkClaimCharterValidationError(
                    f"{class_context}.public_ranking_eligible must be false"
                )


def validate_ranking_rules(
    ranking_rules: dict[str, Any],
    evidence_classes: list[dict[str, Any]],
    context: str,
) -> None:
    """Validate ranking rules are consistent with evidence class flags."""

    if ranking_rules["manual_samples_excluded_from_rankings_by_default"] is not True:
        raise BenchmarkClaimCharterValidationError(
            f"{context}.ranking_rules.manual_samples_excluded_from_rankings_by_default must be true"
        )
    ranking_classes = {
        str(item["evidence_class_id"])
        for item in evidence_classes
        if item["public_ranking_eligible"] is True
    }
    if ranking_classes != PUBLIC_RANKING_CLASSES:
        raise BenchmarkClaimCharterValidationError(
            f"{context}.ranking_rules public ranking classes must be: {', '.join(sorted(PUBLIC_RANKING_CLASSES))}"
        )


def validate_source_paths(source_paths: list[str], context: str, repo_root: Path) -> None:
    """Require every source path to be repository-relative and present."""

    for index, value in enumerate(source_paths):
        path = Path(value)
        if path.is_absolute():
            raise BenchmarkClaimCharterValidationError(f"{context}.source_paths[{index}] must be repository-relative")
        resolved = (repo_root / path).resolve()
        try:
            resolved.relative_to(repo_root.resolve())
        except ValueError as exc:
            raise BenchmarkClaimCharterValidationError(
                f"{context}.source_paths[{index}] must stay within the repository"
            ) from exc
        if not resolved.exists():
            raise BenchmarkClaimCharterValidationError(
                f"{context}.source_paths[{index}] does not exist: {display_path(resolved, repo_root)}"
            )


def validate_safety_assertions(value: dict[str, Any], context: str) -> None:
    """Require the committed charter itself to stay public-safe and non-live."""

    expected = {
        "public_safe": True,
        "live_execution": False,
        "external_actions": False,
        "contains_private_data": False,
        "credentials_required": False,
    }
    for field_name, expected_value in expected.items():
        if value[field_name] is not expected_value:
            raise BenchmarkClaimCharterValidationError(
                f"{context}.safety_assertions.{field_name} must equal {expected_value!r}"
            )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate benchmark claim charter.")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DEFAULT_CHARTER_PATH,
        help="Benchmark claim charter JSON path.",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA_PATH,
        help="Benchmark claim charter JSON Schema path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        summary = validate_charter(args.path, args.schema)
    except (BenchmarkClaimCharterValidationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"benchmark claim charter path: {summary['charter_path']}")
    print(f"benchmark claim charter schema: {summary['schema_path']}")
    print(f"charter id: {summary['charter_id']}")
    print(f"evidence classes: {summary['evidence_class_count']}")
    print(f"public ranking eligible classes: {', '.join(summary['public_ranking_eligible_classes'])}")
    print("benchmark claim charter validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
