"""Validate public-safe human adjudication records.

Adjudications are reviewer labels over existing scored traces. They do not
change scored traces automatically, call models, execute agents, or perform
external actions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from schema_validation_utils import load_json_object, validate_schema_value
from validate_schemas import ValidationError, validate_trace_record


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = REPO_ROOT / "traces/external/adjudications.example.jsonl"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/adjudication.schema.json"


class AdjudicationValidationError(Exception):
    """Adjudication validation error with public-safe context."""


def load_adjudications(path: Path) -> list[dict[str, Any]]:
    """Load and validate adjudication records."""

    if not path.exists():
        raise AdjudicationValidationError(f"{display_path(path)}: file does not exist")

    records = []
    trace_cache: dict[Path, list[dict[str, Any]]] = {}
    seen_ids: set[str] = set()
    schema = load_json_object(DEFAULT_SCHEMA_PATH, "schema", REPO_ROOT, AdjudicationValidationError)
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
            validate_adjudication_record(record, path, line_number, seen_ids, trace_cache, schema)
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
    schema: dict[str, Any] | None = None,
) -> None:
    """Validate one adjudication record."""

    context = f"{display_path(path)}:{line_number}"
    schema = schema if schema is not None else load_json_object(
        DEFAULT_SCHEMA_PATH,
        "schema",
        REPO_ROOT,
        AdjudicationValidationError,
    )
    validate_schema_value(record, schema, "", path, REPO_ROOT, validation_error_for_line(path, line_number))

    adjudication_id = str(record["adjudication_id"])
    if adjudication_id in seen_ids:
        raise AdjudicationValidationError(f"{context}.adjudication_id duplicate value: {adjudication_id}")
    seen_ids.add(adjudication_id)

    if record["public_safe"] is not True:
        raise AdjudicationValidationError(f"{context}.public_safe must be true for committed adjudications")

    source_trace_path = require_existing_repo_path(record["source_trace_path"], f"{context}.source_trace_path")
    source_records = trace_cache.setdefault(source_trace_path, load_trace_records(source_trace_path))
    source_record = find_source_record(record, source_records, context)
    original_failure_modes = [str(mode) for mode in record["original_failure_modes"]]
    adjudicated_failure_modes = [str(mode) for mode in record["adjudicated_failure_modes"]]
    validate_original_fields(record, original_failure_modes, source_record, context)
    validate_decision_consistency(
        str(record["reviewer_decision"]),
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

    source_failure_modes = [str(mode) for mode in source_record.get("failure_modes", [])]
    historical_context = record.get("historical_scorer_context")
    if historical_context is not None:
        validate_historical_scorer_context(
            record,
            historical_context,
            original_failure_modes,
            source_record,
            source_failure_modes,
            context,
        )
        return

    validate_original_fields_match_source(record, original_failure_modes, source_record, source_failure_modes, context)


def validate_original_fields_match_source(
    record: dict[str, Any],
    original_failure_modes: list[str],
    source_record: dict[str, Any],
    source_failure_modes: list[str],
    context: str,
) -> None:
    """Validate legacy adjudications whose original fields refer to current source traces."""

    if record["original_passed"] is not source_record.get("passed"):
        raise AdjudicationValidationError(f"{context}.original_passed does not match source trace")
    if float(record["original_score"]) != float(source_record.get("score", -1)):
        raise AdjudicationValidationError(f"{context}.original_score does not match source trace")
    if original_failure_modes != source_failure_modes:
        raise AdjudicationValidationError(f"{context}.original_failure_modes does not match source trace")


def validate_historical_scorer_context(
    record: dict[str, Any],
    historical_context: Any,
    original_failure_modes: list[str],
    source_record: dict[str, Any],
    source_failure_modes: list[str],
    context: str,
) -> None:
    """Validate explicit pre-change scorer context for changed source traces."""

    if not isinstance(historical_context, dict):
        raise AdjudicationValidationError(f"{context}.historical_scorer_context must be an object")

    require_existing_repo_path(
        historical_context["original_scorer_artifact"],
        f"{context}.historical_scorer_context.original_scorer_artifact",
    )

    if historical_context["current_trace_passed"] is not source_record.get("passed"):
        raise AdjudicationValidationError(
            f"{context}.historical_scorer_context.current_trace_passed does not match source trace"
        )
    if float(historical_context["current_trace_score"]) != float(source_record.get("score", -1)):
        raise AdjudicationValidationError(
            f"{context}.historical_scorer_context.current_trace_score does not match source trace"
        )

    current_trace_failure_modes = [str(mode) for mode in historical_context["current_trace_failure_modes"]]
    if current_trace_failure_modes != source_failure_modes:
        raise AdjudicationValidationError(
            f"{context}.historical_scorer_context.current_trace_failure_modes does not match source trace"
        )

    original_matches_current_trace = (
        record["original_passed"] is source_record.get("passed")
        and float(record["original_score"]) == float(source_record.get("score", -1))
        and original_failure_modes == source_failure_modes
    )
    if original_matches_current_trace:
        raise AdjudicationValidationError(
            f"{context}.historical_scorer_context requires original fields to differ from source trace"
        )


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


def validation_error_for_line(path: Path, line_number: int) -> Callable[[str], AdjudicationValidationError]:
    """Build line-aware adjudication validation errors for shared schema checks."""

    def build_error(reason: str) -> AdjudicationValidationError:
        return AdjudicationValidationError(f"{display_path(path)}:{line_number}: {reason}")

    return build_error


def require_non_empty_string(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise AdjudicationValidationError(f"{context} must be a string")
    if not value.strip():
        raise AdjudicationValidationError(f"{context} must not be empty")
    return value


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
