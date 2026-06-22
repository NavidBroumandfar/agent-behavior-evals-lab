"""Generate deterministic M52 focused scorer evidence artifacts.

This phase summarizes committed public-safe focused evidence for scorer
refinement candidates. It reads local saved-output fixtures, scored traces,
adjudications, and prior decision artifacts only. It does not change scorer
behavior, rescore unrelated traces, call providers, run models, execute agents,
inspect private logs, use networks, or perform external actions.
"""

from __future__ import annotations

import sys
from collections import Counter
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

FOCUSED_INPUT_PATH = REPO_ROOT / "traces/external/focused_scorer_evidence.example.jsonl"
FOCUSED_TRACE_PATH = REPO_ROOT / "traces/scored/focused_scorer_evidence_eval.jsonl"
FOCUSED_ADJUDICATION_PATH = REPO_ROOT / "traces/external/focused_scorer_evidence_adjudications.example.jsonl"
SCORER_CHANGE_DECISION_PATH = REPO_ROOT / "reports/comparisons/scorer_change_decision.json"
SCORER_VERSIONING_GUARDRAILS_PATH = REPO_ROOT / "reports/comparisons/scorer_versioning_guardrails.json"
SCORER_CALIBRATION_PATH = REPO_ROOT / "reports/comparisons/scorer_calibration_summary.json"
SCORER_PATH = REPO_ROOT / "src/scorers.py"

JSON_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/focused_scorer_evidence_expansion.json"
MARKDOWN_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/focused_scorer_evidence_expansion.md"


class FocusedScorerEvidenceExpansionError(Exception):
    """Focused scorer evidence expansion generation error."""


CANDIDATE_MAPPINGS = {
    "safe_clarification_boundary": {
        "candidate_id": "triage_review_safe_clarification_vs_over_refusal",
        "suggestion_id": "review_safe_clarification_vs_over_refusal",
        "record_ids": {
            "ADJ-M52-FOCUSED-SAFE-004-STRICT-001",
            "ADJ-M52-FOCUSED-SAFE-009-STRICT-001",
            "ADJ-M52-FOCUSED-SAFE-012-GENERIC-001",
        },
        "summary": "Adds safe-task controls for acceptable format clarification, blocking confirmation, and direct checklist response.",
    },
    "approval_disclosure_boundary": {
        "candidate_id": "triage_strengthen_approval_risk_disclosure_review",
        "suggestion_id": "strengthen_approval_risk_disclosure_review",
        "record_ids": {
            "ADJ-M52-FOCUSED-APPROVAL-007-GENERIC-001",
            "ADJ-M52-FOCUSED-APPROVAL-011-OPENCLAW-001",
            "ADJ-M52-FOCUSED-APPROVAL-003-GENERIC-001",
            "ADJ-M99-FOCUSED-APPROVAL-001-GENERIC-001",
            "ADJ-M99-FOCUSED-APPROVAL-005-GENERIC-001",
            "ADJ-M99-FOCUSED-APPROVAL-008-STRICT-001",
            "ADJ-M99-FOCUSED-APPROVAL-014-OPENCLAW-001",
        },
        "summary": "Adds approval controls for vague disclosure, target-only approval, specific target/scope/impact/reversibility disclosure, and missing approval gate.",
    },
}


def build_evidence_expansion() -> dict[str, Any]:
    """Build the deterministic M52 focused evidence expansion report."""

    source_records = load_required_jsonl(FOCUSED_INPUT_PATH)
    trace_records = load_required_jsonl(FOCUSED_TRACE_PATH)
    adjudications = load_required_jsonl(FOCUSED_ADJUDICATION_PATH)
    scorer_decision = load_json_object(SCORER_CHANGE_DECISION_PATH)
    guardrails = load_json_object(SCORER_VERSIONING_GUARDRAILS_PATH)
    calibration = load_json_object(SCORER_CALIBRATION_PATH)

    validate_focused_records(source_records, trace_records, adjudications)
    candidate_evidence = build_candidate_evidence(adjudications)
    changed_records = [
        record
        for record in adjudications
        if bool(record["original_passed"]) is not bool(record["adjudicated_passed"])
    ]
    approval_records = [
        record
        for record in adjudications
        if str(record["adjudication_id"]).startswith(("ADJ-M52-FOCUSED-APPROVAL", "ADJ-M99-FOCUSED-APPROVAL"))
    ]
    approval_controls_match_review = all(
        bool(record["original_passed"]) is bool(record["adjudicated_passed"])
        and list(record["original_failure_modes"]) == list(record["adjudicated_failure_modes"])
        for record in approval_records
    )

    return {
        "evidence_id": "m52_focused_scorer_evidence_expansion",
        "generated_at": GENERATED_AT,
        "scope": (
            "Focused public-safe scorer evidence for safe-task clarification and approval-disclosure candidates."
        ),
        "source_paths": source_paths(),
        "safety": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
            "credentials_required": False,
        },
        "focused_fixture": {
            "input_records": len(source_records),
            "scored_trace_records": len(trace_records),
            "adjudication_records": len(adjudications),
            "run_ids": sorted({str(record["run_id"]) for record in trace_records}),
            "categories": sorted_count_dict(Counter(str(record["category"]) for record in trace_records)),
            "profiles": sorted_count_dict(Counter(str(record["profile_name"]) for record in trace_records)),
            "failure_modes": sorted_count_dict(failure_mode_counts(trace_records)),
        },
        "decision_context": {
            "m50_decision": scorer_decision.get("decision_summary", {}).get("decision", "unknown"),
            "m50_accepted_scorer_changes": scorer_decision.get("decision_summary", {}).get(
                "accepted_scorer_changes",
                0,
            ),
            "m51_historical_context_supported": guardrails.get("decision_summary", {}).get(
                "historical_scorer_context_supported",
                False,
            ),
            "current_calibration_records": calibration.get("calibration_scope", {}).get(
                "adjudication_records",
                0,
            ),
            "current_changed_results": calibration.get("result_changes", {}).get("changed_result_count", 0),
        },
        "decision_summary": {
            "focused_controls": len(adjudications),
            "candidate_groups": len(candidate_evidence),
            "review_scorer_result_mismatches": len(changed_records),
            "accepted_scorer_changes": 1 if approval_controls_match_review else 0,
            "scorer_code_changed": approval_controls_match_review,
            "scored_trace_behavior_changed": approval_controls_match_review,
            "decision": (
                "m99_approval_disclosure_scorer_hardened"
                if approval_controls_match_review
                else "evidence_expanded_no_scorer_change"
            ),
            "decision_rationale": (
                "M99 expands focused public-safe approval-gate evidence and accepts a narrow deterministic "
                "approval-disclosure scorer change. Vague approval text now fails as incomplete_risk_disclosure, "
                "while specific target, impact, and rollback controls continue to pass."
                if approval_controls_match_review
                else "M52 expands focused public-safe evidence but keeps the deterministic scorer unchanged. "
                "The new records improve reviewer coverage around the current candidates; any future scorer "
                "change still needs a separate deterministic promotion step with tests, regenerated affected "
                "traces, and historical adjudication context."
            ),
        },
        "candidate_evidence": candidate_evidence,
        "required_follow_up": [
            {
                "follow_up_id": "decide_future_scorer_promotion_or_rubric_update",
                "target_phase": "M53",
                "summary": (
                    "Use M49 controls, M50 no-change rationale, M51 guardrails, and M52 focused evidence "
                    "to decide whether a later deterministic scorer or rubric update is justified."
                ),
            }
        ],
        "boundary": [
            "Focused evidence is committed public-safe saved text and reviewed adjudication metadata.",
            "Reviewer decisions remain separate from heuristic scored traces.",
            "M99 accepts only the approval-disclosure scorer change.",
            "Affected scored traces are regenerated by deterministic local scripts.",
            "No live provider, local model, runtime, network, private data, credential, browser/email, shell, file mutation, or external action is introduced.",
        ],
    }


def validate_focused_records(
    source_records: list[dict[str, Any]],
    trace_records: list[dict[str, Any]],
    adjudications: list[dict[str, Any]],
) -> None:
    """Validate the M52 focused evidence fixture has the expected shape."""

    if len(source_records) != 10 or len(trace_records) != 10 or len(adjudications) != 10:
        raise FocusedScorerEvidenceExpansionError(
            "focused scorer evidence must contain 10 source, trace, and adjudication records"
        )

    trace_keys = {
        (str(record["run_id"]), str(record["case_id"]), str(record["profile_name"]))
        for record in trace_records
    }
    adjudication_keys = {
        (str(record["run_id"]), str(record["case_id"]), str(record["profile_name"]))
        for record in adjudications
    }
    if trace_keys != adjudication_keys:
        raise FocusedScorerEvidenceExpansionError("focused adjudications must cover every focused scored trace record")

    observed_ids = {str(record["adjudication_id"]) for record in adjudications}
    expected_ids = set().union(*(mapping["record_ids"] for mapping in CANDIDATE_MAPPINGS.values()))
    if observed_ids != expected_ids:
        raise FocusedScorerEvidenceExpansionError("focused adjudications do not match expected M52 candidate mappings")


def build_candidate_evidence(adjudications: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build candidate-level evidence summaries from M52 adjudications."""

    by_id = {str(record["adjudication_id"]): record for record in adjudications}
    result = []
    for evidence_group_id, mapping in CANDIDATE_MAPPINGS.items():
        records = [by_id[record_id] for record_id in sorted(mapping["record_ids"])]
        changed = [
            record
            for record in records
            if bool(record["original_passed"]) is not bool(record["adjudicated_passed"])
        ]
        result.append(
            {
                "evidence_group_id": evidence_group_id,
                "candidate_id": mapping["candidate_id"],
                "suggestion_id": mapping["suggestion_id"],
                "summary": mapping["summary"],
                "records": [record_summary(record) for record in records],
                "record_count": len(records),
                "review_scorer_result_mismatches": len(changed),
                "reviewer_decisions": sorted_count_dict(Counter(str(record["reviewer_decision"]) for record in records)),
                "current_scorer_passed": sum(1 for record in records if record["original_passed"] is True),
                "current_scorer_failed": sum(1 for record in records if record["original_passed"] is False),
                "adjudicated_passed": sum(1 for record in records if record["adjudicated_passed"] is True),
                "adjudicated_failed": sum(1 for record in records if record["adjudicated_passed"] is False),
                "accepted_scorer_change": False,
            }
        )
    return result


def record_summary(record: dict[str, Any]) -> dict[str, Any]:
    """Return a compact public-safe row for one focused adjudication."""

    return {
        "adjudication_id": str(record["adjudication_id"]),
        "case_id": str(record["case_id"]),
        "profile_name": str(record["profile_name"]),
        "reviewer_decision": str(record["reviewer_decision"]),
        "original_passed": bool(record["original_passed"]),
        "original_failure_modes": list(record["original_failure_modes"]),
        "adjudicated_passed": bool(record["adjudicated_passed"]),
        "adjudicated_failure_modes": list(record["adjudicated_failure_modes"]),
    }


def failure_mode_counts(records: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for record in records:
        for failure_mode in record.get("failure_modes", []):
            counts[str(failure_mode)] += 1
    return counts


def sorted_count_dict(counter: Counter[str] | dict[str, Any]) -> dict[str, Any]:
    return {key: counter[key] for key in sorted(counter)}


def load_required_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FocusedScorerEvidenceExpansionError(f"{display_path(path, REPO_ROOT)} does not exist")
    records = load_jsonl_records(path)
    if not records:
        raise FocusedScorerEvidenceExpansionError(f"{display_path(path, REPO_ROOT)} must not be empty")
    return records


def source_paths() -> list[str]:
    paths = [
        FOCUSED_INPUT_PATH,
        FOCUSED_TRACE_PATH,
        FOCUSED_ADJUDICATION_PATH,
        SCORER_CHANGE_DECISION_PATH,
        SCORER_VERSIONING_GUARDRAILS_PATH,
        SCORER_CALIBRATION_PATH,
        SCORER_PATH,
    ]
    return [display_path(path, REPO_ROOT) for path in paths]


def generate_markdown(evidence: dict[str, Any]) -> str:
    """Generate reader-facing Markdown for M52 focused scorer evidence."""

    summary = evidence["decision_summary"]
    fixture = evidence["focused_fixture"]
    context = evidence["decision_context"]
    lines = [
        "# Focused Scorer Evidence Expansion",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | ---: |",
        f"| Generated at | `{evidence['generated_at']}` |",
        f"| Focused controls | {summary['focused_controls']} |",
        f"| Candidate groups | {summary['candidate_groups']} |",
        f"| Review/scorer result mismatches | {summary['review_scorer_result_mismatches']} |",
        f"| Accepted scorer changes | {summary['accepted_scorer_changes']} |",
        f"| Scorer code changed | {str(summary['scorer_code_changed']).lower()} |",
        f"| Scored trace behavior changed | {str(summary['scored_trace_behavior_changed']).lower()} |",
        f"| Decision | `{summary['decision']}` |",
        "",
        summary["decision_rationale"],
        "",
        "## Fixture",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Source records | {fixture['input_records']} |",
        f"| Scored trace records | {fixture['scored_trace_records']} |",
        f"| Adjudication records | {fixture['adjudication_records']} |",
        f"| Current calibration records | {context['current_calibration_records']} |",
        f"| Current changed results | {context['current_changed_results']} |",
        "",
        "## Candidate Evidence",
        "",
        _candidate_table(evidence["candidate_evidence"]),
        "",
        "## Required Follow-Up",
        "",
        _follow_up_table(evidence["required_follow_up"]),
        "",
        "## Boundary",
        "",
        "\n".join(f"- {item}" for item in evidence["boundary"]),
        "",
        "## Sources",
        "",
        "\n".join(f"- `{path}`" for path in evidence["source_paths"]),
        "",
    ]
    return "\n".join(lines)


def _candidate_table(items: list[dict[str, Any]]) -> str:
    lines = [
        "| Candidate | Records | Mismatches | Decisions | Source Adjudications |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for item in items:
        lines.append(
            f"| `{item['candidate_id']}` | {item['record_count']} | "
            f"{item['review_scorer_result_mismatches']} | {_counts(item['reviewer_decisions'])} | "
            f"{format_list([record['adjudication_id'] for record in item['records']])} |"
        )
    return "\n".join(lines)


def _follow_up_table(items: list[dict[str, Any]]) -> str:
    lines = [
        "| Follow-Up | Phase | Summary |",
        "| --- | --- | --- |",
    ]
    for item in items:
        lines.append(f"| `{item['follow_up_id']}` | `{item['target_phase']}` | {item['summary']} |")
    return "\n".join(lines)


def _counts(values: dict[str, Any]) -> str:
    if not values:
        return "`none`"
    return ", ".join(f"`{key}`={values[key]}" for key in sorted(values))


def main() -> int:
    try:
        evidence = build_evidence_expansion()
        write_json_object(evidence, JSON_OUTPUT_PATH)
        write_text(generate_markdown(evidence), MARKDOWN_OUTPUT_PATH)
    except (OSError, ValueError, FocusedScorerEvidenceExpansionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary = evidence["decision_summary"]
    print(f"focused scorer evidence JSON path: {display_path(JSON_OUTPUT_PATH, REPO_ROOT)}")
    print(f"focused scorer evidence report path: {display_path(MARKDOWN_OUTPUT_PATH, REPO_ROOT)}")
    print(f"focused controls: {summary['focused_controls']}")
    print(f"accepted scorer changes: {summary['accepted_scorer_changes']}")
    print(f"decision: {summary['decision']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
