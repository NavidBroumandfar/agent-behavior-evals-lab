"""Replay saved transcript fixtures into the local evaluator.

Saved transcripts are static target-side fixtures. This script does not call
real model APIs, run OpenClaw, execute tools, use live adapters, or read private
runtime data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from evaluate_manual_outputs import (
    CATEGORY_ORDER,
    SEVERITY_RANK,
    _display_path,
    _failure_mode_table,
    _ordered_values,
    _percent,
    _summary_table,
    _truncate,
)
from reporting_utils import atomic_write_text
from run_eval import CASE_PATHS, build_trace_record, load_cases
from scorers import score_response
from schema_validation_utils import load_json_object, validate_schema_value
from target_registry import allowed_manual_output_profiles
from trace_writer import write_jsonl
from validate_schemas import ValidationError, validate_trace_record


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = REPO_ROOT / "traces/external/saved_transcripts.example.jsonl"
OUTPUT_PATH = REPO_ROOT / "traces/scored/saved_transcript_replay_eval.jsonl"
REPORT_PATH = REPO_ROOT / "reports/comparisons/saved_transcript_replay_report.md"
SCHEMA_PATH = REPO_ROOT / "schemas/saved_transcript.schema.json"

RUN_ID = "saved_transcript_replay_example"
TRACE_TIMESTAMP = "2026-01-01T00:00:00Z"
REPORT_TITLE = "Saved Transcript Replay Report"
REPORT_CONTEXT = (
    "Saved transcript replay scores a selected assistant turn from each static transcript fixture against an existing "
    "eval case. The lab remains the evaluator: transcripts are target-side fixtures under test, and replay uses the "
    "same local cases and deterministic rule-based scorer as the mock and manual-output paths."
)

EXPECTED_TRANSCRIPT_PROVENANCE_VALUES = {
    "public_safe": True,
    "live_execution": False,
    "external_actions": False,
    "contains_private_data": False,
    "credentials_required": False,
}


def load_transcripts(path: Path) -> list[dict[str, Any]]:
    """Load and validate saved transcript JSONL records."""

    if not path.exists():
        raise ValueError(f"Saved transcript input does not exist: {_display_path(path)}")

    schema = load_json_object(SCHEMA_PATH, "schema", REPO_ROOT, ValueError)
    records = []
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {_display_path(path)} on line {line_number}: {exc}") from exc

            validate_transcript_shape(record, path, line_number, schema)
            records.append(record)

    if not records:
        raise ValueError(f"Saved transcript input is empty: {_display_path(path)}")
    return records


def validate_transcript_shape(
    record: Any,
    path: Path,
    line_number: int,
    schema: dict[str, Any] | None = None,
) -> None:
    """Validate one transcript record before case/profile checks."""

    schema = schema if schema is not None else load_json_object(SCHEMA_PATH, "schema", REPO_ROOT, ValueError)
    validate_schema_value(record, schema, "", path, REPO_ROOT, validation_error_for_line(path, line_number))


def validation_error_for_line(path: Path, line_number: int) -> Callable[[str], ValueError]:
    """Build line-aware validation errors for shared schema checks."""

    def build_error(reason: str) -> ValueError:
        return ValueError(f"{_display_path(path)}:{line_number}: {reason}")

    return build_error


def validate_transcripts(
    records: list[dict[str, Any]],
    cases_by_id: dict[str, dict[str, Any]],
    input_path: Path,
) -> None:
    """Validate case references, target profiles, transcript IDs, and selected assistant turns."""

    seen_transcript_ids: set[str] = set()
    supported_profiles = ", ".join(allowed_manual_output_profiles())

    for line_number, record in enumerate(records, start=1):
        transcript_id = str(record["transcript_id"])
        case_id = str(record["case_id"])
        target_profile = str(record["target_profile"])

        if transcript_id in seen_transcript_ids:
            raise ValueError(f"{_display_path(input_path)}:{line_number}: duplicate transcript_id {transcript_id!r}")
        seen_transcript_ids.add(transcript_id)

        if case_id not in cases_by_id:
            known_cases = ", ".join(sorted(cases_by_id))
            raise ValueError(
                f"{_display_path(input_path)}:{line_number}: unknown case_id {case_id!r}; "
                f"expected one of: {known_cases}"
            )

        if target_profile not in allowed_manual_output_profiles():
            raise ValueError(
                f"{_display_path(input_path)}:{line_number}: unsupported target_profile {target_profile!r}; "
                f"expected one of: {supported_profiles}"
            )

        assistant_turn_index = int(record["assistant_turn_index"])
        turns = record["turns"]
        if assistant_turn_index < 0 or assistant_turn_index >= len(turns):
            raise ValueError(
                f"{_display_path(input_path)}:{line_number}: assistant_turn_index {assistant_turn_index} "
                f"is outside turns range 0..{len(turns) - 1}"
            )

        selected_turn = turns[assistant_turn_index]
        if selected_turn["role"] != "assistant":
            raise ValueError(
                f"{_display_path(input_path)}:{line_number}: assistant_turn_index {assistant_turn_index} "
                f"points to role {selected_turn['role']!r}, expected 'assistant'"
            )

        selected_turn_id = str(record["selected_assistant_turn_id"])
        actual_turn_id = str(selected_turn.get("turn_id", ""))
        if actual_turn_id != selected_turn_id:
            raise ValueError(
                f"{_display_path(input_path)}:{line_number}: selected_assistant_turn_id {selected_turn_id!r} "
                f"does not match selected turn_id {actual_turn_id!r}"
            )

        validate_public_safe_transcript_metadata(record, input_path, line_number)


def validate_public_safe_transcript_metadata(record: dict[str, Any], input_path: Path, line_number: int) -> None:
    """Validate public-safe rich transcript metadata beyond schema shape."""

    provenance = record["provenance"]
    for field_name, expected_value in EXPECTED_TRANSCRIPT_PROVENANCE_VALUES.items():
        if provenance[field_name] is not expected_value:
            expected_text = str(expected_value).lower()
            raise ValueError(
                f"{_display_path(input_path)}:{line_number}: provenance.{field_name} must be {expected_text}"
            )

    for index, summary in enumerate(record.get("tool_call_summaries", [])):
        if summary["external_action"] is not False:
            raise ValueError(
                f"{_display_path(input_path)}:{line_number}: "
                f"tool_call_summaries[{index}].external_action must be false"
            )

    approval = record.get("approval")
    if approval:
        request_present = approval["request_present"]
        outcome = approval["outcome"]
        if request_present is False and outcome != "not_requested":
            raise ValueError(
                f"{_display_path(input_path)}:{line_number}: approval.outcome must be not_requested "
                "when request_present is false"
            )
        if request_present is True and outcome == "not_requested":
            raise ValueError(
                f"{_display_path(input_path)}:{line_number}: approval.outcome must not be not_requested "
                "when request_present is true"
            )


def run_replay(
    input_path: Path = INPUT_PATH,
    output_path: Path = OUTPUT_PATH,
    report_path: Path = REPORT_PATH,
    run_id: str = RUN_ID,
    trace_timestamp: str = TRACE_TIMESTAMP,
    report_title: str = REPORT_TITLE,
    report_context: str = REPORT_CONTEXT,
) -> dict[str, Any]:
    """Replay all saved transcripts, score selected assistant turns, and write artifacts."""

    cases = load_cases(CASE_PATHS)
    cases_by_id = {str(case["case_id"]): case for case in cases}
    transcripts = load_transcripts(input_path)
    validate_transcripts(transcripts, cases_by_id, input_path)

    scored_traces = []
    for transcript in transcripts:
        case = cases_by_id[str(transcript["case_id"])]
        response = transcript_response(transcript, input_path)
        score = score_response(case, response)
        scored_traces.append(build_trace_record(run_id, trace_timestamp, case, response, score))

    validate_scored_traces(scored_traces, output_path)
    write_jsonl(scored_traces, output_path)

    report = generate_report(
        scored_traces,
        input_path,
        output_path,
        report_path,
        run_id,
        trace_timestamp,
        report_title,
        report_context,
    )
    atomic_write_text(report, report_path)

    pass_count = sum(1 for trace in scored_traces if trace["passed"])
    fail_count = len(scored_traces) - pass_count
    return {
        "run_id": run_id,
        "input_path": _display_path(input_path),
        "output_path": _display_path(output_path),
        "report_path": _display_path(report_path),
        "total_transcripts": len(scored_traces),
        "pass_count": pass_count,
        "fail_count": fail_count,
    }


def transcript_response(record: dict[str, Any], input_path: Path = INPUT_PATH) -> dict[str, Any]:
    """Convert a selected assistant transcript turn into scorer response shape."""

    assistant_turn_index = int(record["assistant_turn_index"])
    assistant_turn = record["turns"][assistant_turn_index]
    assistant_content = str(assistant_turn["content"])

    notes = [
        f"Saved transcript replay loaded from {_display_path(input_path)}.",
        f"transcript_id={record['transcript_id']}.",
        f"assistant_turn_index={assistant_turn_index}.",
        f"selected_assistant_turn_id={record['selected_assistant_turn_id']}.",
    ]
    source_label = str(record["source_label"]).strip()
    notes.append(f"source_label={source_label}.")
    notes.append(f"tool_call_summaries={len(record.get('tool_call_summaries', []))}.")
    if "approval" in record:
        notes.append(f"approval={json.dumps(record['approval'], sort_keys=True, separators=(',', ':'))}.")
    if "blocked_actions" in record:
        notes.append(
            f"blocked_actions={json.dumps(record['blocked_actions'], sort_keys=True, separators=(',', ':'))}."
        )
    reviewer_notes = str(record.get("notes", "")).strip()
    if reviewer_notes:
        notes.append(f"notes={reviewer_notes}")

    return {
        "profile_name": str(record["target_profile"]),
        "case_id": str(record["case_id"]),
        "output_text": assistant_content,
        "mock_behavior_notes": " ".join(notes),
        "source_record_id": str(record["transcript_id"]),
        "source_type": "saved_transcript_output",
        "adapter_name": "saved_transcript_replay",
        "adapter_version": "0.2.0-m34",
        "adapter_provenance": {
            "public_safe": record["provenance"]["public_safe"],
            "live_execution": record["provenance"]["live_execution"],
            "external_actions": record["provenance"]["external_actions"],
            "contains_private_data": record["provenance"]["contains_private_data"],
        },
        "adapter_provenance_details": record["provenance_details"],
        "adapter_metadata": transcript_metadata(record, assistant_turn),
    }


def transcript_metadata(record: dict[str, Any], assistant_turn: dict[str, Any]) -> dict[str, Any]:
    """Build public-safe transcript metadata for the scored trace."""

    metadata: dict[str, Any] = {
        "transcript_id": record["transcript_id"],
        "source_label": record["source_label"],
        "assistant_turn_index": record["assistant_turn_index"],
        "selected_assistant_turn_id": record["selected_assistant_turn_id"],
        "selected_turn_role": assistant_turn["role"],
        "turn_count": len(record["turns"]),
        "tool_call_summaries": record.get("tool_call_summaries", []),
    }
    if "approval" in record:
        metadata["approval"] = record["approval"]
    if "blocked_actions" in record:
        metadata["blocked_actions"] = record["blocked_actions"]
    if "notes" in record:
        metadata["notes"] = record["notes"]
    return metadata


def validate_scored_traces(records: list[dict[str, Any]], output_path: Path = OUTPUT_PATH) -> None:
    """Validate generated scored traces against the existing trace schema."""

    for index, record in enumerate(records, start=1):
        try:
            validate_trace_record(record, str(output_path), index)
        except ValidationError as exc:
            raise ValueError(f"Generated saved-transcript trace failed schema validation: {exc}") from exc


def generate_report(
    records: list[dict[str, Any]],
    input_path: Path = INPUT_PATH,
    output_path: Path = OUTPUT_PATH,
    report_path: Path = REPORT_PATH,
    run_id: str = RUN_ID,
    trace_timestamp: str = TRACE_TIMESTAMP,
    report_title: str = REPORT_TITLE,
    report_context: str = REPORT_CONTEXT,
) -> str:
    """Build the deterministic saved transcript replay Markdown report."""

    if not records:
        raise ValueError("Cannot generate saved transcript replay report from an empty trace set.")

    total = len(records)
    pass_count = _pass_count(records)
    fail_count = total - pass_count
    profiles = _ordered_values(records, "profile_name", allowed_manual_output_profiles())
    categories = _ordered_values(records, "category", CATEGORY_ORDER)

    lines = [
        f"# {report_title}",
        "",
        "## Purpose",
        "",
        report_context,
        "",
        "This mode does not call real APIs, run OpenClaw, use live adapters, execute tools, contact networks, use browser or email tools, or read private runtime data.",
        "",
        "## Paths",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Input saved transcripts | `{_display_path(input_path)}` |",
        f"| Output scored trace | `{_display_path(output_path)}` |",
        f"| Output report | `{_display_path(report_path)}` |",
        f"| Run ID | `{run_id}` |",
        f"| Fixed trace timestamp | `{trace_timestamp}` |",
        "",
        "## Transcript Input Contract",
        "",
        "Each JSONL record must include `transcript_id`, `case_id`, `target_profile`, `turns`, zero-based `assistant_turn_index`, `selected_assistant_turn_id`, `source_label`, public-safe `provenance`, and `provenance_details`. Turns may carry stable `turn_id` values; the selected turn must have role `assistant` and a `turn_id` matching `selected_assistant_turn_id`. Optional public-safe sections include `tool_call_summaries`, `approval`, `blocked_actions`, and `notes`.",
        "",
        "## Rich Metadata Summary",
        "",
        _rich_metadata_summary(records),
        "",
        "## Pass / Fail Summary",
        "",
        "| Metric | Count | Rate |",
        "| --- | ---: | ---: |",
        f"| Passed | {pass_count} | {_percent(pass_count, total)} |",
        f"| Failed | {fail_count} | {_percent(fail_count, total)} |",
        f"| Total transcripts scored | {total} | 100.0% |",
        "",
        "## Results By Target Profile",
        "",
        _summary_table(records, "profile_name", profiles, "Target Profile"),
        "",
        "## Results By Category",
        "",
        _summary_table(records, "category", categories, "Category"),
        "",
        "## Failure Mode Distribution",
        "",
        _failure_mode_table(records),
        "",
        "## Notable Failures",
        "",
        _notable_failures(records),
        "",
        "## Limitations",
        "",
        "- Replay validates and scores selected assistant text only; it does not execute transcript actions, tools, adapters, or agents.",
        "- Tool calls, approvals, and blocked actions are public-safe summaries for interpretation; they are not raw runtime logs.",
        "- Transcript fixtures are fictional and public-safe; they do not prove production model or agent behavior.",
        "- Transcript metadata is preserved in optional scored-trace source/provenance fields, but the scorer still uses only selected assistant text and the matched eval case.",
        "- The scorer is deterministic and heuristic-based, so results should be read as evaluator signals rather than final behavioral truth.",
        "",
        "## Next Step",
        "",
        "Use saved-transcript evidence to decide whether a later controlled live sandbox is justified; keep any future runtime work tool-disabled or mocked until scope and safety controls are explicit.",
        "",
    ]

    return "\n".join(lines)


def _rich_metadata_summary(records: list[dict[str, Any]]) -> str:
    tool_summary_count = 0
    approval_metadata_count = 0
    blocked_action_count = 0
    source_labels = set()
    for record in records:
        metadata = record.get("adapter_metadata", {})
        if isinstance(metadata, dict):
            tool_summary_count += len(metadata.get("tool_call_summaries", []))
            blocked_action_count += len(metadata.get("blocked_actions", []))
            if "approval" in metadata:
                approval_metadata_count += 1
            source_label = str(metadata.get("source_label", "")).strip()
            if source_label:
                source_labels.add(source_label)

    lines = [
        "| Metric | Count |",
        "| --- | ---: |",
        f"| Source labels | {len(source_labels)} |",
        f"| Tool-call summaries | {tool_summary_count} |",
        f"| Approval metadata records | {approval_metadata_count} |",
        f"| Blocked or denied action summaries | {blocked_action_count} |",
    ]
    return "\n".join(lines)


def print_summary(summary: dict[str, Any]) -> None:
    """Print a concise human-readable replay summary."""

    print(f"run_id: {summary['run_id']}")
    print(f"input path: {summary['input_path']}")
    print(f"output path: {summary['output_path']}")
    print(f"report path: {summary['report_path']}")
    print(f"total transcripts: {summary['total_transcripts']}")
    print(f"pass count: {summary['pass_count']}")
    print(f"fail count: {summary['fail_count']}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay saved transcript fixtures into scored traces.")
    parser.add_argument("--input", type=Path, default=INPUT_PATH, help="Saved transcript JSONL input path.")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="Scored trace JSONL output path.")
    parser.add_argument("--report", type=Path, default=REPORT_PATH, help="Markdown report output path.")
    parser.add_argument("--run-id", default=RUN_ID, help="Run ID for generated scored traces.")
    parser.add_argument("--timestamp", default=TRACE_TIMESTAMP, help="Fixed timestamp for generated scored traces.")
    parser.add_argument("--report-title", default=REPORT_TITLE, help="Markdown report title.")
    parser.add_argument("--report-context", default=REPORT_CONTEXT, help="Purpose paragraph for the report.")
    return parser.parse_args(argv)


def _notable_failures(records: list[dict[str, Any]], limit: int = 10) -> str:
    failures = [record for record in records if record.get("passed") is not True]
    if not failures:
        return "No failing records were found in this saved transcript replay."

    failures.sort(
        key=lambda record: (
            SEVERITY_RANK.get(str(record.get("severity", "unknown")), SEVERITY_RANK["unknown"]),
            str(record.get("profile_name", "")),
            str(record.get("case_id", "")),
        )
    )

    lines = []
    for record in failures[:limit]:
        failure_modes = ", ".join(str(mode) for mode in record.get("failure_modes", [])) or "none"
        rationale = _truncate(str(record.get("rationale", "")), 220)
        lines.extend(
            [
                f"- `{record.get('case_id', 'unknown')}` / `{record.get('profile_name', 'unknown')}` / `{record.get('category', 'unknown')}`",
                f"  - Severity: {record.get('severity', 'unknown')}",
                f"  - Failure modes: {failure_modes}",
                f"  - Rationale: {rationale}",
            ]
        )

    if len(failures) > limit:
        lines.append(f"- Additional failures omitted: {len(failures) - limit}")
    return "\n".join(lines)


def _pass_count(records: list[dict[str, Any]]) -> int:
    return sum(1 for record in records if record.get("passed") is True)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        print_summary(
            run_replay(
                input_path=args.input,
                output_path=args.output,
                report_path=args.report,
                run_id=args.run_id,
                trace_timestamp=args.timestamp,
                report_title=args.report_title,
                report_context=args.report_context,
            )
        )
    except (OSError, ValueError) as exc:
        print(f"FAILED: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
