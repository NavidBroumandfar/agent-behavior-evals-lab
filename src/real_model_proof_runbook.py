"""Generate the M76 real-model proof operator runbook.

The runbook is public-safe metadata. It exposes the next manual opt-in CLI
commands and publication blockers without executing local models, calling
providers, reading raw outputs, handling credentials, or performing external
actions.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from reporting_utils import write_json_object, write_text
from schema_validation_utils import display_path, load_json_object, validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNBOOK_PATH = REPO_ROOT / "traces/external/real_model_proof_runbook.example.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/real_model_proof_runbook.schema.json"
DEFAULT_REPORT_JSON_PATH = REPO_ROOT / "reports/comparisons/real_model_proof_runbook.json"
DEFAULT_REPORT_MARKDOWN_PATH = REPO_ROOT / "reports/comparisons/real_model_proof_runbook.md"
GENERATED_AT = "2026-06-22T00:00:00Z"

EXPECTED_QUALITY_GATE = {
    "deterministic_gate_uses_fake_metadata_only": True,
    "live_local_execution_in_quality_gate": False,
    "provider_calls_in_quality_gate": False,
    "raw_outputs_read_in_quality_gate": False,
    "external_actions_in_quality_gate": False,
}
EXPECTED_SAFETY = {
    "public_safe": True,
    "metadata_only": True,
    "contains_private_data": False,
    "contains_credentials_or_secrets": False,
    "contains_raw_outputs": False,
    "public_leaderboard_claim": False,
    "production_safety_claim": False,
    "third_party_reproducibility_claim": False,
}
BLOCKED_MARKERS = [
    "sk-",
    "/Users/",
    "\\Users\\",
    "BEGIN PRIVATE",
    "END PRIVATE",
    "raw_output_text",
]


class RealModelProofRunbookError(Exception):
    """Real-model proof runbook validation error."""


def generate_real_model_proof_runbook(
    runbook_path: Path = DEFAULT_RUNBOOK_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    report_json_path: Path = DEFAULT_REPORT_JSON_PATH,
    report_markdown_path: Path = DEFAULT_REPORT_MARKDOWN_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate runbook metadata and write public-safe report artifacts."""

    runbook = validate_real_model_proof_runbook(runbook_path, schema_path, repo_root)
    report = build_report(runbook, runbook_path, repo_root)
    validate_public_report(report, display_path(runbook_path, repo_root))
    write_json_object(report, report_json_path)
    write_text(generate_markdown(report), report_markdown_path)
    return report


def validate_real_model_proof_runbook(
    runbook_path: Path = DEFAULT_RUNBOOK_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the public-safe real-model proof runbook."""

    schema = load_json_object(schema_path, "real-model proof runbook schema", repo_root, RealModelProofRunbookError)
    runbook = load_json_object(runbook_path, "real-model proof runbook", repo_root, RealModelProofRunbookError)
    context = display_path(runbook_path, repo_root)
    validate_schema_value(runbook, schema, context, runbook_path, repo_root, RealModelProofRunbookError)
    validate_runbook_semantics(runbook, context)
    return runbook


def validate_runbook_semantics(runbook: dict[str, Any], context: str) -> None:
    validate_expected_map(runbook["quality_gate"], EXPECTED_QUALITY_GATE, f"{context}.quality_gate")
    validate_expected_map(runbook["safety_assertions"], EXPECTED_SAFETY, f"{context}.safety_assertions")
    if runbook["local_runtime"]["manual_opt_in_required"] is not True:
        raise RealModelProofRunbookError(f"{context}.local_runtime.manual_opt_in_required must be true")
    if runbook["publication_gate"]["local_ranking_claim_allowed"] is True:
        if runbook["evidence_status"]["eligible_reviewed_live_local_ledgers"] < 2:
            raise RealModelProofRunbookError(f"{context}.publication_gate cannot allow ranking before two eligible ledgers")
        if runbook["review_queue"]["needs_discussion_count"] != 0:
            raise RealModelProofRunbookError(f"{context}.publication_gate cannot allow ranking with unresolved review")
    else:
        if not runbook["publication_gate"]["blocked_reason"].strip():
            raise RealModelProofRunbookError(f"{context}.publication_gate.blocked_reason must explain publication block")

    decision = runbook["second_target_decision"]
    selected_model = str(decision["selected_model"])
    primary_targets = runbook["model_lineup"]["primary_local_targets"]
    primary_model_names = {target["model"] for target in primary_targets}
    if primary_model_names != {"llama3.2:latest", selected_model}:
        raise RealModelProofRunbookError(
            f"{context}.model_lineup.primary_local_targets must include llama3.2:latest and the M80 selected model"
        )
    if selected_model in {"qwen3.5:2b-q4_K_M", "gemma4:31b-cloud"}:
        raise RealModelProofRunbookError(f"{context}.second_target_decision.selected_model cannot be smoke/control or cloud")
    if selected_model == decision["replaced_model"] and decision["decision"] == "replace_gemma4_for_publication_path":
        raise RealModelProofRunbookError(f"{context}.second_target_decision.selected_model must replace gemma4")
    if selected_model != decision["replaced_model"] and decision["decision"] == "retry_gemma4_with_stability_profile":
        raise RealModelProofRunbookError(f"{context}.second_target_decision selected model must match retry decision")
    if decision["live_execution_required_for_decision"] is not False:
        raise RealModelProofRunbookError(f"{context}.second_target_decision must remain documentation-only")

    excluded_targets = runbook["model_lineup"]["excluded_targets"]
    if not any(target["model"] == "gemma4:31b-cloud" for target in excluded_targets):
        raise RealModelProofRunbookError(f"{context}.model_lineup.excluded_targets must exclude gemma4:31b-cloud")
    if not any(target["model"] == decision["replaced_model"] for target in excluded_targets):
        raise RealModelProofRunbookError(f"{context}.model_lineup.excluded_targets must defer replaced local target")
    for target in excluded_targets:
        if target["eligible_for_local_ranking"] is not False:
            raise RealModelProofRunbookError(f"{context}.model_lineup.excluded_targets must be ranking-ineligible")
    live_commands = [command for command in runbook["operator_commands"] if command["live_execution"] is True]
    if not live_commands:
        raise RealModelProofRunbookError(f"{context}.operator_commands must include manual live-local commands")
    for command in live_commands:
        if "AGENT_EVALS_ENABLE_LIVE_LOCAL=1" not in command["command"] or "--live-local" not in command["command"]:
            raise RealModelProofRunbookError(f"{context}.operator_commands live commands must require explicit opt-in")
        if command["commits_raw_outputs"] is not False:
            raise RealModelProofRunbookError(f"{context}.operator_commands live commands must not commit raw outputs")
    if not any(
        selected_model in command["command"] and command["live_execution"] is False
        for command in runbook["operator_commands"]
    ):
        raise RealModelProofRunbookError(f"{context}.operator_commands must include a non-live plan for selected model")
    if not any(
        selected_model in command["command"] and command["live_execution"] is True
        for command in runbook["operator_commands"]
    ):
        raise RealModelProofRunbookError(f"{context}.operator_commands must include an opt-in live command for selected model")
    if runbook["hosted_provider_path"]["mixed_with_local_ranking"] is not False:
        raise RealModelProofRunbookError(f"{context}.hosted_provider_path.mixed_with_local_ranking must be false")


def build_report(runbook: dict[str, Any], runbook_path: Path, repo_root: Path) -> dict[str, Any]:
    return {
        "report_id": "m76_real_model_proof_runbook_report",
        "generated_at": GENERATED_AT,
        "source_runbook_path": display_path(runbook_path, repo_root),
        "source_schema_path": display_path(DEFAULT_SCHEMA_PATH, repo_root),
        "objective": runbook["objective"],
        "local_runtime": runbook["local_runtime"],
        "model_lineup": runbook["model_lineup"],
        "second_target_decision": runbook["second_target_decision"],
        "evidence_status": runbook["evidence_status"],
        "review_queue": runbook["review_queue"],
        "operator_commands": runbook["operator_commands"],
        "publication_gate": runbook["publication_gate"],
        "hosted_provider_path": runbook["hosted_provider_path"],
        "quality_gate": runbook["quality_gate"],
        "safety_assertions": runbook["safety_assertions"],
        "boundaries": [
            "This runbook is CLI/report product surface only.",
            "Manual live-local commands require explicit operator opt-in.",
            "Raw outputs remain local and ignored until reviewed normalization approves public-safe evidence.",
            "The hosted provider path is deferred and separated from local/open-weight rankings.",
            "No public leaderboard, production-safety proof, third-party reproducibility claim, or private-audit overclaim is made.",
        ],
    }


def validate_public_report(report: dict[str, Any], context: str) -> None:
    validate_expected_map(report["quality_gate"], EXPECTED_QUALITY_GATE, f"{context}.report.quality_gate")
    validate_expected_map(report["safety_assertions"], EXPECTED_SAFETY, f"{context}.report.safety_assertions")
    text = str(report)
    for marker in BLOCKED_MARKERS:
        if marker in text:
            raise RealModelProofRunbookError(f"{context}.report contains blocked marker: {marker}")


def generate_markdown(report: dict[str, Any]) -> str:
    evidence = report["evidence_status"]
    gate = report["publication_gate"]
    lines = [
        "# Real Model Proof Runbook",
        "",
        "This M76 runbook shows the next manual CLI path to a controlled, opt-in local/open-weight proof point. It does not execute live models.",
        "",
        "## Current Status",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Runtime | `{report['local_runtime']['runtime']}` |",
        f"| Target split | `{evidence['target_split']}` |",
        f"| Cases per primary model | {evidence['required_cases_per_primary_model']} |",
        f"| Eligible reviewed ledgers | {evidence['eligible_reviewed_live_local_ledgers']} / {evidence['required_eligible_ledgers']} |",
        f"| Review queue | {report['review_queue']['records_waiting_for_review']} waiting, {report['review_queue']['needs_discussion_count']} unresolved |",
        f"| Local ranking claim allowed | `{str(gate['local_ranking_claim_allowed']).lower()}` |",
        "",
        "## M80 Second Target Decision",
        "",
        f"- Decision: {report['second_target_decision']['decision']}",
        f"- Selected target: `{report['second_target_decision']['selected_model']}` via `{report['second_target_decision']['selected_adapter']}` over `{report['second_target_decision']['selected_split']}`.",
        f"- Replaced/deferred target: `{report['second_target_decision']['replaced_model']}`.",
        f"- Rationale: {report['second_target_decision']['rationale']}",
        f"- Claim language: {report['second_target_decision']['publication_claim_language']}",
        f"- Decision required live execution: `{str(report['second_target_decision']['live_execution_required_for_decision']).lower()}`",
        "",
        "Pre-execution requirements:",
        "",
        "\n".join(f"- {item}" for item in report["second_target_decision"]["pre_execution_requirements"]),
        "",
        "## Next Commands",
        "",
    ]
    for command in report["operator_commands"]:
        live_label = "live" if command["live_execution"] else "non-live"
        lines.extend(
            [
                f"### {command['label']}",
                "",
                f"`{command['command']}`",
                "",
                f"- Execution: `{live_label}`",
                f"- Raw outputs committed: `{str(command['commits_raw_outputs']).lower()}`",
                f"- Notes: {command['notes']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Publication Gate",
            "",
            f"- Blocked reason: {gate['blocked_reason']}",
            "\n".join(f"- {item}" for item in gate["unlock_requirements"]),
            "",
            "## Boundaries",
            "",
            "\n".join(f"- {boundary}" for boundary in report["boundaries"]),
            "",
        ]
    )
    return "\n".join(lines)


def validate_expected_map(value: dict[str, Any], expected: dict[str, Any], context: str) -> None:
    for field_name, expected_value in expected.items():
        if value[field_name] != expected_value:
            raise RealModelProofRunbookError(f"{context}.{field_name} must equal {expected_value!r}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the real-model proof operator runbook.")
    parser.add_argument("runbook", nargs="?", type=Path, default=DEFAULT_RUNBOOK_PATH)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON_PATH)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MARKDOWN_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        report = generate_real_model_proof_runbook(args.runbook, args.schema, args.report_json, args.report_md)
    except (RealModelProofRunbookError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"real-model proof runbook: {report['source_runbook_path']}")
    print(f"eligible reviewed ledgers: {report['evidence_status']['eligible_reviewed_live_local_ledgers']}")
    print(f"local ranking claim allowed: {str(report['publication_gate']['local_ranking_claim_allowed']).lower()}")
    print("real-model proof runbook generation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
