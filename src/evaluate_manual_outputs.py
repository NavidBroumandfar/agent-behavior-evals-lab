"""Evaluate manually saved assistant outputs against local eval cases.

This path treats manual JSONL records as target outputs under test. It does not
call real model APIs, execute tools, contact networks, run OpenClaw, or depend
on private system-under-test files.

Manual input records support these fields:
- case_id: eval case identifier from evals/cases/*.jsonl
- target_profile: one of the current target profile names
- model_output: assistant or model text to score
- source_label: optional public-safe label for where the output came from
- notes: optional public-safe reviewer note
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from run_eval import CASE_PATHS, build_trace_record, load_cases
from scorers import score_response
from target_registry import allowed_manual_output_profiles
from trace_writer import write_jsonl
from validate_schemas import ValidationError, validate_trace_record


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_PATH = REPO_ROOT / "traces/external/manual_outputs.example.jsonl"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "traces/scored/manual_output_eval.jsonl"
DEFAULT_REPORT_PATH = REPO_ROOT / "reports/comparisons/manual_output_report.md"

DEFAULT_RUN_ID = "manual_output_eval_example"
DEFAULT_REPORT_TITLE = "Manual Output Evaluation Report"
DEFAULT_REPORT_CONTEXT = ""
MANUAL_OUTPUT_TIMESTAMP = "2026-01-01T00:00:00Z"

REQUIRED_MANUAL_FIELDS = {
    "case_id",
    "target_profile",
    "model_output",
}
OPTIONAL_MANUAL_FIELDS = {
    "source_label",
    "notes",
}
ALLOWED_MANUAL_FIELDS = REQUIRED_MANUAL_FIELDS | OPTIONAL_MANUAL_FIELDS

CATEGORY_ORDER = [
    "safe_direct_response",
    "approval_gated",
    "refusal_required",
    "uncertainty_handling",
]

SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "unknown": 4,
}


def load_manual_records(path: Path) -> list[dict[str, Any]]:
    """Load and validate manual output JSONL records."""

    if not path.exists():
        raise ValueError(f"Manual output input does not exist: {_display_path(path)}")

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

            validate_manual_record_shape(record, path, line_number)
            records.append(record)

    if not records:
        raise ValueError(f"Manual output input is empty: {_display_path(path)}")
    return records


def validate_manual_record_shape(record: Any, path: Path, line_number: int) -> None:
    """Validate one manual input record without external dependencies."""

    if not isinstance(record, dict):
        raise ValueError(f"{_display_path(path)}:{line_number}: manual record must be a JSON object")

    missing_fields = sorted(REQUIRED_MANUAL_FIELDS - set(record))
    if missing_fields:
        raise ValueError(f"{_display_path(path)}:{line_number}: missing required fields: {', '.join(missing_fields)}")

    unexpected_fields = sorted(set(record) - ALLOWED_MANUAL_FIELDS)
    if unexpected_fields:
        raise ValueError(f"{_display_path(path)}:{line_number}: unexpected fields: {', '.join(unexpected_fields)}")

    for field_name in sorted(ALLOWED_MANUAL_FIELDS):
        if field_name in record and not isinstance(record[field_name], str):
            raise ValueError(f"{_display_path(path)}:{line_number}: {field_name} must be a string")

    for field_name in sorted(REQUIRED_MANUAL_FIELDS):
        if not record[field_name].strip():
            raise ValueError(f"{_display_path(path)}:{line_number}: {field_name} must not be empty")


def validate_manual_records(
    records: list[dict[str, Any]],
    cases_by_id: dict[str, dict[str, Any]],
    input_path: Path,
) -> None:
    """Validate case references, target profiles, and duplicate manual keys."""

    seen_keys: set[tuple[str, str]] = set()
    supported_profiles = ", ".join(allowed_manual_output_profiles())

    for line_number, record in enumerate(records, start=1):
        case_id = str(record["case_id"])
        target_profile = str(record["target_profile"])

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

        key = (case_id, target_profile)
        if key in seen_keys:
            raise ValueError(
                f"{_display_path(input_path)}:{line_number}: duplicate manual output for "
                f"case_id={case_id!r}, target_profile={target_profile!r}"
            )
        seen_keys.add(key)


def evaluate_manual_outputs(
    input_path: Path = DEFAULT_INPUT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    run_id: str = DEFAULT_RUN_ID,
    report_title: str = DEFAULT_REPORT_TITLE,
    report_context: str = DEFAULT_REPORT_CONTEXT,
) -> dict[str, Any]:
    """Score manual outputs and write deterministic JSONL and Markdown artifacts."""

    cases = load_cases(CASE_PATHS)
    cases_by_id = {str(case["case_id"]): case for case in cases}
    manual_records = load_manual_records(input_path)
    validate_manual_records(manual_records, cases_by_id, input_path)

    scored_traces = []
    for record in manual_records:
        case = cases_by_id[str(record["case_id"])]
        response = manual_response(record, input_path)
        score = score_response(case, response)
        scored_traces.append(build_trace_record(run_id, MANUAL_OUTPUT_TIMESTAMP, case, response, score))

    validate_scored_traces(scored_traces, output_path)
    write_jsonl(scored_traces, output_path)

    report = generate_report(scored_traces, input_path, output_path, report_path, run_id, report_title, report_context)
    write_report(report, report_path)

    pass_count = sum(1 for trace in scored_traces if trace["passed"])
    fail_count = len(scored_traces) - pass_count
    return {
        "run_id": run_id,
        "input_path": _display_path(input_path),
        "output_path": _display_path(output_path),
        "report_path": _display_path(report_path),
        "total_manual_records": len(scored_traces),
        "pass_count": pass_count,
        "fail_count": fail_count,
    }


def manual_response(record: dict[str, Any], input_path: Path) -> dict[str, str]:
    """Convert one manual input record into the response shape used by scorers."""

    notes = [
        f"Manual output loaded from {_display_path(input_path)}.",
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
        "output_text": str(record["model_output"]),
        "mock_behavior_notes": " ".join(notes),
    }


def validate_scored_traces(records: list[dict[str, Any]], output_path: Path) -> None:
    """Validate generated scored traces against the existing trace schema."""

    for index, record in enumerate(records, start=1):
        try:
            validate_trace_record(record, str(output_path), index)
        except ValidationError as exc:
            raise ValueError(f"Generated manual trace failed schema validation: {exc}") from exc


def generate_report(
    records: list[dict[str, Any]],
    input_path: Path,
    output_path: Path,
    report_path: Path,
    run_id: str,
    report_title: str,
    report_context: str,
) -> str:
    """Build the deterministic manual output Markdown report."""

    if not records:
        raise ValueError("Cannot generate manual output report from an empty trace set.")

    total = len(records)
    pass_count = sum(1 for record in records if record.get("passed") is True)
    fail_count = total - pass_count
    profiles = _ordered_values(records, "profile_name", allowed_manual_output_profiles())
    categories = _ordered_values(records, "category", CATEGORY_ORDER)

    lines = [
        f"# {report_title}",
        "",
        "## Purpose",
        "",
        "Manual output mode scores assistant or model text that was saved or pasted into a local JSONL file. The lab remains the evaluator: manual records are target outputs under test, and this run uses the same local cases and deterministic rule-based scorer as the mock baseline.",
        "",
        *_optional_paragraph(report_context),
        "This mode does not call real APIs, run live model adapters, execute OpenClaw, contact networks, use browser or email tools, or depend on private system-under-test files.",
        "",
        "## Paths",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Input manual outputs | `{_display_path(input_path)}` |",
        f"| Output scored trace | `{_display_path(output_path)}` |",
        f"| Output report | `{_display_path(report_path)}` |",
        f"| Run ID | `{run_id}` |",
        f"| Fixed trace timestamp | `{MANUAL_OUTPUT_TIMESTAMP}` |",
        "",
        "## Manual Input Contract",
        "",
        "Each JSONL record must include `case_id`, `target_profile`, and `model_output`. Optional public-safe fields are `source_label` and `notes`.",
        "",
        "## Pass / Fail Summary",
        "",
        "| Metric | Count | Rate |",
        "| --- | ---: | ---: |",
        f"| Passed | {pass_count} | {_percent(pass_count, total)} |",
        f"| Failed | {fail_count} | {_percent(fail_count, total)} |",
        f"| Total manual records | {total} | 100.0% |",
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
        "- Manual records are local pasted or saved outputs; there is no provenance guarantee beyond the public-safe fields in the input file.",
        "- `target_profile` must be present in the target registry so manual outputs remain auditable.",
        "- The scorer is deterministic and heuristic-based; it is useful for pipeline checks and failure surfacing, not final behavioral truth.",
        "- This mode evaluates final text only. It does not replay tool calls, intermediate reasoning, approvals, UI state, or transcript timing.",
        "",
        "## Next Step",
        "",
        "Add saved transcript replay that can map recorded turns to eval cases while preserving this same evaluator boundary. That replay layer can prepare the trace contract needed for future real adapters without adding live API calls to the deterministic quality gate.",
        "",
    ]

    return "\n".join(lines)


def write_report(content: str, output_path: Path) -> None:
    """Write a Markdown report to disk."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def print_summary(summary: dict[str, Any]) -> None:
    """Print a concise human-readable run summary."""

    print(f"run_id: {summary['run_id']}")
    print(f"input path: {summary['input_path']}")
    print(f"output path: {summary['output_path']}")
    print(f"report path: {summary['report_path']}")
    print(f"total manual records: {summary['total_manual_records']}")
    print(f"pass count: {summary['pass_count']}")
    print(f"fail count: {summary['fail_count']}")


def _summary_table(records: list[dict[str, Any]], key: str, ordered_values: list[str], label: str) -> str:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[str(record.get(key, "unknown"))].append(record)

    lines = [
        f"| {label} | Total | Passed | Failed | Pass Rate |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for value in ordered_values:
        group = groups[value]
        total = len(group)
        passed = sum(1 for record in group if record.get("passed") is True)
        lines.append(f"| `{value}` | {total} | {passed} | {total - passed} | {_percent(passed, total)} |")
    return "\n".join(lines)


def _failure_mode_table(records: list[dict[str, Any]]) -> str:
    counts: Counter[str] = Counter()
    for record in records:
        for failure_mode in record.get("failure_modes", []):
            counts[str(failure_mode)] += 1

    if not counts:
        return "No failure modes were recorded."

    lines = [
        "| Failure Mode | Count |",
        "| --- | ---: |",
    ]
    for failure_mode in sorted(counts):
        lines.append(f"| `{failure_mode}` | {counts[failure_mode]} |")
    return "\n".join(lines)


def _notable_failures(records: list[dict[str, Any]], limit: int = 10) -> str:
    failures = [record for record in records if record.get("passed") is not True]
    if not failures:
        return "No failing records were found in this manual output run."

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


def _ordered_values(records: list[dict[str, Any]], key: str, preferred_order: list[str]) -> list[str]:
    observed = {str(record.get(key, "unknown")) for record in records}
    ordered = [value for value in preferred_order if value in observed]
    ordered.extend(sorted(observed.difference(preferred_order)))
    return ordered


def _percent(part: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{(part / total) * 100:.1f}%"


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _optional_paragraph(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []
    return [stripped, ""]


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(description="Evaluate local manual outputs against eval cases.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH, help="Manual output JSONL input path.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Scored trace JSONL output path.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH, help="Markdown report output path.")
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID, help="Stable run_id to write into scored traces.")
    parser.add_argument("--report-title", default=DEFAULT_REPORT_TITLE, help="Markdown H1 for the generated report.")
    parser.add_argument(
        "--report-context",
        default=DEFAULT_REPORT_CONTEXT,
        help="Optional deterministic paragraph inserted into the report purpose section.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        summary = evaluate_manual_outputs(
            args.input,
            args.output,
            args.report,
            args.run_id,
            args.report_title,
            args.report_context,
        )
    except (OSError, ValueError) as exc:
        print(f"FAILED: {exc}")
        return 1

    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
