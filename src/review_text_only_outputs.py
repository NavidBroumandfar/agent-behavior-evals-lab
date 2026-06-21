"""Convert approved local raw text-only outputs into adapter-output JSONL.

This reviewer consumes local raw records after a human has marked them
`approved_public_safe`. It writes normalized adapter-output JSONL that can pass
the existing adapter-output validator. It does not collect live outputs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from trace_writer import write_jsonl
from validate_adapter_outputs import AdapterOutputValidationError, validate_jsonl_file


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_RAW_FIELDS = {
    "raw_record_id",
    "run_id",
    "case_id",
    "target_profile",
    "adapter_name",
    "adapter_version",
    "collected_at",
    "output_text",
    "review_status",
    "provenance",
    "review_required",
}
OPTIONAL_RAW_FIELDS = {
    "source_label",
    "notes",
    "metadata",
}
ALLOWED_RAW_FIELDS = REQUIRED_RAW_FIELDS | OPTIONAL_RAW_FIELDS
REQUIRED_RAW_PROVENANCE_FIELDS = {
    "public_safe",
    "live_execution",
    "external_actions",
    "contains_private_data",
    "credentials_required",
}


class TextOnlyOutputReviewError(Exception):
    """Text-only output review error."""


def review_text_only_outputs(input_path: Path, output_path: Path) -> dict[str, Any]:
    """Convert approved local raw records into normalized adapter-output records."""

    validate_reviewed_output_path(output_path)
    raw_records = load_raw_records(input_path)
    approved_records = [record for record in raw_records if record["review_status"] == "approved_public_safe"]
    if not approved_records:
        raise TextOnlyOutputReviewError(f"{display_path(input_path)}: no approved_public_safe records found")

    adapter_records = [adapter_output_from_raw(record) for record in approved_records]
    write_jsonl(adapter_records, output_path)

    allow_live_local = any(record["provenance"]["live_execution"] is True for record in adapter_records)
    try:
        validate_jsonl_file(output_path, allow_live_local=allow_live_local)
    except AdapterOutputValidationError as exc:
        raise TextOnlyOutputReviewError(f"reviewed adapter output failed validation: {exc}") from exc

    return {
        "input_path": display_path(input_path),
        "output_path": display_path(output_path),
        "raw_records_loaded": len(raw_records),
        "approved_records_written": len(adapter_records),
    }


def load_raw_records(path: Path) -> list[dict[str, Any]]:
    """Load and validate local raw text-only output records."""

    if not path.exists():
        raise TextOnlyOutputReviewError(f"{display_path(path)}: file does not exist")

    records = []
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise TextOnlyOutputReviewError(
                    f"{display_path(path)}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc
            validate_raw_record(record, path, line_number)
            records.append(record)

    if not records:
        raise TextOnlyOutputReviewError(f"{display_path(path)}: file contains no raw records")
    return records


def validate_raw_record(record: Any, path: Path, line_number: int) -> None:
    """Validate one raw text-only output record."""

    context = f"{display_path(path)}:{line_number}"
    if not isinstance(record, dict):
        raise TextOnlyOutputReviewError(f"{context}: record must be an object")

    missing_fields = sorted(REQUIRED_RAW_FIELDS - set(record))
    if missing_fields:
        raise TextOnlyOutputReviewError(f"{context}: missing required fields: {', '.join(missing_fields)}")

    unexpected_fields = sorted(set(record) - ALLOWED_RAW_FIELDS)
    if unexpected_fields:
        raise TextOnlyOutputReviewError(f"{context}: unexpected fields: {', '.join(unexpected_fields)}")

    for field_name in [
        "raw_record_id",
        "run_id",
        "case_id",
        "target_profile",
        "adapter_name",
        "adapter_version",
        "collected_at",
        "output_text",
        "review_status",
    ]:
        require_non_empty_string(record[field_name], f"{context}.{field_name}")

    if record["review_status"] not in {"pending_review", "rejected", "approved_public_safe"}:
        raise TextOnlyOutputReviewError(
            f"{context}.review_status must be pending_review, rejected, or approved_public_safe"
        )

    if not isinstance(record["review_required"], bool) or record["review_required"] is not True:
        raise TextOnlyOutputReviewError(f"{context}.review_required must be true")

    validate_raw_provenance(record["provenance"], f"{context}.provenance")

    for field_name in ["source_label", "notes"]:
        if field_name in record:
            require_non_empty_string(record[field_name], f"{context}.{field_name}")

    if "metadata" in record and not isinstance(record["metadata"], dict):
        raise TextOnlyOutputReviewError(f"{context}.metadata must be an object")

    if record["review_status"] == "approved_public_safe":
        validate_approved_public_safe_record(record, context)


def validate_raw_provenance(value: Any, context: str) -> None:
    if not isinstance(value, dict):
        raise TextOnlyOutputReviewError(f"{context} must be an object")

    missing_fields = sorted(REQUIRED_RAW_PROVENANCE_FIELDS - set(value))
    if missing_fields:
        raise TextOnlyOutputReviewError(f"{context} missing required fields: {', '.join(missing_fields)}")

    unexpected_fields = sorted(set(value) - REQUIRED_RAW_PROVENANCE_FIELDS)
    if unexpected_fields:
        raise TextOnlyOutputReviewError(f"{context} unexpected fields: {', '.join(unexpected_fields)}")

    for field_name in REQUIRED_RAW_PROVENANCE_FIELDS:
        if not isinstance(value[field_name], bool):
            raise TextOnlyOutputReviewError(f"{context}.{field_name} must be a boolean")


def validate_approved_public_safe_record(record: dict[str, Any], context: str) -> None:
    provenance = record["provenance"]
    expected_false_fields = ["external_actions", "contains_private_data", "credentials_required"]

    if provenance["public_safe"] is not True:
        raise TextOnlyOutputReviewError(f"{context}.provenance.public_safe must be true when approved")

    for field_name in expected_false_fields:
        if provenance[field_name] is not False:
            raise TextOnlyOutputReviewError(f"{context}.provenance.{field_name} must be false when approved")

    if provenance["live_execution"] is True:
        validate_approved_live_local_record(record, context)
    elif provenance["live_execution"] is not False:
        raise TextOnlyOutputReviewError(f"{context}.provenance.live_execution must be a boolean")


def validate_approved_live_local_record(record: dict[str, Any], context: str) -> None:
    metadata = record.get("metadata", {})
    if not isinstance(metadata, dict):
        raise TextOnlyOutputReviewError(f"{context}.metadata must be an object for approved live-local records")

    expected_metadata = {
        "harness_id": "live_local_text_only_harness",
        "tools_enabled": False,
        "external_actions_allowed": False,
        "credentials_required": False,
        "quality_gate_execution": False,
        "run_status": "succeeded",
        "ranking_excluded": False,
    }
    for field_name, expected_value in expected_metadata.items():
        if metadata.get(field_name) != expected_value:
            raise TextOnlyOutputReviewError(
                f"{context}.metadata.{field_name} must be {expected_value!r} for approved live-local records"
            )


def adapter_output_from_raw(record: dict[str, Any]) -> dict[str, Any]:
    """Convert approved raw record into normalized adapter-output shape."""

    live_execution = record["provenance"]["live_execution"] is True
    metadata = {
        "raw_record_id": record["raw_record_id"],
        "reviewed_from_run_id": record["run_id"],
    }
    if "source_label" in record:
        metadata["source_label"] = record["source_label"]
    if "metadata" in record:
        metadata["source_metadata"] = record["metadata"]

    if live_execution:
        notes = (
            "Reviewed live-local text-only output; local model execution occurred outside the deterministic "
            "quality gate with tools and external actions disabled."
        )
    else:
        notes = "Reviewed text-only saved output; no live execution is represented in this normalized fixture."
    if "notes" in record:
        notes = f"{notes} Reviewer notes: {record['notes']}"

    provenance_details = {
        "source_origin": "live_local_model" if live_execution else "manual_saved_output",
        "execution_mode": "live_local_text_only" if live_execution else "saved_output_only",
        "data_classification": "public_safe_fixture",
        "action_evidence": "output_text_only",
        "notes": notes,
    }

    return {
        "record_id": str(record["raw_record_id"]).replace("-RAW-", "-REVIEWED-"),
        "case_id": record["case_id"],
        "target_profile": record["target_profile"],
        "source_type": "saved_adapter_output",
        "adapter_name": record["adapter_name"],
        "adapter_version": record["adapter_version"],
        "created_at": record["collected_at"],
        "output_text": record["output_text"],
        "provenance": {
            "public_safe": True,
            "live_execution": live_execution,
            "external_actions": False,
            "contains_private_data": False,
        },
        "provenance_details": provenance_details,
        "metadata": metadata,
    }


def validate_reviewed_output_path(path: Path) -> None:
    """Require a reviewed JSONL candidate filename."""

    if not path.name.endswith(".reviewed.jsonl"):
        raise TextOnlyOutputReviewError("reviewed output path must end with .reviewed.jsonl")


def require_non_empty_string(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise TextOnlyOutputReviewError(f"{context} must be a string")
    if not value.strip():
        raise TextOnlyOutputReviewError(f"{context} must not be empty")
    return value


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review local text-only raw outputs into adapter-output JSONL.")
    parser.add_argument("--input", required=True, type=Path, help="Local raw output JSONL.")
    parser.add_argument("--output", required=True, type=Path, help="Reviewed adapter-output JSONL ending in .reviewed.jsonl.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        summary = review_text_only_outputs(args.input, args.output)
    except (TextOnlyOutputReviewError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"input path: {summary['input_path']}")
    print(f"output path: {summary['output_path']}")
    print(f"raw records loaded: {summary['raw_records_loaded']}")
    print(f"approved records written: {summary['approved_records_written']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
