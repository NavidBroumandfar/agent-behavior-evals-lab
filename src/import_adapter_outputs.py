"""Import validated normalized adapter-output fixtures into scored traces.

This importer is deterministic and fixture-only. It validates saved adapter
outputs, maps them to existing eval cases, applies the existing scorer, and
writes scored trace records. It does not call providers, run local models,
execute OpenClaw, use browser/email tools, or perform external actions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from run_eval import CASE_PATHS, build_trace_record, load_cases
from scorers import score_response
from target_registry import allowed_adapter_output_profiles
from trace_writer import write_jsonl
from validate_adapter_outputs import (
    DEFAULT_INPUT_PATH,
    AdapterOutputValidationError,
    display_path,
    load_adapter_output_records,
)
from validate_schemas import ValidationError, validate_trace_record


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = REPO_ROOT / "traces/scored/adapter_output_fixture_import.jsonl"

RUN_ID = "m4_adapter_output_fixture_import"
TRACE_TIMESTAMP = "2026-05-10T00:00:00Z"


class AdapterOutputImportError(Exception):
    """Importer error with public-safe context."""


def import_adapter_outputs(
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    *,
    allow_live_local: bool = False,
    case_paths: list[Path] | None = None,
) -> dict[str, Any]:
    """Import normalized adapter outputs into deterministic scored traces."""

    records = load_adapter_output_records(input_path, allow_live_local=allow_live_local)
    cases = load_cases(case_paths or CASE_PATHS)
    cases_by_id = {str(case["case_id"]): case for case in cases}

    validate_adapter_output_references(records, cases_by_id, input_path)

    scored_traces = []
    for record in records:
        case = cases_by_id[str(record["case_id"])]
        response = adapter_output_response(record, input_path)
        try:
            score = score_response(case, response)
        except Exception as exc:
            raise AdapterOutputImportError(
                f"{display_path(input_path)}: scoring failed for record_id={record['record_id']!r}: {exc}"
            ) from exc
        scored_traces.append(build_trace_record(RUN_ID, TRACE_TIMESTAMP, case, response, score))

    validate_scored_traces(scored_traces, output_path)
    try:
        write_jsonl(scored_traces, output_path)
    except OSError as exc:
        raise AdapterOutputImportError(f"could not write {display_path(output_path)}: {exc}") from exc

    pass_count = sum(1 for trace in scored_traces if trace["passed"])
    fail_count = len(scored_traces) - pass_count
    return {
        "run_id": RUN_ID,
        "input_path": display_path(input_path),
        "output_path": display_path(output_path),
        "total_adapter_output_records": len(scored_traces),
        "pass_count": pass_count,
        "fail_count": fail_count,
    }


def validate_adapter_output_references(
    records: list[dict[str, Any]],
    cases_by_id: dict[str, dict[str, Any]],
    input_path: Path,
) -> None:
    """Validate case references and target profiles before scoring."""

    supported_profiles = ", ".join(allowed_adapter_output_profiles())
    known_cases = ", ".join(sorted(cases_by_id))

    for line_number, record in enumerate(records, start=1):
        record_id = str(record["record_id"])
        case_id = str(record["case_id"])
        target_profile = str(record["target_profile"])

        if case_id not in cases_by_id:
            raise AdapterOutputImportError(
                f"{display_path(input_path)}:{line_number}: unknown case_id {case_id!r} "
                f"for record_id={record_id!r}; expected one of: {known_cases}"
            )

        if target_profile not in allowed_adapter_output_profiles():
            raise AdapterOutputImportError(
                f"{display_path(input_path)}:{line_number}: unsupported target_profile {target_profile!r} "
                f"for record_id={record_id!r}; expected one of: {supported_profiles}"
            )


def adapter_output_response(record: dict[str, Any], input_path: Path) -> dict[str, Any]:
    """Convert one normalized adapter-output record into scorer response shape."""

    notes = [
        f"Normalized adapter output imported from {display_path(input_path)}.",
        f"record_id={record['record_id']}.",
        f"source_type={record['source_type']}.",
        f"adapter_name={record['adapter_name']}.",
        f"created_at={record['created_at']}.",
    ]

    adapter_version = str(record.get("adapter_version", "")).strip()
    if adapter_version:
        notes.append(f"adapter_version={adapter_version}.")

    provenance = record["provenance"]
    notes.append(
        "provenance="
        f"public_safe={_bool_text(provenance['public_safe'])},"
        f"live_execution={_bool_text(provenance['live_execution'])},"
        f"external_actions={_bool_text(provenance['external_actions'])},"
        f"contains_private_data={_bool_text(provenance['contains_private_data'])}."
    )

    provenance_details = record.get("provenance_details")
    if provenance_details:
        notes.append(
            f"provenance_details={json.dumps(provenance_details, sort_keys=True, separators=(',', ':'))}."
        )

    metadata = record.get("metadata")
    if metadata:
        notes.append(f"metadata={json.dumps(metadata, sort_keys=True, separators=(',', ':'))}.")

    response = {
        "profile_name": str(record["target_profile"]),
        "case_id": str(record["case_id"]),
        "output_text": str(record["output_text"]),
        "mock_behavior_notes": " ".join(notes),
        "source_record_id": str(record["record_id"]),
        "source_type": str(record["source_type"]),
        "adapter_name": str(record["adapter_name"]),
        "adapter_provenance": provenance,
    }

    if adapter_version:
        response["adapter_version"] = adapter_version
    if provenance_details:
        response["adapter_provenance_details"] = provenance_details
    if metadata:
        response["adapter_metadata"] = metadata

    return response


def validate_scored_traces(records: list[dict[str, Any]], output_path: Path) -> None:
    """Validate generated scored traces against the existing trace schema."""

    for index, record in enumerate(records, start=1):
        try:
            validate_trace_record(record, str(output_path), index)
        except ValidationError as exc:
            raise AdapterOutputImportError(f"Generated adapter-output trace failed schema validation: {exc}") from exc


def _bool_text(value: bool) -> str:
    return "true" if value else "false"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import normalized adapter-output JSONL fixtures into scored traces.")
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="Adapter-output JSONL file to import.",
    )
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Scored trace JSONL path to write.",
    )
    parser.add_argument(
        "--allow-live-local",
        action="store_true",
        help="Allow reviewed live-local text-only adapter outputs outside the deterministic quality gate.",
    )
    parser.add_argument(
        "--case-path",
        action="append",
        type=Path,
        dest="case_paths",
        help="Case JSONL path to use for scoring. Repeat to include multiple case files.",
    )
    return parser.parse_args(argv)


def print_summary(summary: dict[str, Any]) -> None:
    print(f"run_id: {summary['run_id']}")
    print(f"input path: {summary['input_path']}")
    print(f"output path: {summary['output_path']}")
    print(f"total adapter output records: {summary['total_adapter_output_records']}")
    print(f"pass count: {summary['pass_count']}")
    print(f"fail count: {summary['fail_count']}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        summary = import_adapter_outputs(
            args.input,
            args.output,
            allow_live_local=args.allow_live_local,
            case_paths=args.case_paths,
        )
    except (AdapterOutputValidationError, AdapterOutputImportError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print_summary(summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
