"""Validate M70 live-local review summaries.

The committed fixture is public-safe fake review metadata. It defines the
review protocol and inter-rater checks required before future live-local model
evidence can unlock benchmark publication. It does not read raw model outputs,
call providers, execute local models, run browser/email/network actions, or
perform external actions.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from reporting_utils import write_json_object, write_text
from schema_validation_utils import display_path, load_json_object, validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY_PATH = REPO_ROOT / "traces/external/live_local_review_summary.example.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/live_local_review_summary.schema.json"
DEFAULT_REPORT_JSON_PATH = REPO_ROOT / "reports/comparisons/live_local_review_summary.json"
DEFAULT_REPORT_MARKDOWN_PATH = REPO_ROOT / "reports/comparisons/live_local_review_summary.md"
GENERATED_AT = "2026-06-22T00:00:00Z"

EXPECTED_QUALITY_GATE = {
    "deterministic_gate_uses_fake_review_metadata_only": True,
    "live_local_execution_in_quality_gate": False,
    "provider_calls_in_quality_gate": False,
    "raw_outputs_read_in_quality_gate": False,
    "external_actions_in_quality_gate": False,
}
EXPECTED_SAFETY = {
    "public_safe": True,
    "contains_private_data": False,
    "raw_outputs_included": False,
    "credentials_required": False,
    "external_actions": False,
    "production_safety_claim": False,
    "cloud_ranking_claim": False,
}
BLOCKED_MARKERS = [
    "/Users/",
    "\\Users\\",
    "sk-",
    "BEGIN PRIVATE",
    "END PRIVATE",
    "raw_output_text",
    "customer",
]


class LiveLocalReviewSummaryError(Exception):
    """Live-local review summary validation error."""


def generate_live_local_review_summary_report(
    summary_path: Path = DEFAULT_SUMMARY_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    report_json_path: Path = DEFAULT_REPORT_JSON_PATH,
    report_markdown_path: Path = DEFAULT_REPORT_MARKDOWN_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the review summary and write public-safe report artifacts."""

    summary = validate_live_local_review_summary(summary_path, schema_path, repo_root)
    report = build_report(summary, summary_path, repo_root)
    validate_public_report(report, display_path(summary_path, repo_root))
    write_json_object(report, report_json_path)
    write_text(generate_markdown(report), report_markdown_path)
    return report


def validate_live_local_review_summary(
    summary_path: Path = DEFAULT_SUMMARY_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the public-safe live-local review summary."""

    schema = load_json_object(schema_path, "live-local review summary schema", repo_root, LiveLocalReviewSummaryError)
    summary = load_json_object(summary_path, "live-local review summary", repo_root, LiveLocalReviewSummaryError)
    context = display_path(summary_path, repo_root)
    validate_schema_value(summary, schema, context, summary_path, repo_root, LiveLocalReviewSummaryError)
    validate_semantics(summary, context)
    return summary


def validate_semantics(summary: dict[str, Any], context: str) -> None:
    validate_expected_map(summary["quality_gate"], EXPECTED_QUALITY_GATE, f"{context}.quality_gate")
    validate_expected_map(summary["safety_assertions"], EXPECTED_SAFETY, f"{context}.safety_assertions")

    protocol = summary["review_protocol"]
    if protocol["reviewer_aliases_only"] is not True:
        raise LiveLocalReviewSummaryError(f"{context}.review_protocol.reviewer_aliases_only must be true")
    if protocol["raw_outputs_included"] is not False:
        raise LiveLocalReviewSummaryError(f"{context}.review_protocol.raw_outputs_included must be false")
    if protocol["private_data_included"] is not False:
        raise LiveLocalReviewSummaryError(f"{context}.review_protocol.private_data_included must be false")

    records = summary["reviewed_records"]
    validate_review_records(records, context)
    validate_counts(summary, context)
    validate_inter_rater(summary["inter_rater"], records, context)


def validate_review_records(records: list[dict[str, Any]], context: str) -> None:
    seen_record_ids: set[str] = set()
    seen_case_ids: set[str] = set()
    for index, record in enumerate(records):
        record_context = f"{context}.reviewed_records[{index}]"
        record_id = str(record["record_id"])
        case_id = str(record["case_id"])
        if record_id in seen_record_ids:
            raise LiveLocalReviewSummaryError(f"{record_context}.record_id duplicate value: {record_id}")
        if case_id in seen_case_ids:
            raise LiveLocalReviewSummaryError(f"{record_context}.case_id duplicate value: {case_id}")
        seen_record_ids.add(record_id)
        seen_case_ids.add(case_id)

        validate_reviewer_alias(record["primary_reviewer_alias"], f"{record_context}.primary_reviewer_alias")
        secondary_alias = str(record["secondary_reviewer_alias"])
        if secondary_alias:
            validate_reviewer_alias(secondary_alias, f"{record_context}.secondary_reviewer_alias")
        if record["inter_rater_status"] == "single_review" and secondary_alias:
            raise LiveLocalReviewSummaryError(f"{record_context}.secondary_reviewer_alias must be empty for single_review")
        if record["inter_rater_status"] != "single_review" and not secondary_alias:
            raise LiveLocalReviewSummaryError(f"{record_context}.secondary_reviewer_alias is required for inter-rater records")
        if record["reviewer_decision"] == "needs_discussion" and record["effective_passed"] is True:
            raise LiveLocalReviewSummaryError(f"{record_context}.effective_passed must be false for needs_discussion")
        if record["reviewer_decision"] == "uphold_scorer_pass" and record["heuristic_passed"] is not True:
            raise LiveLocalReviewSummaryError(f"{record_context}.heuristic_passed must be true for uphold_scorer_pass")
        if record["reviewer_decision"] == "uphold_scorer_fail" and record["heuristic_passed"] is not False:
            raise LiveLocalReviewSummaryError(f"{record_context}.heuristic_passed must be false for uphold_scorer_fail")


def validate_counts(summary: dict[str, Any], context: str) -> None:
    records = summary["reviewed_records"]
    counts = summary["review_counts"]
    expected_counts = {
        "records_reviewed": len(records),
        "scorer_pass_count": sum(1 for record in records if record["heuristic_passed"] is True),
        "scorer_fail_count": sum(1 for record in records if record["heuristic_passed"] is False),
        "effective_pass_count": sum(1 for record in records if record["effective_passed"] is True),
        "effective_fail_count": sum(1 for record in records if record["effective_passed"] is False),
        "override_count": sum(1 for record in records if str(record["reviewer_decision"]).startswith("override_")),
        "needs_discussion_count": sum(1 for record in records if record["reviewer_decision"] == "needs_discussion"),
        "unsafe_output_count": sum(1 for record in records if record["unsafe_output"] is True),
        "malformed_output_count": sum(1 for record in records if record["malformed_output"] is True),
    }
    validate_expected_map(counts, expected_counts, f"{context}.review_counts")


def validate_inter_rater(inter_rater: dict[str, Any], records: list[dict[str, Any]], context: str) -> None:
    double_reviewed = [record for record in records if record["inter_rater_status"] in {"agreement", "disagreement"}]
    agreement_count = sum(1 for record in records if record["inter_rater_status"] == "agreement")
    disagreement_count = sum(1 for record in records if record["inter_rater_status"] == "disagreement")
    expected_rate = 1.0 if not double_reviewed else round(agreement_count / len(double_reviewed), 4)
    expected = {
        "double_reviewed_count": len(double_reviewed),
        "agreement_count": agreement_count,
        "disagreement_count": disagreement_count,
        "agreement_rate": expected_rate,
    }
    validate_expected_map(inter_rater, expected, f"{context}.inter_rater")


def build_report(summary: dict[str, Any], summary_path: Path, repo_root: Path) -> dict[str, Any]:
    """Build an aggregate public-safe review report."""

    return {
        "report_id": "m70_live_local_review_summary_report",
        "generated_at": GENERATED_AT,
        "source_summary_path": display_path(summary_path, repo_root),
        "source_schema_path": display_path(DEFAULT_SCHEMA_PATH, repo_root),
        "summary_id": summary["summary_id"],
        "review_protocol": summary["review_protocol"],
        "sampling_policy": summary["sampling_policy"],
        "review_counts": summary["review_counts"],
        "inter_rater": summary["inter_rater"],
        "quality_gate": summary["quality_gate"],
        "safety_assertions": summary["safety_assertions"],
        "publication_gate": {
            "unresolved_review_blocks_publication": True,
            "publishable_review_state": summary["review_counts"]["needs_discussion_count"] == 0,
            "needs_discussion_count": summary["review_counts"]["needs_discussion_count"],
            "unsafe_output_count": summary["review_counts"]["unsafe_output_count"],
            "malformed_output_count": summary["review_counts"]["malformed_output_count"],
        },
        "boundaries": [
            "M70 validates public-safe review metadata only.",
            "Reviewer IDs are aliases, not personal identities.",
            "Raw local model outputs are not included in committed review summaries.",
            "Unresolved needs_discussion records block publishable benchmark evidence.",
            "This report is not a live model run, cloud ranking, production-safety proof, or provider benchmark.",
        ],
    }


def validate_public_report(report: dict[str, Any], context: str) -> None:
    validate_expected_map(report["quality_gate"], EXPECTED_QUALITY_GATE, f"{context}.report.quality_gate")
    validate_expected_map(report["safety_assertions"], EXPECTED_SAFETY, f"{context}.report.safety_assertions")
    text = str(report)
    for marker in BLOCKED_MARKERS:
        if marker in text:
            raise LiveLocalReviewSummaryError(f"{context}.report contains blocked marker: {marker}")


def generate_markdown(report: dict[str, Any]) -> str:
    counts = report["review_counts"]
    inter_rater = report["inter_rater"]
    gate = report["publication_gate"]
    lines = [
        "# Live-Local Review Summary",
        "",
        "This M70 report is public-safe review metadata only. It defines the review and inter-rater gates required before future live-local evidence can become publishable benchmark evidence.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Generated at | `{report['generated_at']}` |",
        f"| Source summary | `{report['source_summary_path']}` |",
        f"| Records reviewed | {counts['records_reviewed']} |",
        f"| Needs discussion | {counts['needs_discussion_count']} |",
        f"| Overrides | {counts['override_count']} |",
        f"| Unsafe outputs | {counts['unsafe_output_count']} |",
        f"| Malformed outputs | {counts['malformed_output_count']} |",
        f"| Publishable review state | `{str(gate['publishable_review_state']).lower()}` |",
        "",
        "## Inter-Rater",
        "",
        f"- Reviewers: `{inter_rater['reviewer_count']}`",
        f"- Double-reviewed records: `{inter_rater['double_reviewed_count']}`",
        f"- Agreement rate: `{inter_rater['agreement_rate']:.4f}`",
        f"- Disagreements: `{inter_rater['disagreement_count']}`",
        "",
        "## Boundaries",
        "",
        "\n".join(f"- {boundary}" for boundary in report["boundaries"]),
        "",
    ]
    return "\n".join(lines)


def validate_expected_map(value: dict[str, Any], expected: dict[str, Any], context: str) -> None:
    for field_name, expected_value in expected.items():
        if value[field_name] != expected_value:
            raise LiveLocalReviewSummaryError(f"{context}.{field_name} must equal {expected_value!r}")


def validate_reviewer_alias(value: str, context: str) -> None:
    if not value.startswith("reviewer_"):
        raise LiveLocalReviewSummaryError(f"{context} must be a public-safe reviewer alias")
    if any(marker in value for marker in ["@", "/", "\\", " "]):
        raise LiveLocalReviewSummaryError(f"{context} must not contain personal contact details")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and report live-local review summary metadata.")
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_SUMMARY_PATH)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON_PATH)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MARKDOWN_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        report = generate_live_local_review_summary_report(
            args.path,
            args.schema,
            args.report_json,
            args.report_md,
        )
    except (OSError, ValueError, LiveLocalReviewSummaryError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"review summary: {report['source_summary_path']}")
    print(f"records reviewed: {report['review_counts']['records_reviewed']}")
    print(f"needs discussion: {report['review_counts']['needs_discussion_count']}")
    print("live-local review summary validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
