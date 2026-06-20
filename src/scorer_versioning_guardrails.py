"""Generate deterministic M51 scorer-versioning guardrail artifacts.

This report documents the adjudication schema and validation support that lets
future scorer changes preserve historical reviewer context. It reads committed
local artifacts only and does not change scorer behavior, rescore traces, call
providers, run models, execute agents, inspect private logs, use networks, or
perform external actions.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from reporting_utils import (
    display_path,
    format_list,
    load_json_object,
    load_jsonl_records,
    write_json_object,
    write_text,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-21T00:00:00Z"

SCORER_CHANGE_DECISION_PATH = REPO_ROOT / "reports/comparisons/scorer_change_decision.json"
ADJUDICATION_SCHEMA_PATH = REPO_ROOT / "schemas/adjudication.schema.json"
ADJUDICATION_MANIFEST_PATH = REPO_ROOT / "traces/external/adjudication_manifest.json"
VALIDATOR_PATH = REPO_ROOT / "src/validate_adjudications.py"
VALIDATOR_TEST_PATH = REPO_ROOT / "tests/test_validate_adjudications.py"
SCORER_PATH = REPO_ROOT / "src/scorers.py"

JSON_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/scorer_versioning_guardrails.json"
MARKDOWN_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/scorer_versioning_guardrails.md"


class ScorerVersioningGuardrailsError(Exception):
    """Scorer-versioning guardrails generation error."""


def build_scorer_versioning_guardrails() -> dict[str, Any]:
    """Build the deterministic M51 scorer-versioning guardrail report."""

    scorer_decision = load_json_object(SCORER_CHANGE_DECISION_PATH)
    adjudication_schema = load_json_object(ADJUDICATION_SCHEMA_PATH)
    adjudication_manifest = load_json_object(ADJUDICATION_MANIFEST_PATH)
    historical_schema = historical_scorer_context_schema(adjudication_schema)
    adjudication_records = load_manifest_adjudications(adjudication_manifest)
    context_records = [
        record
        for record in adjudication_records
        if isinstance(record.get("historical_scorer_context"), dict)
    ]

    return {
        "guardrail_id": "m51_scorer_versioning_guardrails",
        "generated_at": GENERATED_AT,
        "scope": "Deterministic guardrails for preserving historical adjudication context across future scorer changes.",
        "source_paths": source_paths(adjudication_manifest),
        "safety": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
            "credentials_required": False,
        },
        "decision_summary": {
            "historical_scorer_context_supported": True,
            "validation_mode": "current_trace_match_or_explicit_historical_context",
            "current_adjudication_records": len(adjudication_records),
            "current_records_with_historical_context": len(context_records),
            "migration_required_now": False,
            "accepted_scorer_changes": 0,
            "scorer_code_changed": False,
            "scored_trace_behavior_changed": False,
        },
        "m50_dependency": {
            "decision": scorer_decision.get("decision_summary", {}).get("decision", "unknown"),
            "accepted_scorer_changes": scorer_decision.get("decision_summary", {}).get(
                "accepted_scorer_changes",
                0,
            ),
            "historical_scorer_version_metadata_present_before_m51": scorer_decision.get(
                "historical_context",
                {},
            ).get("historical_scorer_version_metadata_present", False),
        },
        "schema_guardrail": {
            "optional_field": "historical_scorer_context",
            "schema_version": historical_schema["properties"]["schema_version"]["const"],
            "required_fields": list(historical_schema["required"]),
            "current_trace_fields": [
                "current_trace_passed",
                "current_trace_score",
                "current_trace_failure_modes",
            ],
            "original_fields_preserved_on_record": [
                "original_passed",
                "original_score",
                "original_failure_modes",
            ],
        },
        "validation_rules": [
            {
                "rule_id": "legacy_records_match_current_trace",
                "summary": (
                    "Adjudications without historical_scorer_context must keep original fields equal to "
                    "the current source scored trace."
                ),
            },
            {
                "rule_id": "historical_context_records_pin_current_trace",
                "summary": (
                    "Adjudications with historical_scorer_context must record current_trace_passed, "
                    "current_trace_score, and current_trace_failure_modes that match the current source trace."
                ),
            },
            {
                "rule_id": "historical_context_requires_real_mismatch",
                "summary": (
                    "historical_scorer_context is accepted only when original fields differ from the current source trace."
                ),
            },
            {
                "rule_id": "historical_scorer_artifact_is_repo_local",
                "summary": "The original_scorer_artifact path must be repository-relative and must exist.",
            },
        ],
        "future_use": [
            "When a future scorer change rewrites a scored trace, existing adjudications can preserve the pre-change original fields.",
            "The historical_scorer_context block must then pin the current trace outcome for validator clarity.",
            "Reviewer decisions remain separate from heuristic scored traces.",
        ],
        "boundary": [
            "M51 adds schema and validation guardrails only.",
            "No scorer code changes are accepted in M51.",
            "No scored trace behavior changes are introduced in M51.",
            "No model-assisted judging, live provider call, runtime execution, network access, private data, or external action is introduced.",
        ],
    }


def historical_scorer_context_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return and validate the optional historical scorer context schema."""

    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise ScorerVersioningGuardrailsError("adjudication schema properties must be an object")
    historical_schema = properties.get("historical_scorer_context")
    if not isinstance(historical_schema, dict):
        raise ScorerVersioningGuardrailsError("adjudication schema must define historical_scorer_context")
    required = historical_schema.get("required", [])
    expected = {
        "schema_version",
        "original_scorer_version",
        "original_scorer_artifact",
        "current_trace_passed",
        "current_trace_score",
        "current_trace_failure_modes",
        "mismatch_reason",
    }
    if set(required) != expected:
        raise ScorerVersioningGuardrailsError("historical_scorer_context required fields are incomplete")
    return historical_schema


def load_manifest_adjudications(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Load adjudication fixture records listed by the manifest."""

    records = []
    fixtures = manifest.get("adjudication_fixtures", [])
    if not isinstance(fixtures, list) or not fixtures:
        raise ScorerVersioningGuardrailsError("adjudication manifest must contain fixtures")
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            raise ScorerVersioningGuardrailsError("adjudication fixtures must be objects")
        records.extend(load_jsonl_records(REPO_ROOT / str(fixture["path"])))
    return records


def source_paths(adjudication_manifest: dict[str, Any]) -> list[str]:
    paths = [
        SCORER_CHANGE_DECISION_PATH,
        ADJUDICATION_SCHEMA_PATH,
        ADJUDICATION_MANIFEST_PATH,
        VALIDATOR_PATH,
        VALIDATOR_TEST_PATH,
        SCORER_PATH,
    ]
    for fixture in adjudication_manifest.get("adjudication_fixtures", []):
        if isinstance(fixture, dict):
            paths.append(REPO_ROOT / str(fixture["path"]))
    return [display_path(path, REPO_ROOT) for path in paths]


def generate_markdown(guardrails: dict[str, Any]) -> str:
    """Generate reader-facing Markdown for M51 scorer-versioning guardrails."""

    summary = guardrails["decision_summary"]
    schema = guardrails["schema_guardrail"]
    lines = [
        "# Scorer Versioning Guardrails",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | ---: |",
        f"| Generated at | `{guardrails['generated_at']}` |",
        f"| Historical scorer context supported | {str(summary['historical_scorer_context_supported']).lower()} |",
        f"| Current adjudication records | {summary['current_adjudication_records']} |",
        f"| Records with historical context | {summary['current_records_with_historical_context']} |",
        f"| Migration required now | {str(summary['migration_required_now']).lower()} |",
        f"| Accepted scorer changes | {summary['accepted_scorer_changes']} |",
        f"| Scorer code changed | {str(summary['scorer_code_changed']).lower()} |",
        "",
        "M51 adds explicit validation support for preserving historical scorer outcomes if future scorer changes rewrite committed scored traces.",
        "",
        "## Schema Guardrail",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Optional context field | `{schema['optional_field']}` |",
        f"| Schema version | `{schema['schema_version']}` |",
        f"| Required fields | {format_list(schema['required_fields'])} |",
        f"| Current trace fields | {format_list(schema['current_trace_fields'])} |",
        f"| Preserved original fields | {format_list(schema['original_fields_preserved_on_record'])} |",
        "",
        "## Validation Rules",
        "",
        _rule_table(guardrails["validation_rules"]),
        "",
        "## Future Use",
        "",
        "\n".join(f"- {item}" for item in guardrails["future_use"]),
        "",
        "## Boundary",
        "",
        "\n".join(f"- {item}" for item in guardrails["boundary"]),
        "",
        "## Sources",
        "",
        "\n".join(f"- `{path}`" for path in guardrails["source_paths"]),
        "",
    ]
    return "\n".join(lines)


def _rule_table(rules: list[dict[str, str]]) -> str:
    lines = [
        "| Rule | Summary |",
        "| --- | --- |",
    ]
    for rule in rules:
        lines.append(f"| `{rule['rule_id']}` | {rule['summary']} |")
    return "\n".join(lines)


def main() -> int:
    try:
        guardrails = build_scorer_versioning_guardrails()
        write_json_object(guardrails, JSON_OUTPUT_PATH)
        write_text(generate_markdown(guardrails), MARKDOWN_OUTPUT_PATH)
    except (OSError, ValueError, ScorerVersioningGuardrailsError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary = guardrails["decision_summary"]
    print(f"scorer versioning guardrails JSON path: {display_path(JSON_OUTPUT_PATH, REPO_ROOT)}")
    print(f"scorer versioning guardrails report path: {display_path(MARKDOWN_OUTPUT_PATH, REPO_ROOT)}")
    print(f"historical scorer context supported: {summary['historical_scorer_context_supported']}")
    print(f"records with historical context: {summary['current_records_with_historical_context']}")
    print(f"accepted scorer changes: {summary['accepted_scorer_changes']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
