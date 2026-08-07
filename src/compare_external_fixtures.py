"""Generate a deterministic comparison report for controlled external fixtures.

This report reads already-scored traces from saved-output fixture paths. It
does not rescore outputs, call providers, run local models, execute OpenClaw,
or perform external actions.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from reporting_utils import atomic_write_text
from validate_schemas import ValidationError, validate_trace_record


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "traces/external/fixture_manifest.json"
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
    source_path: Path
    source_kind: str
    source_type: str
    provenance_class: str
    data_classification: str
    quality_gate_included: bool
    description: str


@dataclass(frozen=True)
class FixtureManifest:
    path: Path
    generated_at: str
    sources: list[FixtureSource]


class ExternalFixtureComparisonError(Exception):
    """Comparison report generation error."""


def load_fixture_manifest(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    repo_root: Path = REPO_ROOT,
) -> FixtureManifest:
    """Load fixture source metadata from the external fixture manifest."""

    resolved_manifest_path = resolve_repo_path(manifest_path, repo_root)
    if not resolved_manifest_path.exists():
        raise ExternalFixtureComparisonError(f"missing fixture manifest: {_display_path(resolved_manifest_path, repo_root)}")

    try:
        with resolved_manifest_path.open("r", encoding="utf-8") as manifest_file:
            manifest = json.load(manifest_file)
    except json.JSONDecodeError as exc:
        raise ExternalFixtureComparisonError(
            f"{_display_path(resolved_manifest_path, repo_root)}:{exc.lineno}: invalid JSON: {exc.msg}"
        ) from exc

    if not isinstance(manifest, dict):
        raise ExternalFixtureComparisonError(f"{_display_path(resolved_manifest_path, repo_root)}: manifest must be an object")

    fixtures = manifest.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise ExternalFixtureComparisonError("fixture manifest must contain at least one fixture")

    generated_at = str(manifest.get("generated_at", GENERATED_AT))
    sources = [
        fixture_source_from_manifest_entry(fixture, index, resolved_manifest_path, repo_root)
        for index, fixture in enumerate(fixtures)
    ]
    return FixtureManifest(path=resolved_manifest_path, generated_at=generated_at, sources=sources)


def fixture_source_from_manifest_entry(
    fixture: Any,
    index: int,
    manifest_path: Path,
    repo_root: Path = REPO_ROOT,
) -> FixtureSource:
    """Build a report source from one manifest fixture entry."""

    context = f"{_display_path(manifest_path, repo_root)}:fixtures[{index}]"
    if not isinstance(fixture, dict):
        raise ExternalFixtureComparisonError(f"{context}: fixture entry must be an object")

    fixture_id = require_manifest_string(fixture, "fixture_id", context)
    scored_trace_path = resolve_repo_path(Path(require_manifest_string(fixture, "scored_trace_path", context)), repo_root)
    source_path = resolve_repo_path(Path(require_manifest_string(fixture, "source_path", context)), repo_root)
    quality_gate_included = fixture.get("quality_gate_included")
    if not isinstance(quality_gate_included, bool):
        raise ExternalFixtureComparisonError(f"{context}.quality_gate_included must be a boolean")

    return FixtureSource(
        key=fixture_id,
        label=fixture_label(fixture_id),
        path=scored_trace_path,
        source_path=source_path,
        source_kind=require_manifest_string(fixture, "source_kind", context),
        source_type=require_manifest_string(fixture, "source_type", context),
        provenance_class=require_manifest_string(fixture, "provenance_class", context),
        data_classification=require_manifest_string(fixture, "data_classification", context),
        quality_gate_included=quality_gate_included,
        description=require_manifest_string(fixture, "notes", context),
    )


def require_manifest_string(fixture: dict[str, Any], field_name: str, context: str) -> str:
    value = fixture.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ExternalFixtureComparisonError(f"{context}.{field_name} must be a non-empty string")
    return value


def resolve_repo_path(path: Path, repo_root: Path = REPO_ROOT) -> Path:
    if path.is_absolute():
        resolved = path.resolve()
    else:
        resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise ExternalFixtureComparisonError(f"{path} must stay within the repository") from exc
    return resolved


def fixture_label(fixture_id: str) -> str:
    return " ".join(part.capitalize() for part in fixture_id.split("_"))


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


def load_all_sources(manifest: FixtureManifest | None = None) -> dict[str, list[dict[str, Any]]]:
    """Load all configured external scored fixture sources."""

    resolved_manifest = manifest or load_fixture_manifest()
    return {source.key: load_source_records(source) for source in resolved_manifest.sources}


def generate_report(source_records: dict[str, list[dict[str, Any]]], manifest: FixtureManifest | None = None) -> str:
    """Build the external fixture comparison Markdown report."""

    resolved_manifest = manifest or load_fixture_manifest()
    fixture_sources = resolved_manifest.sources
    if set(source_records) != {source.key for source in fixture_sources}:
        raise ExternalFixtureComparisonError("loaded source keys do not match configured fixture sources")

    all_records = [record for source in fixture_sources for record in source_records[source.key]]
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
        f"| Manifest | `{_display_path(resolved_manifest.path)}` |",
        f"| Manifest generated timestamp | `{resolved_manifest.generated_at}` |",
        f"| Output report | `{_display_path(OUTPUT_PATH)}` |",
        f"| Source groups compared | {len(fixture_sources)} |",
        f"| Total scored records compared | {len(all_records)} |",
        "",
        "This is a controlled saved-output fixture comparison driven by `traces/external/fixture_manifest.json`, not live benchmark execution. It reads already-scored traces from public-safe fixtures and summarizes the existing scoring results.",
        "",
        "No real provider APIs, local model runtimes, live OpenClaw execution, browser tools, email tools, external actions, credentials, SDKs, network calls, or private runtime integrations are involved.",
        "",
        "## Source Groups",
        "",
        _source_groups_table(source_records, fixture_sources),
        "",
        "## Pass / Fail And Average Score By Source",
        "",
        _source_summary_table(source_records, fixture_sources),
        "",
        "## Failure Mode Distribution By Source",
        "",
        _source_distribution_table(source_records, fixture_sources, "failure_modes", failure_modes, "Failure Mode"),
        "",
        "## Severity Distribution By Source",
        "",
        _source_distribution_table(source_records, fixture_sources, "severity", severities, "Severity"),
        "",
        "## Category Distribution By Source",
        "",
        _source_distribution_table(source_records, fixture_sources, "category", categories, "Category"),
        "",
        "## Notable Failures",
        "",
        _notable_failures(source_records, fixture_sources),
        "",
        "## Interpretation",
        "",
        "These fixture groups exercise the evaluator boundary from the saved-output families listed in the fixture manifest. The comparison helps identify which source groups produce approval-gate, refusal, uncertainty, fake-completion, or unsupported-claim signals under the existing scorer.",
        "",
        "The report does not rank live systems. Differences between source groups reflect the small public-safe fixtures currently present in the repository and the deterministic v0 scorer behavior already captured in the scored traces.",
        "",
        "## Limitations",
        "",
        "- Inputs are already-scored local fixtures; this report does not rerun scoring or collect new outputs.",
        "- Source groups have small and uneven record counts, so pass rates are useful for fixture review, not benchmark claims.",
        "- The sanitized OpenClaw-style groups are public-safe sample data and are not evidence from a live OpenClaw runtime.",
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
    """Write the comparison report to the intended deterministic path atomically."""

    atomic_write_text(content, OUTPUT_PATH)


def print_summary(source_records: dict[str, list[dict[str, Any]]], manifest: FixtureManifest) -> None:
    """Print a concise deterministic CLI summary."""

    total = sum(len(records) for records in source_records.values())
    failed = sum(1 for records in source_records.values() for record in records if record.get("passed") is not True)

    print(f"manifest path: {_display_path(manifest.path)}")
    print(f"source groups compared: {len(manifest.sources)}")
    print(f"total scored records compared: {total}")
    print(f"failed records: {failed}")
    print(f"output path: {_display_path(OUTPUT_PATH)}")


def _source_groups_table(source_records: dict[str, list[dict[str, Any]]], fixture_sources: list[FixtureSource]) -> str:
    lines = [
        "| Source Group | Fixture ID | Scored Trace | Source Fixture | Quality Gate | Records | Run IDs | Description |",
        "| --- | --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for source in fixture_sources:
        records = source_records[source.key]
        lines.append(
            f"| {source.label} | `{source.key}` | `{_display_path(source.path)}` | "
            f"`{_display_path(source.source_path)}` | {_yes_no(source.quality_gate_included)} | {len(records)} | "
            f"{_format_list(_unique_values(records, 'run_id'))} | {source.description} |"
        )
    return "\n".join(lines)


def _source_summary_table(source_records: dict[str, list[dict[str, Any]]], fixture_sources: list[FixtureSource]) -> str:
    lines = [
        "| Source Group | Total Records | Passed | Failed | Pass Rate | Average Score |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for source in fixture_sources:
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
    fixture_sources: list[FixtureSource],
    key: str,
    values: list[str],
    label: str,
) -> str:
    if not values:
        return f"No {label.lower()} values were recorded."

    header = "| Source Group | " + " | ".join(f"`{value}`" for value in values) + " |"
    alignment = "| --- | " + " | ".join("---:" for _ in values) + " |"
    lines = [header, alignment]

    for source in fixture_sources:
        records = source_records[source.key]
        if key == "failure_modes":
            counts = _failure_mode_counts(records)
        else:
            counts = Counter(str(record.get(key, "unknown")) for record in records)
        cells = [str(counts.get(value, 0)) for value in values]
        lines.append(f"| {source.label} | " + " | ".join(cells) + " |")

    return "\n".join(lines)


def _notable_failures(
    source_records: dict[str, list[dict[str, Any]]],
    fixture_sources: list[FixtureSource],
    limit: int = 8,
) -> str:
    failures = []
    source_rank = {source.key: index for index, source in enumerate(fixture_sources)}
    source_labels = {source.key: source.label for source in fixture_sources}

    for source in fixture_sources:
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


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _display_path(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def main() -> int:
    try:
        manifest = load_fixture_manifest()
        source_records = load_all_sources(manifest)
        report = generate_report(source_records, manifest)
        write_report(report)
    except (ExternalFixtureComparisonError, OSError, ValueError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1

    print_summary(source_records, manifest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
