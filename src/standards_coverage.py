"""Generate and validate public case-to-standards coverage.

This module reads committed public-safe cases and standards catalogs, expands
case mapping groups, and writes deterministic coverage reports. It does not
claim compliance, call networks, execute models, use credentials, or inspect
private evidence.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from reporting_utils import display_path, load_json_object, load_jsonl_records, write_json_object, write_text
from schema_validation_utils import load_json_object as load_schema_json_object
from schema_validation_utils import validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATHS = [
    REPO_ROOT / "standards/owasp_llm_top_10.json",
    REPO_ROOT / "standards/owasp_agentic.json",
    REPO_ROOT / "standards/nist_ai_rmf.json",
    REPO_ROOT / "standards/mitre_atlas.json",
]
MAPPING_PATH = REPO_ROOT / "standards/case_standard_mappings.json"
MAPPING_SCHEMA_PATH = REPO_ROOT / "schemas/case_standard_mappings.schema.json"
DEFAULT_SNAPSHOT_PATH = REPO_ROOT / "reports/comparisons/standards_coverage.json"
DEFAULT_REPORT_PATH = REPO_ROOT / "reports/comparisons/standards_coverage.md"


class StandardsCoverageError(Exception):
    """Standards coverage validation error."""


def load_public_cases(case_sources: list[str]) -> list[dict[str, Any]]:
    """Load public cases and attach source metadata."""

    cases: list[dict[str, Any]] = []
    seen_case_ids: set[str] = set()
    for source in case_sources:
        path = REPO_ROOT / source
        if not path.exists():
            raise StandardsCoverageError(f"case source does not exist: {source}")
        for record in load_jsonl_records(path):
            case_id = str(record["case_id"])
            if case_id in seen_case_ids:
                raise StandardsCoverageError(f"duplicate case_id in public case sources: {case_id}")
            seen_case_ids.add(case_id)
            record["_source_path"] = source
            cases.append(record)
    return cases


def load_catalog_index() -> tuple[dict[str, dict[str, Any]], set[tuple[str, str]]]:
    """Load standards catalogs and return catalog and control indexes."""

    catalogs: dict[str, dict[str, Any]] = {}
    control_index: set[tuple[str, str]] = set()
    for path in CATALOG_PATHS:
        catalog = load_json_object(path)
        catalog_id = str(catalog["catalog_id"])
        if catalog_id in catalogs:
            raise StandardsCoverageError(f"duplicate standards catalog_id: {catalog_id}")
        catalogs[catalog_id] = catalog
        for control in catalog["controls"]:
            control_index.add((catalog_id, str(control["control_id"])))
    return catalogs, control_index


def expand_mapping_group(group: dict[str, Any], cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return cases selected by a mapping group."""

    selectors = group["case_selectors"]
    prefixes = [str(prefix) for prefix in selectors.get("case_id_prefixes", [])]
    categories = set(str(category) for category in selectors.get("categories", []))
    risk_areas = set(str(risk_area) for risk_area in selectors.get("risk_areas", []))

    selected = []
    for case in cases:
        case_id = str(case["case_id"])
        category = str(case.get("category", ""))
        risk_area = str(case.get("risk_area", ""))
        if prefixes and any(case_id.startswith(prefix) for prefix in prefixes):
            selected.append(case)
            continue
        if categories and category in categories:
            selected.append(case)
            continue
        if risk_areas and risk_area in risk_areas:
            selected.append(case)
    return selected


def validate_standard_refs(group: dict[str, Any], control_index: set[tuple[str, str]]) -> None:
    """Validate a mapping group's standards references."""

    if not group.get("standards"):
        raise StandardsCoverageError(f"{group['group_id']}: standards must not be empty")
    for standard in group["standards"]:
        key = (str(standard["catalog_id"]), str(standard["control_id"]))
        if key not in control_index:
            raise StandardsCoverageError(f"{group['group_id']}: unknown standard reference {key[0]} {key[1]}")


def build_snapshot(
    *,
    mapping_path: Path = MAPPING_PATH,
    snapshot_path: Path = DEFAULT_SNAPSHOT_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> dict[str, Any]:
    """Build, validate, and write standards coverage artifacts."""

    mapping = load_json_object(mapping_path)
    mapping_schema = load_schema_json_object(
        MAPPING_SCHEMA_PATH,
        "case standard mappings schema",
        REPO_ROOT,
        StandardsCoverageError,
    )
    validate_schema_value(
        mapping,
        mapping_schema,
        display_path(mapping_path),
        mapping_path,
        REPO_ROOT,
        StandardsCoverageError,
    )
    catalogs, control_index = load_catalog_index()
    cases = load_public_cases(list(mapping["case_sources"]))

    coverage_by_case: dict[str, dict[str, Any]] = {
        str(case["case_id"]): {
            "case_id": str(case["case_id"]),
            "source_path": str(case["_source_path"]),
            "category": str(case.get("category", "")),
            "risk_area": str(case.get("risk_area", "")),
            "mapping_groups": [],
            "standards": [],
        }
        for case in cases
    }
    group_rows = []
    standards_counter: Counter[str] = Counter()

    for group in mapping["mapping_groups"]:
        validate_standard_refs(group, control_index)
        selected_cases = expand_mapping_group(group, cases)
        if not selected_cases:
            raise StandardsCoverageError(f"{group['group_id']}: mapping group selected no cases")
        standard_refs = [
            {
                "catalog_id": str(standard["catalog_id"]),
                "control_id": str(standard["control_id"]),
            }
            for standard in group["standards"]
        ]
        for case in selected_cases:
            row = coverage_by_case[str(case["case_id"])]
            row["mapping_groups"].append(str(group["group_id"]))
            row["standards"].extend(standard_refs)
            for standard in standard_refs:
                standards_counter[f"{standard['catalog_id']}:{standard['control_id']}"] += 1
        group_rows.append(
            {
                "group_id": str(group["group_id"]),
                "selected_case_count": len(selected_cases),
                "standards": standard_refs,
                "coverage_note": str(group["coverage_note"]),
            }
        )

    uncovered_case_ids = sorted(case_id for case_id, row in coverage_by_case.items() if not row["standards"])
    if uncovered_case_ids:
        raise StandardsCoverageError(f"unmapped public cases: {', '.join(uncovered_case_ids)}")

    for row in coverage_by_case.values():
        row["standards"] = dedupe_standards(row["standards"])
        row["mapping_groups"] = sorted(set(row["mapping_groups"]))

    snapshot = {
        "snapshot_id": "standards_coverage_v1",
        "version": "0.1.0",
        "generated_at": "2026-06-22T00:00:00Z",
        "status": "coverage_not_compliance",
        "mapping_path": display_path(mapping_path),
        "mapping_id": mapping["mapping_id"],
        "mapping_version": mapping["version"],
        "catalogs": [
            {
                "catalog_id": catalog_id,
                "version": catalog["version"],
                "title": catalog["title"],
                "source_url": catalog["source_url"],
                "control_count": len(catalog["controls"]),
            }
            for catalog_id, catalog in sorted(catalogs.items())
        ],
        "case_summary": summarize_cases(cases),
        "mapping_groups": group_rows,
        "standards_counts": dict(sorted(standards_counter.items())),
        "covered_case_count": len(coverage_by_case),
        "uncovered_case_count": 0,
        "case_coverage": list(sorted(coverage_by_case.values(), key=lambda row: row["case_id"])),
        "claim_boundary": [
            "Standards mapping is coverage evidence only.",
            "This report does not certify compliance with OWASP, NIST, MITRE, or any regulatory framework.",
            "This report does not prove production safety.",
        ],
        "safety_assertions": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
            "credentials_required": False,
        },
    }
    write_json_object(snapshot, snapshot_path)
    write_text(markdown_report(snapshot), report_path)
    return snapshot


def dedupe_standards(standards: list[dict[str, str]]) -> list[dict[str, str]]:
    """Dedupe standards while preserving deterministic order."""

    seen: set[tuple[str, str]] = set()
    deduped = []
    for standard in standards:
        key = (standard["catalog_id"], standard["control_id"])
        if key not in seen:
            seen.add(key)
            deduped.append(standard)
    return deduped


def summarize_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Return public case coverage summary."""

    by_source = Counter(str(case["_source_path"]) for case in cases)
    by_category = Counter(str(case.get("category", "")) for case in cases)
    by_risk_area = Counter(str(case.get("risk_area", "baseline_or_unspecified")) for case in cases)
    return {
        "total_cases": len(cases),
        "by_source": dict(sorted(by_source.items())),
        "by_category": dict(sorted(by_category.items())),
        "by_risk_area": dict(sorted(by_risk_area.items())),
    }


def markdown_report(snapshot: dict[str, Any]) -> str:
    """Build the Markdown standards coverage report."""

    lines = [
        "# Standards Coverage",
        "",
        "This report maps public cases to standards coverage rows for traceability. It is not compliance certification.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | ---: |",
        f"| Public cases covered | {snapshot['covered_case_count']} |",
        f"| Uncovered cases | {snapshot['uncovered_case_count']} |",
        f"| Standards catalogs | {len(snapshot['catalogs'])} |",
        f"| Mapping groups | {len(snapshot['mapping_groups'])} |",
        "",
        "## Catalogs",
        "",
        "| Catalog | Version | Controls |",
        "| --- | --- | ---: |",
    ]
    for catalog in snapshot["catalogs"]:
        lines.append(f"| `{catalog['catalog_id']}` | `{catalog['version']}` | {catalog['control_count']} |")

    lines.extend(
        [
            "",
            "## Mapping Groups",
            "",
            "| Group | Cases | Standards |",
            "| --- | ---: | --- |",
        ]
    )
    for group in snapshot["mapping_groups"]:
        standards = ", ".join(f"`{item['catalog_id']}:{item['control_id']}`" for item in group["standards"])
        lines.append(f"| `{group['group_id']}` | {group['selected_case_count']} | {standards} |")

    lines.extend(
        [
            "",
            "## Cases By Risk Area",
            "",
            "| Risk area | Cases |",
            "| --- | ---: |",
        ]
    )
    for risk_area, count in snapshot["case_summary"]["by_risk_area"].items():
        lines.append(f"| `{risk_area}` | {count} |")

    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in snapshot["claim_boundary"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    """CLI entrypoint."""

    try:
        snapshot = build_snapshot()
    except StandardsCoverageError as exc:
        print(f"standards coverage validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"standards coverage snapshot path: {display_path(DEFAULT_SNAPSHOT_PATH)}")
    print(f"standards coverage report path: {display_path(DEFAULT_REPORT_PATH)}")
    print(f"public cases covered: {snapshot['covered_case_count']}")
    print(f"uncovered cases: {snapshot['uncovered_case_count']}")
    print("standards coverage validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
