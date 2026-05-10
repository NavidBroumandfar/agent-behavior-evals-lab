"""Generate a deterministic comparison report for controlled external fixtures.

This report reads already-scored traces from saved-output fixture paths. It
does not rescore outputs, call providers, run local models, execute OpenClaw,
or perform external actions.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from validate_schemas import ValidationError, validate_trace_record


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "reports/comparisons/external_fixture_comparison_report.md"
GENERATED_AT = "2026-05-10T00:00:00Z"

CATEGORY_ORDER = [
    "safe_direct_response",
    "approval_gated",
    "refusal_required",
    "uncertainty_handling",
]

SEVERITY_ORDER = [
    "critical",
    "high",
    "medium",
    "low",
    "unknown",
]

SEVERITY_RANK = {severity: index for index, severity in enumerate(SEVERITY_ORDER)}


@dataclass(frozen=True)
class FixtureSource:
    key: str
    label: str
    path: Path
    description: str


FIXTURE_SOURCES = [
    FixtureSource(
        key="manual_output",
        label="Manual Output Fixture",
        path=REPO_ROOT / "traces/scored/manual_output_eval.jsonl",
        description="Saved or pasted public-safe assistant/model text scored through the manual-output path.",
    ),
    FixtureSource(
        key="openclaw_style_manual",
        label="Sanitized OpenClaw-Style Manual Fixture",
        path=REPO_ROOT / "traces/scored/openclaw_manual_eval.jsonl",
        description="Fictional sanitized OpenClaw-style examples; not live OpenClaw execution.",
    ),
    FixtureSource(
        key="saved_transcript_replay",
        label="Saved Transcript Replay Fixture",
        path=REPO_ROOT / "traces/scored/saved_transcript_replay_eval.jsonl",
        description="Static public-safe transcripts scored by selected assistant turn.",
    ),
    FixtureSource(
        key="adapter_output_import",
        label="Normalized Adapter-Output Import Fixture",
        path=REPO_ROOT / "traces/scored/adapter_output_fixture_import.jsonl",
        description="Validated normalized adapter-output records imported into scored traces.",
    ),
    FixtureSource(
        key="dry_run_adapter_import",
        label="Dry-Run Adapter Contract Fixture",
        path=REPO_ROOT / "traces/scored/dry_run_adapter_output_import.jsonl",
        description="Deterministic no-network dry-run adapter records validated and imported into scored traces.",
    ),
]


class ExternalFixtureComparisonError(Exception):
    """Comparison report generation error."""


def load_source_records(source: FixtureSource) -> list[dict[str, Any]]:
    """Load and validate one scored trace JSONL source."""

    if not source.path.exists():
        raise ExternalFixtureComparisonError(f"missing scored trace file: {_display_path(source.path)}")

    records: list[dict[str, Any]] = []
    with source.path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ExternalFixtureComparisonError(
                    f"{_display_path(source.path)}:{line_number}: invalid JSON: {exc.msg}"
                ) from exc

            try:
                validate_trace_record(record, str(source.path), line_number)
            except ValidationError as exc:
                raise ExternalFixtureComparisonError(f"{exc}") from exc

            records.append(record)

    if not records:
        raise ExternalFixtureComparisonError(f"scored trace file is empty: {_display_path(source.path)}")

    return records


def load_all_sources() -> dict[str, list[dict[str, Any]]]:
    """Load all configured external scored fixture sources."""

    return {source.key: load_source_records(source) for source in FIXTURE_SOURCES}


def generate_report(source_records: dict[str, list[dict[str, Any]]]) -> str:
    """Build the external fixture comparison Markdown report."""

    if set(source_records) != {source.key for source in FIXTURE_SOURCES}:
        raise ExternalFixtureComparisonError("loaded source keys do not match configured fixture sources")

    all_records = [record for source in FIXTURE_SOURCES for record in source_records[source.key]]
    if not all_records:
        raise ExternalFixtureComparisonError("cannot generate report from zero scored records")

    failure_modes = _observed_failure_modes(all_records)
    categories = _ordered_values(all_records, "category", CATEGORY_ORDER)
    severities = _ordered_values(all_records, "severity", SEVERITY_ORDER)

    lines = [
        "# External Fixture Comparison Report",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Generated timestamp | `{GENERATED_AT}` |",
        f"| Output report | `{_display_path(OUTPUT_PATH)}` |",
        f"| Source groups compared | {len(FIXTURE_SOURCES)} |",
        f"| Total scored records compared | {len(all_records)} |",
        "",
        "This is a controlled saved-output fixture comparison, not live benchmark execution. It reads already-scored traces from public-safe fixtures and summarizes the existing scoring results.",
        "",
        "No real provider APIs, local model runtimes, live OpenClaw execution, browser tools, email tools, external actions, credentials, SDKs, network calls, or private runtime integrations are involved.",
        "",
        "## Source Groups",
        "",
        _source_groups_table(source_records),
        "",
        "## Pass / Fail And Average Score By Source",
        "",
        _source_summary_table(source_records),
        "",
        "## Failure Mode Distribution By Source",
        "",
        _source_distribution_table(source_records, "failure_modes", failure_modes, "Failure Mode"),
        "",
        "## Severity Distribution By Source",
        "",
        _source_distribution_table(source_records, "severity", severities, "Severity"),
        "",
        "## Category Distribution By Source",
        "",
        _source_distribution_table(source_records, "category", categories, "Category"),
        "",
        "## Notable Failures",
        "",
        _notable_failures(source_records),
        "",
        "## Interpretation",
        "",
        "These fixture groups exercise the evaluator boundary from different saved-output shapes: pasted manual outputs, fictional OpenClaw-style samples, saved transcript replay, normalized adapter-output import, and dry-run adapter contract output. The comparison helps identify which source groups produce approval-gate, refusal, uncertainty, fake-completion, or unsupported-claim signals under the existing scorer.",
        "",
        "The report does not rank live systems. Differences between source groups reflect the small public-safe fixtures currently present in the repository and the deterministic v0 scorer behavior already captured in the scored traces.",
        "",
        "## Limitations",
        "",
        "- Inputs are already-scored local fixtures; this report does not rerun scoring or collect new outputs.",
        "- Source groups have small and uneven record counts, so pass rates are useful for fixture review, not benchmark claims.",
        "- The sanitized OpenClaw-style group is fictional public-safe sample data and is not evidence from a live OpenClaw runtime.",
        "- The scorer is heuristic and unchanged; report findings inherit its known false positives and false negatives.",
        "- Trace metadata for source provenance still travels through existing trace fields such as `mock_behavior_notes`.",
        "",
        "## Next Step",
        "",
        "A later provider-agnostic adapter interface can build on this dry-run contract path without changing scoring logic or adding live execution to the deterministic quality gate.",
        "",
    ]

    return "\n".join(lines)


def write_report(content: str) -> None:
    """Write the comparison report to the intended deterministic path."""

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(content, encoding="utf-8")


def print_summary(source_records: dict[str, list[dict[str, Any]]]) -> None:
    """Print a concise deterministic CLI summary."""

    total = sum(len(records) for records in source_records.values())
    failed = sum(1 for records in source_records.values() for record in records if record.get("passed") is not True)

    print(f"source groups compared: {len(FIXTURE_SOURCES)}")
    print(f"total scored records compared: {total}")
    print(f"failed records: {failed}")
    print(f"output path: {_display_path(OUTPUT_PATH)}")


def _source_groups_table(source_records: dict[str, list[dict[str, Any]]]) -> str:
    lines = [
        "| Source Group | Scored Trace | Records | Run IDs | Description |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for source in FIXTURE_SOURCES:
        records = source_records[source.key]
        lines.append(
            f"| {source.label} | `{_display_path(source.path)}` | {len(records)} | "
            f"{_format_list(_unique_values(records, 'run_id'))} | {source.description} |"
        )
    return "\n".join(lines)


def _source_summary_table(source_records: dict[str, list[dict[str, Any]]]) -> str:
    lines = [
        "| Source Group | Total Records | Passed | Failed | Pass Rate | Average Score |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for source in FIXTURE_SOURCES:
        records = source_records[source.key]
        total = len(records)
        passed = _pass_count(records)
        failed = total - passed
        lines.append(
            f"| {source.label} | {total} | {passed} | {failed} | "
            f"{_percent(passed, total)} | {_average_score(records)} |"
        )
    return "\n".join(lines)


def _source_distribution_table(
    source_records: dict[str, list[dict[str, Any]]],
    key: str,
    values: list[str],
    label: str,
) -> str:
    if not values:
        return f"No {label.lower()} values were recorded."

    header = "| Source Group | " + " | ".join(f"`{value}`" for value in values) + " |"
    alignment = "| --- | " + " | ".join("---:" for _ in values) + " |"
    lines = [header, alignment]

    for source in FIXTURE_SOURCES:
        records = source_records[source.key]
        if key == "failure_modes":
            counts = _failure_mode_counts(records)
        else:
            counts = Counter(str(record.get(key, "unknown")) for record in records)
        cells = [str(counts.get(value, 0)) for value in values]
        lines.append(f"| {source.label} | " + " | ".join(cells) + " |")

    return "\n".join(lines)


def _notable_failures(source_records: dict[str, list[dict[str, Any]]], limit: int = 8) -> str:
    failures = []
    source_rank = {source.key: index for index, source in enumerate(FIXTURE_SOURCES)}
    source_labels = {source.key: source.label for source in FIXTURE_SOURCES}

    for source in FIXTURE_SOURCES:
        for record in source_records[source.key]:
            if record.get("passed") is not True:
                failures.append((source.key, record))

    if not failures:
        return "No failed records were found across the compared external fixtures."

    failures.sort(
        key=lambda item: (
            SEVERITY_RANK.get(str(item[1].get("severity", "unknown")), SEVERITY_RANK["unknown"]),
            source_rank[item[0]],
            str(item[1].get("case_id", "")),
            str(item[1].get("profile_name", "")),
        )
    )

    lines = []
    for source_key, record in failures[:limit]:
        failure_modes = ", ".join(str(mode) for mode in record.get("failure_modes", [])) or "none"
        rationale = _truncate(str(record.get("rationale", "")), 220)
        lines.extend(
            [
                f"- {source_labels[source_key]}: `{record.get('case_id', 'unknown')}` / `{record.get('profile_name', 'unknown')}` / `{record.get('category', 'unknown')}`",
                f"  - Severity: {record.get('severity', 'unknown')}",
                f"  - Score: {record.get('score', 'unknown')}",
                f"  - Failure modes: {failure_modes}",
                f"  - Rationale: {rationale}",
            ]
        )

    if len(failures) > limit:
        lines.append(f"- Additional failures omitted: {len(failures) - limit}")

    return "\n".join(lines)


def _observed_failure_modes(records: list[dict[str, Any]]) -> list[str]:
    return sorted(_failure_mode_counts(records))


def _failure_mode_counts(records: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for record in records:
        for failure_mode in record.get("failure_modes", []):
            counts[str(failure_mode)] += 1
    return counts


def _ordered_values(records: list[dict[str, Any]], key: str, preferred_order: list[str]) -> list[str]:
    observed = {str(record.get(key, "unknown")) for record in records}
    ordered = [value for value in preferred_order if value in observed]
    ordered.extend(sorted(observed.difference(preferred_order)))
    return ordered


def _unique_values(records: list[dict[str, Any]], key: str) -> list[str]:
    seen = set()
    values = []
    for record in records:
        value = str(record.get(key, "unknown"))
        if value not in seen:
            seen.add(value)
            values.append(value)
    return values


def _pass_count(records: list[dict[str, Any]]) -> int:
    return sum(1 for record in records if record.get("passed") is True)


def _average_score(records: list[dict[str, Any]]) -> str:
    if not records:
        return "0.000"
    total = sum(float(record.get("score", 0.0)) for record in records)
    return f"{total / len(records):.3f}"


def _format_list(values: list[str]) -> str:
    if not values:
        return "`none`"
    return ", ".join(f"`{value}`" for value in values)


def _percent(part: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{(part / total) * 100:.1f}%"


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    try:
        source_records = load_all_sources()
        report = generate_report(source_records)
        write_report(report)
    except (ExternalFixtureComparisonError, OSError, ValueError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    print_summary(source_records)
    return 0


if __name__ == "__main__":
    sys.exit(main())
