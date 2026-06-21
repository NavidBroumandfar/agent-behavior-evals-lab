"""Validate the M55 public local benchmark corpus.

The validator reads local committed case and manifest artifacts only. It does
not call providers, local models, Ollama, agents, networks, tools, or external
actions.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from local_benchmark_corpus import (
    CASE_SET_ID,
    CASE_SET_VERSION,
    CATEGORY_BY_RISK_AREA,
    DEFAULT_MANIFEST_PATH,
    DIFFICULTIES,
    EXPECTED_BEHAVIOR_BY_RISK_AREA,
    FAILURE_MODES_BY_RISK_AREA,
    PREFIX_BY_RISK_AREA,
    POLICY_REFS_BY_RISK_AREA,
    RISK_AREAS,
    SCORING_NOTES_BY_RISK_AREA,
    SEVERITY_BY_RISK_AREA,
    SPLITS,
    benchmark_splits_for_sequence,
    difficulty_for_sequence,
    sha256_text,
)
from schema_validation_utils import display_path, load_json_object, validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_SCHEMA_PATH = REPO_ROOT / "schemas/local_benchmark_manifest.schema.json"
DEFAULT_CASE_SCHEMA_PATH = REPO_ROOT / "schemas/local_benchmark_case.schema.json"
EXPECTED_CASES_PER_RISK_AREA = 30
EXPECTED_CASE_COUNT = EXPECTED_CASES_PER_RISK_AREA * len(RISK_AREAS)
EXPECTED_SPLIT_COUNTS = {
    "smoke": 3 * len(RISK_AREAS),
    "standard": 10 * len(RISK_AREAS),
    "extended": EXPECTED_CASE_COUNT,
}
EXPECTED_SAFE_ASSERTIONS = {
    "public_safe": True,
    "live_execution": False,
    "external_actions": False,
    "contains_private_data": False,
    "credentials_required": False,
}


class LocalBenchmarkCorpusValidationError(Exception):
    """Local benchmark corpus validation error."""


def validate_corpus(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    manifest_schema_path: Path = DEFAULT_MANIFEST_SCHEMA_PATH,
    case_schema_path: Path = DEFAULT_CASE_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the local benchmark corpus and return a deterministic summary."""

    manifest_schema = load_json_object(
        manifest_schema_path,
        "manifest schema",
        repo_root,
        LocalBenchmarkCorpusValidationError,
    )
    case_schema = load_json_object(
        case_schema_path,
        "case schema",
        repo_root,
        LocalBenchmarkCorpusValidationError,
    )
    manifest = load_json_object(manifest_path, "manifest", repo_root, LocalBenchmarkCorpusValidationError)
    manifest_context = display_path(manifest_path, repo_root)

    validate_schema_value(
        manifest,
        manifest_schema,
        manifest_context,
        manifest_path,
        repo_root,
        LocalBenchmarkCorpusValidationError,
    )
    case_path = resolve_repo_relative_path(manifest["case_path"], f"{manifest_context}.case_path", repo_root)
    case_text = case_path.read_text(encoding="utf-8")
    if sha256_text(case_text) != manifest["case_file_sha256"]:
        raise LocalBenchmarkCorpusValidationError(f"{manifest_context}.case_file_sha256 does not match case file")

    cases = load_and_validate_cases(case_path, case_schema, repo_root)
    validate_cases(cases, display_path(case_path, repo_root))
    validate_manifest_consistency(manifest, cases, manifest_context)
    validate_source_paths(manifest["source_paths"], manifest_context, repo_root)
    validate_safety_assertions(manifest["safety_assertions"], manifest_context)

    risk_counts = counts_by(cases, "risk_area")
    split_counts = split_counts_for_cases(cases)
    return {
        "manifest_path": manifest_context,
        "case_path": display_path(case_path, repo_root),
        "manifest_schema_path": display_path(manifest_schema_path, repo_root),
        "case_schema_path": display_path(case_schema_path, repo_root),
        "case_set_id": str(manifest["case_set_id"]),
        "version": str(manifest["version"]),
        "case_count": len(cases),
        "risk_area_counts": risk_counts,
        "split_counts": split_counts,
    }


def load_and_validate_cases(
    case_path: Path,
    case_schema: dict[str, Any],
    repo_root: Path,
) -> list[dict[str, Any]]:
    """Load and schema-validate JSONL case records."""

    cases: list[dict[str, Any]] = []
    with case_path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise LocalBenchmarkCorpusValidationError(
                    f"{display_path(case_path, repo_root)}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc
            validate_schema_value(
                record,
                case_schema,
                f"{display_path(case_path, repo_root)}:{line_number}",
                case_path,
                repo_root,
                LocalBenchmarkCorpusValidationError,
            )
            cases.append(record)
    return cases


def validate_cases(cases: list[dict[str, Any]], context: str) -> None:
    """Validate deterministic M55 corpus semantics."""

    if len(cases) != EXPECTED_CASE_COUNT:
        raise LocalBenchmarkCorpusValidationError(
            f"{context} must contain {EXPECTED_CASE_COUNT} cases, found {len(cases)}"
        )
    if len(cases) < 200:
        raise LocalBenchmarkCorpusValidationError(f"{context} must contain at least 200 cases")

    case_ids = [str(case["case_id"]) for case in cases]
    duplicate_ids = sorted({case_id for case_id in case_ids if case_ids.count(case_id) > 1})
    if duplicate_ids:
        raise LocalBenchmarkCorpusValidationError(f"{context} duplicate case_id values: {', '.join(duplicate_ids)}")

    by_risk_sequence: dict[str, list[int]] = defaultdict(list)
    for case in cases:
        risk_area = str(case["risk_area"])
        sequence = int(case["sequence"])
        case_context = f"{context}.{case['case_id']}"
        by_risk_sequence[risk_area].append(sequence)
        validate_case_semantics(case, case_context)

    risk_counts = counts_by(cases, "risk_area")
    expected_risk_counts = {risk_area: EXPECTED_CASES_PER_RISK_AREA for risk_area in RISK_AREAS}
    if risk_counts != expected_risk_counts:
        raise LocalBenchmarkCorpusValidationError(
            f"{context} risk-area counts must equal {expected_risk_counts}, found {risk_counts}"
        )

    for risk_area in RISK_AREAS:
        observed_sequences = sorted(by_risk_sequence[risk_area])
        expected_sequences = list(range(1, EXPECTED_CASES_PER_RISK_AREA + 1))
        if observed_sequences != expected_sequences:
            raise LocalBenchmarkCorpusValidationError(
                f"{context}.{risk_area} sequences must be {expected_sequences}, found {observed_sequences}"
            )

    split_counts = split_counts_for_cases(cases)
    if split_counts != EXPECTED_SPLIT_COUNTS:
        raise LocalBenchmarkCorpusValidationError(
            f"{context} split counts must equal {EXPECTED_SPLIT_COUNTS}, found {split_counts}"
        )


def validate_case_semantics(case: dict[str, Any], context: str) -> None:
    risk_area = str(case["risk_area"])
    sequence = int(case["sequence"])
    expected_case_id = f"LPB-{PREFIX_BY_RISK_AREA[risk_area]}-{sequence:03d}"
    if case["case_id"] != expected_case_id:
        raise LocalBenchmarkCorpusValidationError(f"{context}.case_id must equal {expected_case_id}")
    if case["case_set_id"] != CASE_SET_ID:
        raise LocalBenchmarkCorpusValidationError(f"{context}.case_set_id must equal {CASE_SET_ID}")
    if case["case_set_version"] != CASE_SET_VERSION:
        raise LocalBenchmarkCorpusValidationError(f"{context}.case_set_version must equal {CASE_SET_VERSION}")
    if case["category"] != CATEGORY_BY_RISK_AREA[risk_area]:
        raise LocalBenchmarkCorpusValidationError(
            f"{context}.category must equal {CATEGORY_BY_RISK_AREA[risk_area]}"
        )
    if case["difficulty"] != difficulty_for_sequence(sequence):
        raise LocalBenchmarkCorpusValidationError(
            f"{context}.difficulty must equal {difficulty_for_sequence(sequence)}"
        )
    if case["benchmark_splits"] != benchmark_splits_for_sequence(sequence):
        raise LocalBenchmarkCorpusValidationError(
            f"{context}.benchmark_splits must equal {benchmark_splits_for_sequence(sequence)}"
        )
    if case["policy_refs"] != POLICY_REFS_BY_RISK_AREA[risk_area]:
        raise LocalBenchmarkCorpusValidationError(f"{context}.policy_refs do not match risk-area policy refs")
    if case["expected_failure_modes"] != FAILURE_MODES_BY_RISK_AREA[risk_area]:
        raise LocalBenchmarkCorpusValidationError(
            f"{context}.expected_failure_modes do not match risk-area failure modes"
        )
    if case["severity"] != SEVERITY_BY_RISK_AREA[risk_area]:
        raise LocalBenchmarkCorpusValidationError(f"{context}.severity must equal {SEVERITY_BY_RISK_AREA[risk_area]}")
    if case["expected_behavior"] != EXPECTED_BEHAVIOR_BY_RISK_AREA[risk_area]:
        raise LocalBenchmarkCorpusValidationError(f"{context}.expected_behavior does not match risk-area guidance")
    if case["scoring_notes"] != SCORING_NOTES_BY_RISK_AREA[risk_area]:
        raise LocalBenchmarkCorpusValidationError(f"{context}.scoring_notes do not match risk-area guidance")


def validate_manifest_consistency(manifest: dict[str, Any], cases: list[dict[str, Any]], context: str) -> None:
    """Validate manifest counts mirror the case file."""

    if manifest["case_count"] != len(cases):
        raise LocalBenchmarkCorpusValidationError(f"{context}.case_count must equal {len(cases)}")
    if manifest["coverage"]["by_category"] != counts_by(cases, "category"):
        raise LocalBenchmarkCorpusValidationError(f"{context}.coverage.by_category does not match cases")
    if manifest["coverage"]["by_risk_area"] != counts_by(cases, "risk_area"):
        raise LocalBenchmarkCorpusValidationError(f"{context}.coverage.by_risk_area does not match cases")
    if manifest["coverage"]["by_difficulty"] != counts_by(cases, "difficulty"):
        raise LocalBenchmarkCorpusValidationError(f"{context}.coverage.by_difficulty does not match cases")

    observed_split_counts = split_counts_for_cases(cases)
    for split in SPLITS:
        if manifest["splits"][split]["case_count"] != observed_split_counts[split]:
            raise LocalBenchmarkCorpusValidationError(
                f"{context}.splits.{split}.case_count must equal {observed_split_counts[split]}"
            )


def validate_source_paths(source_paths: list[str], context: str, repo_root: Path) -> None:
    for index, value in enumerate(source_paths):
        resolve_repo_relative_path(value, f"{context}.source_paths[{index}]", repo_root)


def validate_safety_assertions(value: dict[str, Any], context: str) -> None:
    for field_name, expected_value in EXPECTED_SAFE_ASSERTIONS.items():
        if value[field_name] is not expected_value:
            raise LocalBenchmarkCorpusValidationError(
                f"{context}.safety_assertions.{field_name} must equal {expected_value!r}"
            )


def resolve_repo_relative_path(value: Any, context: str, repo_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise LocalBenchmarkCorpusValidationError(f"{context} must be a non-empty string")
    path = Path(value)
    if path.is_absolute():
        raise LocalBenchmarkCorpusValidationError(f"{context} must be repository-relative")
    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise LocalBenchmarkCorpusValidationError(f"{context} must stay within the repository") from exc
    if not resolved.exists():
        raise LocalBenchmarkCorpusValidationError(f"{context} does not exist: {display_path(resolved, repo_root)}")
    return resolved


def counts_by(cases: list[dict[str, Any]], field_name: str) -> dict[str, int]:
    return dict(sorted(Counter(str(case[field_name]) for case in cases).items()))


def split_counts_for_cases(cases: list[dict[str, Any]]) -> dict[str, int]:
    return {
        split: sum(1 for case in cases if split in case["benchmark_splits"])
        for split in SPLITS
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the M55 public local benchmark corpus.")
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--manifest-schema", type=Path, default=DEFAULT_MANIFEST_SCHEMA_PATH)
    parser.add_argument("--case-schema", type=Path, default=DEFAULT_CASE_SCHEMA_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = validate_corpus(args.manifest, args.manifest_schema, args.case_schema)
    except (LocalBenchmarkCorpusValidationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"local benchmark corpus manifest path: {summary['manifest_path']}")
    print(f"local benchmark corpus case path: {summary['case_path']}")
    print(f"case set id: {summary['case_set_id']}")
    print(f"version: {summary['version']}")
    print(f"cases validated: {summary['case_count']}")
    print(f"risk areas: {len(summary['risk_area_counts'])}")
    print(f"smoke cases: {summary['split_counts']['smoke']}")
    print(f"standard cases: {summary['split_counts']['standard']}")
    print(f"extended cases: {summary['split_counts']['extended']}")
    print("local benchmark corpus validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
