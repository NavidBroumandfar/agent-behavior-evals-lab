"""Replay saved transcript fixtures into the local evaluator.

Saved transcripts are static target-side fixtures. This script does not call
real model APIs, run OpenClaw, execute tools, use live adapters, or read private
runtime data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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
from run_eval import CASE_PATHS, PROFILE_NAMES, build_trace_record, load_cases
from scorers import score_response
from trace_writer import write_jsonl
from validate_schemas import ValidationError, validate_trace_record


REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = REPO_ROOT / "traces/external/saved_transcripts.example.jsonl"
OUTPUT_PATH = REPO_ROOT / "traces/scored/saved_transcript_replay_eval.jsonl"
REPORT_PATH = REPO_ROOT / "reports/comparisons/saved_transcript_replay_report.md"

RUN_ID = "saved_transcript_replay_example"
TRACE_TIMESTAMP = "2026-01-01T00:00:00Z"

REQUIRED_TRANSCRIPT_FIELDS = {
    "transcript_id",
    "case_id",
    "target_profile",
    "turns",
    "assistant_turn_index",
}
OPTIONAL_TRANSCRIPT_FIELDS = {
    "source_label",
    "notes",
}
ALLOWED_TRANSCRIPT_FIELDS = REQUIRED_TRANSCRIPT_FIELDS | OPTIONAL_TRANSCRIPT_FIELDS
ALLOWED_TURN_FIELDS = {"role", "content"}
ALLOWED_ROLES = {"system", "user", "assistant"}

def load_transcripts(path: Path) -> list[dict[str, Any]]:
    """Load and validate saved transcript JSONL records."""

    if not path.exists():
        raise ValueError(f"Saved transcript input does not exist: {_display_path(path)}")

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

            validate_transcript_shape(record, path, line_number)
            records.append(record)

    if not records:
        raise ValueError(f"Saved transcript input is empty: {_display_path(path)}")
    return records


def validate_transcript_shape(record: Any, path: Path, line_number: int) -> None:
    """Validate one transcript record before case/profile checks."""

    if not isinstance(record, dict):
        raise ValueError(f"{_display_path(path)}:{line_number}: transcript record must be a JSON object")

    missing_fields = sorted(REQUIRED_TRANSCRIPT_FIELDS - set(record))
    if missing_fields:
        raise ValueError(f"{_display_path(path)}:{line_number}: missing required fields: {', '.join(missing_fields)}")

    unexpected_fields = sorted(set(record) - ALLOWED_TRANSCRIPT_FIELDS)
    if unexpected_fields:
        raise ValueError(f"{_display_path(path)}:{line_number}: unexpected fields: {', '.join(unexpected_fields)}")

    for field_name in ["transcript_id", "case_id", "target_profile"]:
        if not isinstance(record[field_name], str) or not record[field_name].strip():
            raise ValueError(f"{_display_path(path)}:{line_number}: {field_name} must be a non-empty string")

    for field_name in sorted(OPTIONAL_TRANSCRIPT_FIELDS):
        if field_name in record and not isinstance(record[field_name], str):
            raise ValueError(f"{_display_path(path)}:{line_number}: {field_name} must be a string")

    if not isinstance(record["assistant_turn_index"], int) or isinstance(record["assistant_turn_index"], bool):
        raise ValueError(f"{_display_path(path)}:{line_number}: assistant_turn_index must be an integer")

    validate_turns(record["turns"], path, line_number)


def validate_turns(turns: Any, path: Path, line_number: int) -> None:
    """Validate the transcript turns array."""

    if not isinstance(turns, list) or not turns:
        raise ValueError(f"{_display_path(path)}:{line_number}: turns must be a non-empty array")

    for turn_index, turn in enumerate(turns):
        if not isinstance(turn, dict):
            raise ValueError(f"{_display_path(path)}:{line_number}: turns[{turn_index}] must be an object")

        missing_fields = sorted(ALLOWED_TURN_FIELDS - set(turn))
        if missing_fields:
            raise ValueError(
                f"{_display_path(path)}:{line_number}: turns[{turn_index}] missing fields: {', '.join(missing_fields)}"
            )

        unexpected_fields = sorted(set(turn) - ALLOWED_TURN_FIELDS)
        if unexpected_fields:
            raise ValueError(
                f"{_display_path(path)}:{line_number}: turns[{turn_index}] unexpected fields: {', '.join(unexpected_fields)}"
            )

        role = turn["role"]
        content = turn["content"]
        if role not in ALLOWED_ROLES:
            allowed_roles = ", ".join(sorted(ALLOWED_ROLES))
            raise ValueError(f"{_display_path(path)}:{line_number}: turns[{turn_index}].role must be one of: {allowed_roles}")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"{_display_path(path)}:{line_number}: turns[{turn_index}].content must be a non-empty string")


def validate_transcripts(
    records: list[dict[str, Any]],
    cases_by_id: dict[str, dict[str, Any]],
    input_path: Path,
) -> None:
    """Validate case references, target profiles, transcript IDs, and selected assistant turns."""

    seen_transcript_ids: set[str] = set()
    supported_profiles = ", ".join(PROFILE_NAMES)

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

        if target_profile not in PROFILE_NAMES:
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


def run_replay() -> dict[str, Any]:
    """Replay all saved transcripts, score selected assistant turns, and write artifacts."""

    cases = load_cases(CASE_PATHS)
    cases_by_id = {str(case["case_id"]): case for case in cases}
    transcripts = load_transcripts(INPUT_PATH)
    validate_transcripts(transcripts, cases_by_id, INPUT_PATH)

    scored_traces = []
    for transcript in transcripts:
        case = cases_by_id[str(transcript["case_id"])]
        response = transcript_response(transcript)
        score = score_response(case, response)
        scored_traces.append(build_trace_record(RUN_ID, TRACE_TIMESTAMP, case, response, score))

    validate_scored_traces(scored_traces)
    write_jsonl(scored_traces, OUTPUT_PATH)

    report = generate_report(scored_traces)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    pass_count = sum(1 for trace in scored_traces if trace["passed"])
    fail_count = len(scored_traces) - pass_count
    return {
        "run_id": RUN_ID,
        "input_path": _display_path(INPUT_PATH),
        "output_path": _display_path(OUTPUT_PATH),
        "report_path": _display_path(REPORT_PATH),
        "total_transcripts": len(scored_traces),
        "pass_count": pass_count,
        "fail_count": fail_count,
    }


def transcript_response(record: dict[str, Any]) -> dict[str, str]:
    """Convert a selected assistant transcript turn into scorer response shape."""

    assistant_turn_index = int(record["assistant_turn_index"])
    assistant_content = str(record["turns"][assistant_turn_index]["content"])

    notes = [
        f"Saved transcript replay loaded from {_display_path(INPUT_PATH)}.",
        f"transcript_id={record['transcript_id']}.",
        f"assistant_turn_index={assistant_turn_index}.",
    ]
    source_label = str(record.get("source_label", "")).strip()
    if source_label:
        notes.append(f"source_label={source_label}.")
    reviewer_notes = str(record.get("notes", "")).strip()
    if reviewer_notes:
        notes.append(f"notes={reviewer_notes}")

    return {
        "profile_name": str(record["target_profile"]),
        "case_id": str(record["case_id"]),
        "output_text": assistant_content,
        "mock_behavior_notes": " ".join(notes),
    }


def validate_scored_traces(records: list[dict[str, Any]]) -> None:
    """Validate generated scored traces against the existing trace schema."""

    for index, record in enumerate(records, start=1):
        try:
            validate_trace_record(record, str(OUTPUT_PATH), index)
        except ValidationError as exc:
            raise ValueError(f"Generated saved-transcript trace failed schema validation: {exc}") from exc


def generate_report(records: list[dict[str, Any]]) -> str:
    """Build the deterministic saved transcript replay Markdown report."""

    if not records:
        raise ValueError("Cannot generate saved transcript replay report from an empty trace set.")

    total = len(records)
    pass_count = _pass_count(records)
    fail_count = total - pass_count
    profiles = _ordered_values(records, "profile_name", PROFILE_NAMES)
    categories = _ordered_values(records, "category", CATEGORY_ORDER)

    lines = [
        "# Saved Transcript Replay Report",
        "",
        "## Purpose",
        "",
        "Saved transcript replay scores a selected assistant turn from each static transcript fixture against an existing eval case. The lab remains the evaluator: transcripts are target-side fixtures under test, and replay uses the same local cases and deterministic rule-based scorer as the mock and manual-output paths.",
        "",
        "This mode does not call real APIs, run OpenClaw, use live adapters, execute tools, contact networks, use browser or email tools, or read private runtime data.",
        "",
        "## Paths",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Input saved transcripts | `{_display_path(INPUT_PATH)}` |",
        f"| Output scored trace | `{_display_path(OUTPUT_PATH)}` |",
        f"| Output report | `{_display_path(REPORT_PATH)}` |",
        f"| Run ID | `{RUN_ID}` |",
        f"| Fixed trace timestamp | `{TRACE_TIMESTAMP}` |",
        "",
        "## Transcript Input Contract",
        "",
        "Each JSONL record must include `transcript_id`, `case_id`, `target_profile`, `turns`, and zero-based `assistant_turn_index`. Each turn must include `role` and `content`; the selected turn must have role `assistant`. Optional public-safe fields are `source_label` and `notes`.",
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
        "- Transcript fixtures are fictional and public-safe; they do not prove production model or agent behavior.",
        "- The current trace schema stores transcript metadata in `mock_behavior_notes` rather than dedicated transcript fields.",
        "- The scorer is deterministic and heuristic-based, so results should be read as evaluator signals rather than final behavioral truth.",
        "",
        "## Next Step",
        "",
        "Refine the future adapter contract so real saved transcripts can preserve stable turn IDs, tool-call summaries, approval state, and source labels while still feeding this same deterministic scoring boundary.",
        "",
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


def main() -> int:
    try:
        print_summary(run_replay())
    except (OSError, ValueError) as exc:
        print(f"FAILED: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
