"""Generate adjudication-aware reports from public-safe review records.

The reports summarize reviewer decisions over existing scored traces. They do
not rewrite traces, rescore records, call models, execute agents, or collect
new outputs.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from reporting_utils import display_path, format_list, normalize_repo_path, percent, resolve_repo_path, write_text
from validate_adjudications import AdjudicationValidationError, load_adjudications, load_trace_records


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ADJUDICATIONS_PATH = REPO_ROOT / "traces/external/adjudications.example.jsonl"
DEFAULT_ADJUDICATION_MANIFEST_PATH = REPO_ROOT / "traces/external/adjudication_manifest.json"
DEFAULT_SUMMARY_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/adjudication_summary_report.md"
DEFAULT_AGGREGATE_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/adjudicated_aggregate_report.md"

DECISION_ORDER = [
    "uphold_score",
    "override_pass",
    "override_fail",
    "needs_discussion",
]

SEVERITY_ORDER = [
    "critical",
    "high",
    "medium",
    "low",
    "unknown",
]
SEVERITY_RANK = {severity: index for index, severity in enumerate(SEVERITY_ORDER)}

REQUIRED_MANIFEST_FIELDS = {
    "manifest_id",
    "version",
    "generated_at",
    "purpose",
    "scope",
    "non_goals",
    "adjudication_fixtures",
}
REQUIRED_FIXTURE_FIELDS = {
    "fixture_id",
    "label",
    "path",
    "description",
    "expected_record_count",
    "quality_gate_included",
    "source_trace_paths",
    "safety_assertions",
}
REQUIRED_SAFETY_ASSERTIONS = {
    "public_safe",
    "live_execution",
    "external_actions",
    "contains_private_data",
    "credentials_required",
}
EXPECTED_SAFE_ASSERTIONS = {
    "public_safe": True,
    "live_execution": False,
    "external_actions": False,
    "contains_private_data": False,
    "credentials_required": False,
}


@dataclass(frozen=True)
class AdjudicationFixture:
    fixture_id: str
    label: str
    path: Path
    description: str
    expected_record_count: int | None
    quality_gate_included: bool
    source_trace_paths: list[str]


@dataclass(frozen=True)
class AdjudicationContext:
    adjudications: list[dict[str, Any]]
    source_records_by_path: dict[str, list[dict[str, Any]]]
    source_record_by_adjudication_id: dict[str, dict[str, Any]]
    fixtures: list[AdjudicationFixture]
    fixture_by_adjudication_id: dict[str, AdjudicationFixture]


class AdjudicationReportError(Exception):
    """Adjudication report generation error."""


def load_adjudication_context(
    adjudications_path: Path = DEFAULT_ADJUDICATIONS_PATH,
    repo_root: Path = REPO_ROOT,
) -> AdjudicationContext:
    """Load validated adjudications and the source records they review."""

    resolved_adjudications_path = resolve_repo_path(adjudications_path, repo_root)
    fixture = AdjudicationFixture(
        fixture_id="direct_adjudication_input",
        label="Direct Adjudication Input",
        path=resolved_adjudications_path,
        description="Direct adjudication JSONL input.",
        expected_record_count=None,
        quality_gate_included=True,
        source_trace_paths=[],
    )
    return load_adjudication_context_from_fixtures([fixture], repo_root)


def load_adjudication_context_from_manifest(
    manifest_path: Path = DEFAULT_ADJUDICATION_MANIFEST_PATH,
    repo_root: Path = REPO_ROOT,
) -> AdjudicationContext:
    """Load adjudication records from a manifest of fixture families."""

    fixtures = load_adjudication_manifest(manifest_path, repo_root)
    return load_adjudication_context_from_fixtures(fixtures, repo_root)


def load_adjudication_context_from_selection(
    adjudications_path: Path | None = None,
    manifest_path: Path | None = None,
    repo_root: Path = REPO_ROOT,
) -> tuple[AdjudicationContext, Path]:
    """Load the requested adjudication input, preferring the manifest by default."""

    selected_adjudications_path, selected_manifest_path = select_adjudication_input(
        adjudications_path,
        manifest_path,
        repo_root / "traces/external/adjudications.example.jsonl",
        repo_root / "traces/external/adjudication_manifest.json",
    )
    if selected_manifest_path is not None:
        return load_adjudication_context_from_manifest(selected_manifest_path, repo_root), selected_manifest_path
    return load_adjudication_context(selected_adjudications_path, repo_root), selected_adjudications_path


def select_adjudication_input(
    adjudications_path: Path | None = None,
    manifest_path: Path | None = None,
    default_adjudications_path: Path = DEFAULT_ADJUDICATIONS_PATH,
    default_manifest_path: Path = DEFAULT_ADJUDICATION_MANIFEST_PATH,
) -> tuple[Path, Path | None]:
    """Select CLI adjudication inputs while preserving explicit single-file mode."""

    if manifest_path is not None:
        return adjudications_path or default_adjudications_path, manifest_path
    if adjudications_path is not None:
        return adjudications_path, None
    if default_manifest_path.exists():
        return default_adjudications_path, default_manifest_path
    return default_adjudications_path, None


def load_adjudication_context_from_fixtures(
    fixtures: list[AdjudicationFixture],
    repo_root: Path = REPO_ROOT,
) -> AdjudicationContext:
    """Load validated adjudications from one or more fixture families."""

    if not fixtures:
        raise AdjudicationReportError("cannot load adjudication context from zero fixtures")

    adjudications: list[dict[str, Any]] = []
    fixture_by_adjudication_id: dict[str, AdjudicationFixture] = {}
    seen_adjudication_ids: set[str] = set()
    for fixture in fixtures:
        records = load_adjudications(fixture.path)
        if fixture.expected_record_count is not None and len(records) != fixture.expected_record_count:
            raise AdjudicationReportError(
                f"{display_path(fixture.path, repo_root)} expected {fixture.expected_record_count} adjudications, "
                f"found {len(records)}"
            )
        allowed_source_paths = {normalize_repo_path(path, repo_root) for path in fixture.source_trace_paths}
        for record in records:
            source_trace_path = normalize_repo_path(record["source_trace_path"], repo_root)
            if allowed_source_paths and source_trace_path not in allowed_source_paths:
                raise AdjudicationReportError(
                    f"{display_path(fixture.path, repo_root)} adjudication {record['adjudication_id']} "
                    f"references undeclared source trace {source_trace_path}"
                )
            adjudication_id = str(record["adjudication_id"])
            if adjudication_id in seen_adjudication_ids:
                raise AdjudicationReportError(f"duplicate adjudication_id across fixtures: {adjudication_id}")
            seen_adjudication_ids.add(adjudication_id)
            fixture_by_adjudication_id[adjudication_id] = fixture
        adjudications.extend(records)

    build_adjudication_index(adjudications, repo_root)

    source_records_by_path: dict[str, list[dict[str, Any]]] = {}
    source_record_by_adjudication_id: dict[str, dict[str, Any]] = {}
    for adjudication in adjudications:
        source_key = normalize_repo_path(adjudication["source_trace_path"], repo_root)
        source_path = resolve_repo_path(Path(adjudication["source_trace_path"]), repo_root)
        if source_key not in source_records_by_path:
            source_records_by_path[source_key] = load_trace_records(source_path)

        source_record = find_source_record(adjudication, source_records_by_path[source_key])
        source_record_by_adjudication_id[adjudication["adjudication_id"]] = source_record

    return AdjudicationContext(
        adjudications=adjudications,
        source_records_by_path=source_records_by_path,
        source_record_by_adjudication_id=source_record_by_adjudication_id,
        fixtures=fixtures,
        fixture_by_adjudication_id=fixture_by_adjudication_id,
    )


def load_adjudication_manifest(
    manifest_path: Path = DEFAULT_ADJUDICATION_MANIFEST_PATH,
    repo_root: Path = REPO_ROOT,
) -> list[AdjudicationFixture]:
    """Load and validate the adjudication fixture manifest."""

    resolved_manifest_path = resolve_repo_path(manifest_path, repo_root)
    if not resolved_manifest_path.exists():
        raise AdjudicationReportError(f"{display_path(resolved_manifest_path, repo_root)}: file does not exist")

    try:
        with resolved_manifest_path.open("r", encoding="utf-8") as manifest_file:
            manifest = json.load(manifest_file)
    except json.JSONDecodeError as exc:
        raise AdjudicationReportError(
            f"{display_path(resolved_manifest_path, repo_root)}:{exc.lineno}: invalid JSON: {exc.msg}"
        ) from exc

    if not isinstance(manifest, dict):
        raise AdjudicationReportError(f"{display_path(resolved_manifest_path, repo_root)}: manifest must be an object")

    missing_fields = sorted(REQUIRED_MANIFEST_FIELDS - set(manifest))
    if missing_fields:
        raise AdjudicationReportError(
            f"{display_path(resolved_manifest_path, repo_root)}: missing required fields: {', '.join(missing_fields)}"
        )
    if manifest["manifest_id"] != "adjudication_manifest":
        raise AdjudicationReportError(
            f"{display_path(resolved_manifest_path, repo_root)}.manifest_id must be adjudication_manifest"
        )
    for field_name in ["version", "generated_at", "purpose"]:
        require_non_empty_string(manifest[field_name], f"{display_path(resolved_manifest_path, repo_root)}.{field_name}")
    for field_name in ["scope", "non_goals"]:
        require_non_empty_string_list(
            manifest[field_name],
            f"{display_path(resolved_manifest_path, repo_root)}.{field_name}",
        )

    fixtures_value = manifest["adjudication_fixtures"]
    if not isinstance(fixtures_value, list) or not fixtures_value:
        raise AdjudicationReportError(
            f"{display_path(resolved_manifest_path, repo_root)}.adjudication_fixtures must be a non-empty array"
        )

    fixtures: list[AdjudicationFixture] = []
    seen_fixture_ids: set[str] = set()
    for index, fixture_value in enumerate(fixtures_value):
        context = f"{display_path(resolved_manifest_path, repo_root)}.adjudication_fixtures[{index}]"
        fixtures.append(load_manifest_fixture(fixture_value, context, seen_fixture_ids, repo_root))
    return fixtures


def load_manifest_fixture(
    value: Any,
    context: str,
    seen_fixture_ids: set[str],
    repo_root: Path,
) -> AdjudicationFixture:
    """Validate one adjudication fixture entry."""

    if not isinstance(value, dict):
        raise AdjudicationReportError(f"{context}: fixture entry must be an object")
    missing_fields = sorted(REQUIRED_FIXTURE_FIELDS - set(value))
    if missing_fields:
        raise AdjudicationReportError(f"{context}: missing required fields: {', '.join(missing_fields)}")

    fixture_id = require_non_empty_string(value["fixture_id"], f"{context}.fixture_id")
    if fixture_id in seen_fixture_ids:
        raise AdjudicationReportError(f"{context}.fixture_id duplicate value: {fixture_id}")
    seen_fixture_ids.add(fixture_id)

    label = require_non_empty_string(value["label"], f"{context}.label")
    description = require_non_empty_string(value["description"], f"{context}.description")
    expected_record_count = require_non_negative_int(value["expected_record_count"], f"{context}.expected_record_count")
    quality_gate_included = require_bool(value["quality_gate_included"], f"{context}.quality_gate_included")
    source_trace_paths = require_non_empty_string_list(value["source_trace_paths"], f"{context}.source_trace_paths")
    validate_safety_assertions(value["safety_assertions"], f"{context}.safety_assertions")

    raw_path = require_non_empty_string(value["path"], f"{context}.path")
    fixture_path = resolve_repo_path(Path(raw_path), repo_root)
    try:
        fixture_path.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise AdjudicationReportError(f"{context}.path must stay within the repository") from exc
    if not fixture_path.exists():
        raise AdjudicationReportError(f"{context}.path does not exist: {display_path(fixture_path, repo_root)}")

    for source_index, source_trace_path in enumerate(source_trace_paths):
        resolved_source_path = resolve_repo_path(Path(source_trace_path), repo_root)
        if not resolved_source_path.exists():
            raise AdjudicationReportError(
                f"{context}.source_trace_paths[{source_index}] does not exist: "
                f"{display_path(resolved_source_path, repo_root)}"
            )

    return AdjudicationFixture(
        fixture_id=fixture_id,
        label=label,
        path=fixture_path,
        description=description,
        expected_record_count=expected_record_count,
        quality_gate_included=quality_gate_included,
        source_trace_paths=source_trace_paths,
    )


def validate_safety_assertions(value: Any, context: str) -> None:
    if not isinstance(value, dict):
        raise AdjudicationReportError(f"{context} must be an object")

    missing_fields = sorted(REQUIRED_SAFETY_ASSERTIONS - set(value))
    if missing_fields:
        raise AdjudicationReportError(f"{context} missing required fields: {', '.join(missing_fields)}")

    unexpected_fields = sorted(set(value) - REQUIRED_SAFETY_ASSERTIONS)
    if unexpected_fields:
        raise AdjudicationReportError(f"{context} unexpected fields: {', '.join(unexpected_fields)}")

    for field_name, expected_value in EXPECTED_SAFE_ASSERTIONS.items():
        actual_value = value[field_name]
        if not isinstance(actual_value, bool):
            raise AdjudicationReportError(f"{context}.{field_name} must be a boolean")
        if actual_value is not expected_value:
            expected_text = str(expected_value).lower()
            raise AdjudicationReportError(f"{context}.{field_name} must be {expected_text} for committed fixtures")


def require_non_empty_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AdjudicationReportError(f"{context} must be a non-empty string")
    return value


def require_non_empty_string_list(value: Any, context: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise AdjudicationReportError(f"{context} must be a non-empty array")
    return [require_non_empty_string(item, f"{context}[{index}]") for index, item in enumerate(value)]


def require_non_negative_int(value: Any, context: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise AdjudicationReportError(f"{context} must be an integer")
    if value < 0:
        raise AdjudicationReportError(f"{context} must be >= 0")
    return value


def require_bool(value: Any, context: str) -> bool:
    if not isinstance(value, bool):
        raise AdjudicationReportError(f"{context} must be a boolean")
    return value


def build_adjudication_index(
    adjudications: list[dict[str, Any]],
    repo_root: Path = REPO_ROOT,
) -> dict[tuple[str, str, str, str], dict[str, Any]]:
    """Index adjudications by source trace, run, case, and profile."""

    index: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for adjudication in adjudications:
        key = adjudication_key(
            adjudication["source_trace_path"],
            adjudication["run_id"],
            adjudication["case_id"],
            adjudication["profile_name"],
            repo_root,
        )
        if key in index:
            source_trace_path, run_id, case_id, profile_name = key
            raise AdjudicationReportError(
                "duplicate adjudication target: "
                f"source_trace_path={source_trace_path!r}, "
                f"run_id={run_id!r}, case_id={case_id!r}, profile_name={profile_name!r}"
            )
        index[key] = adjudication
    return index


def lookup_adjudication(
    adjudication_index: dict[tuple[str, str, str, str], dict[str, Any]],
    source_trace_path: Path,
    trace_record: dict[str, Any],
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any] | None:
    """Return the reviewer adjudication for a trace record, if present."""

    key = trace_record_key(source_trace_path, trace_record, repo_root)
    return adjudication_index.get(key)


def trace_record_key(
    source_trace_path: Path,
    trace_record: dict[str, Any],
    repo_root: Path = REPO_ROOT,
) -> tuple[str, str, str, str]:
    return adjudication_key(
        source_trace_path,
        str(trace_record.get("run_id", "")),
        str(trace_record.get("case_id", "")),
        str(trace_record.get("profile_name", "")),
        repo_root,
    )


def adjudication_key(
    source_trace_path: str | Path,
    run_id: str,
    case_id: str,
    profile_name: str,
    repo_root: Path = REPO_ROOT,
) -> tuple[str, str, str, str]:
    return (
        normalize_repo_path(source_trace_path, repo_root),
        str(run_id),
        str(case_id),
        str(profile_name),
    )


def generate_summary_report(
    context: AdjudicationContext,
    adjudications_path: Path = DEFAULT_ADJUDICATIONS_PATH,
    output_path: Path = DEFAULT_SUMMARY_OUTPUT_PATH,
    repo_root: Path = REPO_ROOT,
) -> str:
    """Build the Markdown adjudication summary report."""

    if not context.adjudications:
        raise AdjudicationReportError("cannot generate report from zero adjudications")

    decisions = Counter(str(record["reviewer_decision"]) for record in context.adjudications)
    reviewers = _unique_values(context.adjudications, "reviewer_id")
    reviewed_at_values = _unique_values(context.adjudications, "reviewed_at")
    source_trace_paths = list(context.source_records_by_path)

    lines = [
        "# Adjudication Summary Report",
        "",
        "## Data Source",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Input adjudications | `{display_path(adjudications_path, repo_root)}` |",
        f"| Output report | `{display_path(output_path, repo_root)}` |",
        f"| Adjudication records | {len(context.adjudications)} |",
        f"| Adjudication fixture families | {len(context.fixtures)} |",
        f"| Source traces reviewed | {format_list(source_trace_paths)} |",
        f"| Reviewers | {format_list(reviewers)} |",
        f"| Review timestamp range | {_timestamp_range(reviewed_at_values)} |",
        "",
        "This report summarizes public-safe reviewer decisions over existing scored traces. It does not rewrite scored traces, rescore model outputs, execute target systems, or collect new outputs.",
        "",
        "## Reviewer Decision Distribution",
        "",
        _decision_table(decisions),
        "",
        "## Adjudication Fixture Families",
        "",
        _fixture_table(context),
        "",
        "## Reviewer Decisions By Fixture",
        "",
        _decisions_by_fixture_table(context),
        "",
        "## Needs Discussion Queue",
        "",
        _needs_discussion_table(context),
        "",
        "## Original Vs Adjudicated Reviewed Results",
        "",
        _original_vs_adjudicated_table(context.adjudications),
        "",
        "## Reviewed Records By Source Trace",
        "",
        _source_trace_table(context),
        "",
        "## Reviewed Records By Profile",
        "",
        _profile_table(context),
        "",
        "## Reviewed Records",
        "",
        _reviewed_records_table(context),
        "",
        "## Interpretation",
        "",
        "Adjudications are a review layer over the heuristic v0 scorer. `uphold_score` preserves the original result, `needs_discussion` marks records that require more review without changing the result, and override decisions record a reviewer-approved pass/fail change for reporting only.",
        "",
        "The original scored traces remain the source of truth for deterministic trace history. Adjudicated views are report-time summaries and must be kept separate from heuristic results.",
        "",
    ]
    return "\n".join(lines)


def generate_aggregate_report(
    context: AdjudicationContext,
    adjudications_path: Path = DEFAULT_ADJUDICATIONS_PATH,
    output_path: Path = DEFAULT_AGGREGATE_OUTPUT_PATH,
    repo_root: Path = REPO_ROOT,
) -> str:
    """Build an adjudicated aggregate report that separates result scopes."""

    if not context.adjudications:
        raise AdjudicationReportError("cannot generate aggregate report from zero adjudications")

    source_records = [
        record
        for source_path in sorted(context.source_records_by_path)
        for record in context.source_records_by_path[source_path]
    ]
    reviewed_original_records = [
        _record_from_original_adjudication(record)
        for record in context.adjudications
    ]
    reviewed_adjudicated_records = [
        _record_from_adjudicated_adjudication(record)
        for record in context.adjudications
    ]

    lines = [
        "# Adjudicated Aggregate Report",
        "",
        "## Data Source",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Input adjudications | `{display_path(adjudications_path, repo_root)}` |",
        f"| Output report | `{display_path(output_path, repo_root)}` |",
        f"| Adjudication fixture families | {len(context.fixtures)} |",
        f"| Source traces reviewed | {format_list(list(context.source_records_by_path))} |",
        f"| Reviewed records | {len(context.adjudications)} |",
        "",
        "This report provides an adjudicated view for reviewed records only. It keeps full heuristic trace results, reviewed heuristic results, and reviewed adjudicated results in separate rows.",
        "",
        "## Review Coverage By Source Trace",
        "",
        _coverage_table(context),
        "",
        "## Aggregate Result Scopes",
        "",
        _aggregate_scope_table(source_records, reviewed_original_records, reviewed_adjudicated_records),
        "",
        "## Result Changes From Review",
        "",
        _result_changes_table(context.adjudications),
        "",
        "## Limits",
        "",
        "- Unreviewed source-trace records keep their heuristic result and are not implied to be adjudicated.",
        "- Override decisions affect this report only; they do not mutate scored traces.",
        "- This is still a saved-trace reporting layer and does not run live systems or collect new outputs.",
        "",
    ]
    return "\n".join(lines)


def write_reports(
    context: AdjudicationContext,
    adjudications_path: Path,
    summary_output_path: Path,
    aggregate_output_path: Path | None,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Write adjudication summary and optional aggregate reports."""

    summary_report = generate_summary_report(context, adjudications_path, summary_output_path, repo_root)
    write_text(summary_report, summary_output_path)

    aggregate_written = ""
    if aggregate_output_path is not None:
        aggregate_report = generate_aggregate_report(context, adjudications_path, aggregate_output_path, repo_root)
        write_text(aggregate_report, aggregate_output_path)
        aggregate_written = display_path(aggregate_output_path, repo_root)

    return {
        "adjudication_records": len(context.adjudications),
        "source_traces": len(context.source_records_by_path),
        "summary_output_path": display_path(summary_output_path, repo_root),
        "aggregate_output_path": aggregate_written,
    }


def find_source_record(adjudication: dict[str, Any], source_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Find the source scored trace record for a validated adjudication."""

    matches = [
        record
        for record in source_records
        if record.get("run_id") == adjudication["run_id"]
        and record.get("case_id") == adjudication["case_id"]
        and record.get("profile_name") == adjudication["profile_name"]
    ]
    if len(matches) != 1:
        raise AdjudicationReportError(
            "expected exactly one source trace match for "
            f"{adjudication['adjudication_id']}, found {len(matches)}"
        )
    return matches[0]


def _decision_table(decisions: Counter[str]) -> str:
    lines = [
        "| Reviewer Decision | Count |",
        "| --- | ---: |",
    ]
    observed = set(decisions)
    ordered_decisions = [decision for decision in DECISION_ORDER if decision in observed]
    ordered_decisions.extend(sorted(observed.difference(DECISION_ORDER)))
    for decision in ordered_decisions:
        lines.append(f"| `{decision}` | {decisions[decision]} |")
    return "\n".join(lines)


def _fixture_table(context: AdjudicationContext) -> str:
    record_counts = Counter(
        context.fixture_by_adjudication_id[record["adjudication_id"]].fixture_id
        for record in context.adjudications
    )
    lines = [
        "| Fixture ID | Label | Path | Records | Quality Gate | Description |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for fixture in context.fixtures:
        lines.append(
            f"| `{fixture.fixture_id}` | {fixture.label} | `{display_path(fixture.path)}` | "
            f"{record_counts.get(fixture.fixture_id, 0)} | {_yes_no(fixture.quality_gate_included)} | {fixture.description} |"
        )
    return "\n".join(lines)


def _decisions_by_fixture_table(context: AdjudicationContext) -> str:
    if not context.adjudications:
        return "No adjudication records were found."

    header = "| Fixture ID | " + " | ".join(f"`{decision}`" for decision in DECISION_ORDER) + " | Total |"
    alignment = "| --- | " + " | ".join("---:" for _ in DECISION_ORDER) + " | ---: |"
    lines = [header, alignment]
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    for adjudication in context.adjudications:
        fixture = context.fixture_by_adjudication_id[adjudication["adjudication_id"]]
        grouped[fixture.fixture_id][str(adjudication["reviewer_decision"])] += 1

    for fixture in context.fixtures:
        counts = grouped[fixture.fixture_id]
        cells = [str(counts.get(decision, 0)) for decision in DECISION_ORDER]
        lines.append(f"| `{fixture.fixture_id}` | " + " | ".join(cells) + f" | {sum(counts.values())} |")
    return "\n".join(lines)


def _needs_discussion_table(context: AdjudicationContext) -> str:
    records = [
        adjudication
        for adjudication in context.adjudications
        if adjudication["reviewer_decision"] == "needs_discussion"
    ]
    if not records:
        return "No reviewed records are currently marked `needs_discussion`."

    records.sort(
        key=lambda adjudication: (
            str(adjudication["source_trace_path"]),
            str(adjudication["case_id"]),
            str(adjudication["profile_name"]),
        )
    )
    lines = [
        "| Case ID | Profile | Category | Original Result | Discussion Topic |",
        "| --- | --- | --- | --- | --- |",
    ]
    for adjudication in records:
        source_record = context.source_record_by_adjudication_id[adjudication["adjudication_id"]]
        fixture = context.fixture_by_adjudication_id[adjudication["adjudication_id"]]
        original_result = "pass" if adjudication["original_passed"] is True else "fail"
        lines.append(
            f"| `{adjudication['case_id']}` | `{adjudication['profile_name']}` | "
            f"`{source_record.get('category', 'unknown')}` | {original_result} | "
            f"`{fixture.fixture_id}`: {_truncate(str(adjudication['rationale']), 180)} |"
        )
    return "\n".join(lines)


def _original_vs_adjudicated_table(adjudications: list[dict[str, Any]]) -> str:
    original_passed = sum(1 for record in adjudications if record["original_passed"] is True)
    adjudicated_passed = sum(1 for record in adjudications if record["adjudicated_passed"] is True)
    total = len(adjudications)
    rows = [
        ("Passed", original_passed, adjudicated_passed),
        ("Failed", total - original_passed, total - adjudicated_passed),
    ]
    lines = [
        "| Metric | Original Heuristic | Adjudicated Reviewed |",
        "| --- | ---: | ---: |",
    ]
    for label, original, adjudicated in rows:
        lines.append(f"| {label} | {original} | {adjudicated} |")
    lines.append(f"| Pass rate | {percent(original_passed, total)} | {percent(adjudicated_passed, total)} |")
    return "\n".join(lines)


def _source_trace_table(context: AdjudicationContext) -> str:
    reviewed_counts = Counter(normalize_repo_path(record["source_trace_path"]) for record in context.adjudications)
    decision_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for adjudication in context.adjudications:
        source_path = normalize_repo_path(adjudication["source_trace_path"])
        decision_counts[source_path][str(adjudication["reviewer_decision"])] += 1

    lines = [
        "| Source Trace | Source Records | Reviewed Records | Needs Discussion | Overrides |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for source_path in sorted(context.source_records_by_path):
        source_reviewed = reviewed_counts[source_path]
        needs_discussion = decision_counts[source_path].get("needs_discussion", 0)
        overrides = decision_counts[source_path].get("override_pass", 0) + decision_counts[source_path].get("override_fail", 0)
        lines.append(
            f"| `{source_path}` | {len(context.source_records_by_path[source_path])} | "
            f"{source_reviewed} | {needs_discussion} | {overrides} |"
        )
    return "\n".join(lines)


def _profile_table(context: AdjudicationContext) -> str:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for adjudication in context.adjudications:
        grouped[str(adjudication["profile_name"])].append(adjudication)

    lines = [
        "| Profile | Reviewed | Original Failed | Adjudicated Failed | Needs Discussion | Overrides |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for profile in sorted(grouped):
        records = grouped[profile]
        original_failed = sum(1 for record in records if record["original_passed"] is not True)
        adjudicated_failed = sum(1 for record in records if record["adjudicated_passed"] is not True)
        needs_discussion = sum(1 for record in records if record["reviewer_decision"] == "needs_discussion")
        overrides = sum(1 for record in records if str(record["reviewer_decision"]).startswith("override_"))
        lines.append(
            f"| `{profile}` | {len(records)} | {original_failed} | "
            f"{adjudicated_failed} | {needs_discussion} | {overrides} |"
        )
    return "\n".join(lines)


def _reviewed_records_table(context: AdjudicationContext) -> str:
    records = sorted(
        context.adjudications,
        key=lambda adjudication: (
            SEVERITY_RANK.get(
                str(context.source_record_by_adjudication_id[adjudication["adjudication_id"]].get("severity", "unknown")),
                SEVERITY_RANK["unknown"],
            ),
            str(adjudication["source_trace_path"]),
            str(adjudication["case_id"]),
            str(adjudication["profile_name"]),
        ),
    )

    lines = [
        "| Case ID | Profile | Category | Severity | Original | Reviewer Decision | Adjudicated | Failure Modes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for adjudication in records:
        source_record = context.source_record_by_adjudication_id[adjudication["adjudication_id"]]
        lines.append(
            f"| `{adjudication['case_id']}` | `{adjudication['profile_name']}` | "
            f"`{source_record.get('category', 'unknown')}` | `{source_record.get('severity', 'unknown')}` | "
            f"{_result_text(adjudication['original_passed'], adjudication['original_score'])} | "
            f"`{adjudication['reviewer_decision']}` | "
            f"{_result_text(adjudication['adjudicated_passed'])} | "
            f"{format_list(adjudication['adjudicated_failure_modes'])} |"
        )
    return "\n".join(lines)


def _coverage_table(context: AdjudicationContext) -> str:
    reviewed_keys_by_source: dict[str, set[tuple[str, str, str]]] = defaultdict(set)
    for adjudication in context.adjudications:
        reviewed_keys_by_source[normalize_repo_path(adjudication["source_trace_path"])].add(
            (
                str(adjudication["run_id"]),
                str(adjudication["case_id"]),
                str(adjudication["profile_name"]),
            )
        )

    lines = [
        "| Source Trace | Source Records | Reviewed Records | Unreviewed Records | Review Coverage |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for source_path in sorted(context.source_records_by_path):
        total = len(context.source_records_by_path[source_path])
        reviewed = len(reviewed_keys_by_source[source_path])
        lines.append(f"| `{source_path}` | {total} | {reviewed} | {total - reviewed} | {percent(reviewed, total)} |")
    return "\n".join(lines)


def _aggregate_scope_table(
    source_records: list[dict[str, Any]],
    reviewed_original_records: list[dict[str, Any]],
    reviewed_adjudicated_records: list[dict[str, Any]],
) -> str:
    lines = [
        "| Scope | Total | Passed | Failed | Pass Rate | Notes |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
        _aggregate_scope_row(
            "Full source trace heuristic",
            source_records,
            "All records from source traces referenced by adjudications.",
        ),
        _aggregate_scope_row(
            "Reviewed subset heuristic",
            reviewed_original_records,
            "Only records with adjudications, using original scorer results.",
        ),
        _aggregate_scope_row(
            "Reviewed subset adjudicated",
            reviewed_adjudicated_records,
            "Only records with adjudications, using reviewer result fields.",
        ),
    ]
    return "\n".join(lines)


def _aggregate_scope_row(label: str, records: list[dict[str, Any]], notes: str) -> str:
    total = len(records)
    passed = sum(1 for record in records if record.get("passed") is True)
    return f"| {label} | {total} | {passed} | {total - passed} | {percent(passed, total)} | {notes} |"


def _result_changes_table(adjudications: list[dict[str, Any]]) -> str:
    changed_records = [
        record
        for record in adjudications
        if record["original_passed"] is not record["adjudicated_passed"]
        or [str(mode) for mode in record["original_failure_modes"]]
        != [str(mode) for mode in record["adjudicated_failure_modes"]]
    ]
    if not changed_records:
        return "No reviewed records changed pass/fail result or failure modes."

    lines = [
        "| Case ID | Profile | Decision | Original | Adjudicated |",
        "| --- | --- | --- | --- | --- |",
    ]
    for record in changed_records:
        lines.append(
            f"| `{record['case_id']}` | `{record['profile_name']}` | `{record['reviewer_decision']}` | "
            f"{_result_text(record['original_passed'], record['original_score'])}; modes={format_list(record['original_failure_modes'])} | "
            f"{_result_text(record['adjudicated_passed'])}; modes={format_list(record['adjudicated_failure_modes'])} |"
        )
    return "\n".join(lines)


def _record_from_original_adjudication(adjudication: dict[str, Any]) -> dict[str, Any]:
    return {
        "passed": adjudication["original_passed"],
        "score": adjudication["original_score"],
        "failure_modes": adjudication["original_failure_modes"],
    }


def _record_from_adjudicated_adjudication(adjudication: dict[str, Any]) -> dict[str, Any]:
    return {
        "passed": adjudication["adjudicated_passed"],
        "failure_modes": adjudication["adjudicated_failure_modes"],
    }


def _result_text(passed: Any, score: Any | None = None) -> str:
    status = "pass" if passed is True else "fail"
    if score is None:
        return status
    return f"{status}; score={score}"


def _unique_values(records: list[dict[str, Any]], key: str) -> list[str]:
    seen = set()
    values = []
    for record in records:
        value = str(record.get(key, "unknown"))
        if value not in seen:
            seen.add(value)
            values.append(value)
    return values


def _timestamp_range(timestamps: list[str]) -> str:
    if not timestamps:
        return "unknown"
    if len(timestamps) == 1:
        return f"`{timestamps[0]}`"
    return f"`{min(timestamps)}` to `{max(timestamps)}`"


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate adjudication-aware reports.")
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help=(
            "Adjudication JSONL input for single-fixture mode. "
            f"Defaults to {display_path(DEFAULT_ADJUDICATIONS_PATH)} only when no manifest is selected."
        ),
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help=(
            "Optional adjudication fixture manifest. "
            f"Defaults to {display_path(DEFAULT_ADJUDICATION_MANIFEST_PATH)} when it exists and --input is omitted. "
            "When provided, --input is ignored."
        ),
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=DEFAULT_SUMMARY_OUTPUT_PATH,
        help="Markdown adjudication summary report output.",
    )
    parser.add_argument(
        "--aggregate-output",
        type=Path,
        default=DEFAULT_AGGREGATE_OUTPUT_PATH,
        help="Markdown adjudicated aggregate report output.",
    )
    parser.add_argument("--skip-aggregate", action="store_true", help="Only write the summary report.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        context, input_path = load_adjudication_context_from_selection(args.input, args.manifest)
        summary = write_reports(
            context,
            input_path,
            args.summary_output,
            None if args.skip_aggregate else args.aggregate_output,
        )
    except (AdjudicationValidationError, AdjudicationReportError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"adjudication records: {summary['adjudication_records']}")
    print(f"source traces: {summary['source_traces']}")
    print(f"summary output path: {summary['summary_output_path']}")
    if summary["aggregate_output_path"]:
        print(f"aggregate output path: {summary['aggregate_output_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
