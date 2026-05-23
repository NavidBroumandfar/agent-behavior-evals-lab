"""Collect reviewed-later text-only outputs into local raw JSONL.

This is an M7 helper for non-gated saved-output experiments. It only normalizes
already-provided text into a local raw file. It does not call providers, run
models, execute agents, use credentials, or perform external actions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from target_registry import target_profile_names
from trace_writer import write_jsonl
from validate_adapter_run_metadata import DEFAULT_METADATA_PATH, load_metadata, validate_metadata


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_INPUT_FIELDS = {
    "case_id",
    "target_profile",
    "output_text",
}
OPTIONAL_INPUT_FIELDS = {
    "source_label",
    "notes",
    "metadata",
}
ALLOWED_INPUT_FIELDS = REQUIRED_INPUT_FIELDS | OPTIONAL_INPUT_FIELDS


class TextOnlyOutputCollectionError(Exception):
    """Text-only output collection error."""


def collect_text_only_outputs(metadata_path: Path, input_path: Path, output_path: Path) -> dict[str, Any]:
    """Collect text-only saved outputs into local raw JSONL."""

    validate_local_raw_output_path(output_path)
    validate_metadata(metadata_path)
    metadata = load_metadata(metadata_path)
    input_records = load_text_output_inputs(input_path)
    validate_inputs_against_metadata(input_records, metadata, input_path)

    raw_records = []
    for index, record in enumerate(input_records, start=1):
        raw_records.append(raw_record_from_input(record, metadata, index))

    write_jsonl(raw_records, output_path)

    return {
        "run_id": metadata["run_id"],
        "input_path": display_path(input_path),
        "output_path": display_path(output_path),
        "raw_records_written": len(raw_records),
        "review_status": "pending_review",
    }


def load_text_output_inputs(path: Path) -> list[dict[str, Any]]:
    """Load local text-only input records."""

    if not path.exists():
        raise TextOnlyOutputCollectionError(f"{display_path(path)}: file does not exist")

    records = []
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise TextOnlyOutputCollectionError(
                    f"{display_path(path)}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc
            validate_text_output_input(record, path, line_number)
            records.append(record)

    if not records:
        raise TextOnlyOutputCollectionError(f"{display_path(path)}: file contains no text output records")
    return records


def validate_text_output_input(record: Any, path: Path, line_number: int) -> None:
    """Validate one text-only input record."""

    context = f"{display_path(path)}:{line_number}"
    if not isinstance(record, dict):
        raise TextOnlyOutputCollectionError(f"{context}: record must be an object")

    missing_fields = sorted(REQUIRED_INPUT_FIELDS - set(record))
    if missing_fields:
        raise TextOnlyOutputCollectionError(f"{context}: missing required fields: {', '.join(missing_fields)}")

    unexpected_fields = sorted(set(record) - ALLOWED_INPUT_FIELDS)
    if unexpected_fields:
        raise TextOnlyOutputCollectionError(f"{context}: unexpected fields: {', '.join(unexpected_fields)}")

    for field_name in REQUIRED_INPUT_FIELDS | {"source_label", "notes"}:
        if field_name in record:
            require_non_empty_string(record[field_name], f"{context}.{field_name}")

    if "metadata" in record and not isinstance(record["metadata"], dict):
        raise TextOnlyOutputCollectionError(f"{context}.metadata must be an object")


def validate_inputs_against_metadata(
    records: list[dict[str, Any]],
    metadata: dict[str, Any],
    input_path: Path,
) -> None:
    """Validate case/profile references against the run metadata."""

    metadata_case_ids = set(str(case_id) for case_id in metadata["case_selection"]["case_ids"])
    metadata_target_profile = str(metadata["target"]["target_profile"])
    registered_profiles = target_profile_names()
    seen_keys: set[tuple[str, str]] = set()

    for line_number, record in enumerate(records, start=1):
        context = f"{display_path(input_path)}:{line_number}"
        case_id = str(record["case_id"])
        target_profile = str(record["target_profile"])

        if case_id not in metadata_case_ids:
            expected = ", ".join(sorted(metadata_case_ids))
            raise TextOnlyOutputCollectionError(f"{context}.case_id must be one of metadata case IDs: {expected}")

        if target_profile != metadata_target_profile:
            raise TextOnlyOutputCollectionError(
                f"{context}.target_profile must match metadata target_profile {metadata_target_profile!r}"
            )

        if target_profile not in registered_profiles:
            expected = ", ".join(registered_profiles)
            raise TextOnlyOutputCollectionError(f"{context}.target_profile must be one of: {expected}")

        key = (case_id, target_profile)
        if key in seen_keys:
            raise TextOnlyOutputCollectionError(
                f"{context}: duplicate output for case_id={case_id!r}, target_profile={target_profile!r}"
            )
        seen_keys.add(key)


def raw_record_from_input(record: dict[str, Any], metadata: dict[str, Any], index: int) -> dict[str, Any]:
    """Convert one text-only input into a local raw record."""

    raw_record = {
        "raw_record_id": f"{metadata['run_id']}-RAW-{index:03d}",
        "run_id": metadata["run_id"],
        "case_id": record["case_id"],
        "target_profile": record["target_profile"],
        "adapter_name": metadata["adapter"]["adapter_name"],
        "adapter_version": metadata["adapter"]["adapter_version"],
        "collected_at": metadata["created_at"],
        "output_text": record["output_text"],
        "review_status": "pending_review",
        "provenance": {
            "public_safe": False,
            "live_execution": metadata["provenance"]["live_execution"],
            "external_actions": False,
            "contains_private_data": False,
            "credentials_required": False,
        },
        "review_required": True,
    }

    source_label = str(record.get("source_label", "")).strip()
    if source_label:
        raw_record["source_label"] = source_label

    notes = str(record.get("notes", "")).strip()
    if notes:
        raw_record["notes"] = notes

    source_metadata = record.get("metadata")
    if source_metadata:
        raw_record["metadata"] = source_metadata

    return raw_record


def validate_local_raw_output_path(path: Path) -> None:
    """Require a local-only JSONL filename for raw outputs."""

    if not path.name.endswith(".local.jsonl"):
        raise TextOnlyOutputCollectionError("raw output path must end with .local.jsonl")


def require_non_empty_string(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise TextOnlyOutputCollectionError(f"{context} must be a string")
    if not value.strip():
        raise TextOnlyOutputCollectionError(f"{context} must not be empty")
    return value


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect text-only outputs into local raw JSONL.")
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA_PATH, help="Adapter run metadata JSON.")
    parser.add_argument("--input", required=True, type=Path, help="Local JSONL with case_id, target_profile, output_text.")
    parser.add_argument("--output", required=True, type=Path, help="Local raw output JSONL ending in .local.jsonl.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        summary = collect_text_only_outputs(args.metadata, args.input, args.output)
    except (TextOnlyOutputCollectionError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"run_id: {summary['run_id']}")
    print(f"input path: {summary['input_path']}")
    print(f"output path: {summary['output_path']}")
    print(f"raw records written: {summary['raw_records_written']}")
    print(f"review status: {summary['review_status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
