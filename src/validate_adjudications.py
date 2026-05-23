"""Validate public-safe human adjudication records.

Adjudications are reviewer labels over existing scored traces. They do not
change scored traces automatically, call models, execute agents, or perform
external actions.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from validate_schemas import ValidationError, validate_trace_record


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = REPO_ROOT / "traces/external/adjudications.example.jsonl"

REQUIRED_FIELDS = {
    "adjudication_id",
    "source_trace_path",
    "run_id",
    "case_id",
    "profile_name",
    "reviewed_at",
    "reviewer_id",
    "reviewer_decision",
    "original_passed",
    "original_score",
    "original_failure_modes",
    "adjudicated_passed",
    "adjudicated_failure_modes",
    "rationale",
    "public_safe",
}
ALLOWED_REVIEWER_DECISIONS = {
    "uphold_score",
    "override_pass",
    "override_fail",
    "needs_discussion",
}
UTC_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class AdjudicationValidationError(Exception):
    """Adjudication validation error with public-safe context."""


def load_adjudications(path: Path) -> list[dict[str, Any]]:
    """Load and validate adjudication records."""

    if not path.exists():
        raise AdjudicationValidationError(f"{display_path(path)}: file does not exist")

    records = []
    trace_cache: dict[Path, list[dict[str, Any]]] = {}
    seen_ids: set[str] = set()
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise AdjudicationValidationError(
                    f"{display_path(path)}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc
            validate_adjudication_record(record, path, line_number, seen_ids, trace_cache)
            records.append(record)

    if not records:
        raise AdjudicationValidationError(f"{display_path(path)}: file contains no adjudication records")
    return records


def validate_adjudication_file(path: Path = DEFAULT_INPUT_PATH) -> int:
    """Validate one adjudication JSONL file and return the record count."""

    return len(load_adjudications(path))


def validate_adjudication_record(
    record: Any,
    path: Path,
    line_number: int,
    seen_ids: set[str],
    trace_cache: dict[Path, list[dict[str, Any]]],
) -> None:
    """Validate one adjudication record."""

    context = f"{display_path(path)}:{line_number}"
    if not isinstance(record, dict):
        raise AdjudicationValidationError(f"{context}: record must be a JSON object")

    missing_fields = sorted(REQUIRED_FIELDS - set(record))
    if missing_fields:
        raise AdjudicationValidationError(f"{context}: missing required fields: {', '.join(missing_fields)}")

    unexpected_fields = sorted(set(record) - REQUIRED_FIELDS)
    if unexpected_fields:
        raise AdjudicationValidationError(f"{context}: unexpected fields: {', '.join(unexpected_fields)}")

    adjudication_id = require_non_empty_string(record["adjudication_id"], f"{context}.adjudication_id")
    if adjudication_id in seen_ids:
        raise AdjudicationValidationError(f"{context}.adjudication_id duplicate value: {adjudication_id}")
    seen_ids.add(adjudication_id)

    for field_name in ["run_id", "case_id", "profile_name", "reviewer_id", "rationale"]:
        require_non_empty_string(record[field_name], f"{context}.{field_name}")
    validate_utc_timestamp(record["reviewed_at"], f"{context}.reviewed_at")

    reviewer_decision = require_enum(
        record["reviewer_decision"],
        ALLOWED_REVIEWER_DECISIONS,
        f"{context}.reviewer_decision",
    )
    require_bool(record["original_passed"], f"{context}.original_passed")
    require_number_between_zero_and_one(record["original_score"], f"{context}.original_score")
    original_failure_modes = require_string_list(
        record["original_failure_modes"],
        f"{context}.original_failure_modes",
        allow_empty=True,
    )
    require_bool(record["adjudicated_passed"], f"{context}.adjudicated_passed")
    adjudicated_failure_modes = require_string_list(
        record["adjudicated_failure_modes"],
        f"{context}.adjudicated_failure_modes",
        allow_empty=True,
    )
    require_bool(record["public_safe"], f"{context}.public_safe")
    if record["public_safe"] is not True:
        raise AdjudicationValidationError(f"{context}.public_safe must be true for committed adjudications")

    source_trace_path = require_existing_repo_path(record["source_trace_path"], f"{context}.source_trace_path")
    source_records = trace_cache.setdefault(source_trace_path, load_trace_records(source_trace_path))
    source_record = find_source_record(record, source_records, context)
    validate_original_fields(record, original_failure_modes, source_record, context)
    validate_decision_consistency(
        reviewer_decision,
        bool(record["original_passed"]),
        original_failure_modes,
        bool(record["adjudicated_passed"]),
        adjudicated_failure_modes,
        context,
    )


def load_trace_records(path: Path) -> list[dict[str, Any]]:
    """Load and validate source scored trace records."""

    records = []
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise AdjudicationValidationError(
                    f"{display_path(path)}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc
            try:
                validate_trace_record(record, str(path), line_number)
            except ValidationError as exc:
                raise AdjudicationValidationError(str(exc)) from exc
            records.append(record)

    if not records:
        raise AdjudicationValidationError(f"{display_path(path)}: source trace has no records")
    return records


def find_source_record(record: dict[str, Any], source_records: list[dict[str, Any]], context: str) -> dict[str, Any]:
    """Find the adjudicated scored trace record."""

    matches = [
        source_record
        for source_record in source_records
        if source_record.get("run_id") == record["run_id"]
        and source_record.get("case_id") == record["case_id"]
        and source_record.get("profile_name") == record["profile_name"]
    ]
    if len(matches) != 1:
        raise AdjudicationValidationError(
            f"{context}: expected exactly one matching source trace record, found {len(matches)}"
        )
    return matches[0]


def validate_original_fields(
    record: dict[str, Any],
    original_failure_modes: list[str],
    source_record: dict[str, Any],
    context: str,
) -> None:
    """Validate that original fields match the source trace."""

    if record["original_passed"] is not source_record.get("passed"):
        raise AdjudicationValidationError(f"{context}.original_passed does not match source trace")
    if float(record["original_score"]) != float(source_record.get("score", -1)):
        raise AdjudicationValidationError(f"{context}.original_score does not match source trace")

    source_failure_modes = [str(mode) for mode in source_record.get("failure_modes", [])]
    if original_failure_modes != source_failure_modes:
        raise AdjudicationValidationError(f"{context}.original_failure_modes does not match source trace")


def validate_decision_consistency(
    reviewer_decision: str,
    original_passed: bool,
    original_failure_modes: list[str],
    adjudicated_passed: bool,
    adjudicated_failure_modes: list[str],
    context: str,
) -> None:
    """Validate adjudicated result shape for each decision type."""

    if reviewer_decision in {"uphold_score", "needs_discussion"}:
        if adjudicated_passed is not original_passed:
            raise AdjudicationValidationError(f"{context}: {reviewer_decision} must preserve original_passed")
        if adjudicated_failure_modes != original_failure_modes:
            raise AdjudicationValidationError(f"{context}: {reviewer_decision} must preserve original_failure_modes")
        return

    if reviewer_decision == "override_pass":
        if adjudicated_passed is not True:
            raise AdjudicationValidationError(f"{context}: override_pass requires adjudicated_passed=true")
        if adjudicated_failure_modes:
            raise AdjudicationValidationError(f"{context}: override_pass requires no adjudicated failure modes")
        return

    if reviewer_decision == "override_fail":
        if adjudicated_passed is not False:
            raise AdjudicationValidationError(f"{context}: override_fail requires adjudicated_passed=false")
        if not adjudicated_failure_modes:
            raise AdjudicationValidationError(f"{context}: override_fail requires adjudicated failure modes")


def validate_utc_timestamp(value: Any, context: str) -> None:
    text = require_non_empty_string(value, context)
    if not UTC_TIMESTAMP_PATTERN.fullmatch(text):
        raise AdjudicationValidationError(f"{context} must use YYYY-MM-DDTHH:MM:SSZ UTC format")


def require_enum(value: Any, allowed_values: set[str], context: str) -> str:
    text = require_non_empty_string(value, context)
    if text not in allowed_values:
        allowed = ", ".join(sorted(allowed_values))
        raise AdjudicationValidationError(f"{context} must be one of: {allowed}")
    return text


def require_bool(value: Any, context: str) -> bool:
    if not isinstance(value, bool):
        raise AdjudicationValidationError(f"{context} must be a boolean")
    return value


def require_number_between_zero_and_one(value: Any, context: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise AdjudicationValidationError(f"{context} must be a number")
    if value < 0 or value > 1:
        raise AdjudicationValidationError(f"{context} must be between 0 and 1")
    return float(value)


def require_non_empty_string(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise AdjudicationValidationError(f"{context} must be a string")
    if not value.strip():
        raise AdjudicationValidationError(f"{context} must not be empty")
    return value


def require_string_list(value: Any, context: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list):
        raise AdjudicationValidationError(f"{context} must be an array")
    if not value and not allow_empty:
        raise AdjudicationValidationError(f"{context} must not be empty")

    result = []
    for index, item in enumerate(value):
        result.append(require_non_empty_string(item, f"{context}[{index}]"))
    return result


def require_existing_repo_path(value: Any, context: str) -> Path:
    raw_path = require_non_empty_string(value, context)
    path = Path(raw_path)
    if path.is_absolute():
        raise AdjudicationValidationError(f"{context} must be a repository-relative path")

    resolved = (REPO_ROOT / path).resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise AdjudicationValidationError(f"{context} must stay within the repository") from exc

    if not resolved.exists():
        raise AdjudicationValidationError(f"{context} does not exist: {display_path(resolved)}")
    return resolved


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate public-safe human adjudication records.")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_INPUT_PATH],
        help="Adjudication JSONL files to validate.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    total_count = 0
    try:
        for path in args.paths:
            total_count += validate_adjudication_file(path)
    except (AdjudicationValidationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"adjudication records validated: {total_count}")
    print("adjudication validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
