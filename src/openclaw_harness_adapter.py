"""Generate the M63 public-safe OpenClaw harness smoke fixture.

This adapter is a deterministic, metadata-only stand-in for a future opt-in
OpenClaw harness. It emits normalized saved-transcript and tool-summary
evidence from a committed public-safe plan. It does not launch OpenClaw, execute
tools, read raw runtime logs, call networks, use credentials, mutate files, or
perform external actions.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from replay_saved_transcripts import validate_transcript_shape, validate_transcripts
from reporting_utils import atomic_write_text
from run_eval import CASE_PATHS, load_cases
from schema_validation_utils import display_path, load_json_object, validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN_PATH = REPO_ROOT / "traces/external/openclaw_harness_adapter_plan.example.json"
DEFAULT_PLAN_SCHEMA_PATH = REPO_ROOT / "schemas/openclaw_harness_adapter.schema.json"
SAVED_TRANSCRIPT_SCHEMA_PATH = REPO_ROOT / "schemas/saved_transcript.schema.json"
TOOL_CALL_SUMMARY_SCHEMA_PATH = REPO_ROOT / "schemas/tool_call_summary.schema.json"
EXPECTED_SAFE_ASSERTIONS = {
    "public_safe": True,
    "live_execution": False,
    "tool_execution": False,
    "external_actions": False,
    "contains_private_data": False,
    "credentials_required": False,
    "raw_private_logs": False,
}


class OpenClawHarnessAdapterError(Exception):
    """OpenClaw harness adapter validation or generation error."""


def generate_smoke_fixture(
    plan_path: Path = DEFAULT_PLAN_PATH,
    plan_schema_path: Path = DEFAULT_PLAN_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the M63 plan and emit public-safe smoke artifacts."""

    plan_schema = load_json_object(plan_schema_path, "openclaw harness adapter schema", repo_root, OpenClawHarnessAdapterError)
    plan = load_json_object(plan_path, "openclaw harness adapter plan", repo_root, OpenClawHarnessAdapterError)
    context = display_path(plan_path, repo_root)
    validate_schema_value(plan, plan_schema, context, plan_path, repo_root, OpenClawHarnessAdapterError)
    validate_utc_timestamp(plan["created_at"], f"{context}.created_at")
    validate_plan_semantics(plan, context, repo_root)

    transcript_output_path = require_repo_path(plan["outputs"]["normalized_transcript_path"], f"{context}.outputs.normalized_transcript_path", repo_root)
    tool_summary_output_path = require_repo_path(plan["outputs"]["tool_summary_path"], f"{context}.outputs.tool_summary_path", repo_root)
    transcript = dict(plan["smoke_transcript"])
    tool_summaries = [dict(summary) for summary in plan["tool_call_summaries"]]

    validate_smoke_transcript(transcript, transcript_output_path, repo_root)
    validate_tool_summaries(tool_summaries, tool_summary_output_path, plan_path, repo_root)
    write_jsonl(transcript_output_path, [transcript])
    write_jsonl(tool_summary_output_path, tool_summaries)

    return {
        "plan_path": context,
        "schema_path": display_path(plan_schema_path, repo_root),
        "adapter_id": str(plan["adapter_id"]),
        "target_runtime": str(plan["target_runtime"]),
        "target_profile": str(plan["target_profile"]),
        "transcript_output_path": display_path(transcript_output_path, repo_root),
        "tool_summary_output_path": display_path(tool_summary_output_path, repo_root),
        "raw_output_path": str(plan["outputs"]["raw_output_path"]),
        "transcripts": 1,
        "tool_summaries": len(tool_summaries),
        "live_openclaw_execution_in_quality_gate": plan["quality_gate"]["live_openclaw_execution_in_quality_gate"],
    }


def validate_plan_semantics(plan: dict[str, Any], context: str, repo_root: Path) -> None:
    """Validate opt-in, sandbox, output, promotion, and safety semantics."""

    if plan["target_runtime"] != "openclaw":
        raise OpenClawHarnessAdapterError(f"{context}.target_runtime must be openclaw")
    if plan["target_profile"] != "openclaw_reference_agent":
        raise OpenClawHarnessAdapterError(f"{context}.target_profile must be openclaw_reference_agent")

    contract_path = require_existing_repo_path(plan["sandbox_contract_path"], f"{context}.sandbox_contract_path", repo_root)
    if contract_path.name != "tool_sandbox_contract.example.json":
        raise OpenClawHarnessAdapterError(f"{context}.sandbox_contract_path must reference the M61 sandbox contract")

    validate_case_selection(plan["case_selection"], f"{context}.case_selection", repo_root)
    validate_runtime_controls(plan["runtime_controls"], f"{context}.runtime_controls")
    validate_outputs(plan["outputs"], f"{context}.outputs", repo_root)
    validate_promotion_path(plan["promotion_path"], f"{context}.promotion_path", repo_root)
    validate_quality_gate(plan["quality_gate"], f"{context}.quality_gate")
    validate_safety_assertions(plan["safety_assertions"], f"{context}.safety_assertions")

    transcript = plan["smoke_transcript"]
    if transcript["target_profile"] != plan["target_profile"]:
        raise OpenClawHarnessAdapterError(f"{context}.smoke_transcript.target_profile must match target_profile")
    if transcript["case_id"] not in plan["case_selection"]["case_ids"]:
        raise OpenClawHarnessAdapterError(f"{context}.smoke_transcript.case_id must be selected in case_selection")


def validate_case_selection(value: dict[str, Any], context: str, repo_root: Path) -> None:
    case_ids = [str(case_id) for case_id in value["case_ids"]]
    if int(value["case_count"]) != len(case_ids):
        raise OpenClawHarnessAdapterError(f"{context}.case_count must match case_ids length")
    for index, source_path in enumerate(value["case_source_paths"]):
        resolved = require_existing_repo_path(source_path, f"{context}.case_source_paths[{index}]", repo_root)
        if resolved.suffix != ".jsonl":
            raise OpenClawHarnessAdapterError(f"{context}.case_source_paths[{index}] must point to JSONL")

    known_case_ids = {str(case["case_id"]) for case in load_cases(CASE_PATHS)}
    unknown = sorted(set(case_ids) - known_case_ids)
    if unknown:
        raise OpenClawHarnessAdapterError(f"{context}.case_ids contains unknown case IDs: {', '.join(unknown)}")


def validate_runtime_controls(value: dict[str, Any], context: str) -> None:
    expected_true = ["opt_in_required", "tools_disabled_or_sandboxed", "raw_output_local_only", "disposable_workspace_required"]
    expected_false = ["live_execution_allowed", "network_access", "credentials_required", "external_actions"]
    for field_name in expected_true:
        if value[field_name] is not True:
            raise OpenClawHarnessAdapterError(f"{context}.{field_name} must be true")
    for field_name in expected_false:
        if value[field_name] is not False:
            raise OpenClawHarnessAdapterError(f"{context}.{field_name} must be false")
    if value["opt_in_flag"] != "--live-openclaw":
        raise OpenClawHarnessAdapterError(f"{context}.opt_in_flag must be --live-openclaw")
    if value["environment_variable"] != "AGENT_EVALS_ENABLE_LIVE_OPENCLAW":
        raise OpenClawHarnessAdapterError(
            f"{context}.environment_variable must be AGENT_EVALS_ENABLE_LIVE_OPENCLAW"
        )


def validate_outputs(value: dict[str, Any], context: str, repo_root: Path) -> None:
    raw_output_path = require_repo_path(value["raw_output_path"], f"{context}.raw_output_path", repo_root)
    transcript_path = require_repo_path(value["normalized_transcript_path"], f"{context}.normalized_transcript_path", repo_root)
    tool_summary_path = require_repo_path(value["tool_summary_path"], f"{context}.tool_summary_path", repo_root)
    scored_trace_path = require_repo_path(value["scored_trace_path"], f"{context}.scored_trace_path", repo_root)
    report_path = require_repo_path(value["report_path"], f"{context}.report_path", repo_root)

    require_path_under(raw_output_path, repo_root / "traces/raw", f"{context}.raw_output_path")
    require_path_under(transcript_path, repo_root / "traces/external", f"{context}.normalized_transcript_path")
    require_path_under(tool_summary_path, repo_root / "traces/external", f"{context}.tool_summary_path")
    require_path_under(scored_trace_path, repo_root / "traces/scored", f"{context}.scored_trace_path")
    require_path_under(report_path, repo_root / "reports/comparisons", f"{context}.report_path")

    if not raw_output_path.name.endswith(".local.jsonl"):
        raise OpenClawHarnessAdapterError(f"{context}.raw_output_path must end with .local.jsonl")
    if not transcript_path.name.endswith(".example.jsonl"):
        raise OpenClawHarnessAdapterError(f"{context}.normalized_transcript_path must end with .example.jsonl")
    if not tool_summary_path.name.endswith(".example.jsonl"):
        raise OpenClawHarnessAdapterError(f"{context}.tool_summary_path must end with .example.jsonl")
    if not scored_trace_path.name.endswith(".jsonl"):
        raise OpenClawHarnessAdapterError(f"{context}.scored_trace_path must end with .jsonl")
    if report_path.suffix != ".md":
        raise OpenClawHarnessAdapterError(f"{context}.report_path must point to Markdown")
    if value["raw_outputs_committable"] is not False:
        raise OpenClawHarnessAdapterError(f"{context}.raw_outputs_committable must be false")
    if value["normalized_outputs_committable"] is not True:
        raise OpenClawHarnessAdapterError(f"{context}.normalized_outputs_committable must be true")
    if raw_output_path.exists():
        raise OpenClawHarnessAdapterError(f"{context}.raw_output_path must not exist in committed fixtures")


def validate_promotion_path(value: dict[str, Any], context: str, repo_root: Path) -> None:
    validator = require_existing_repo_path(value["validator"], f"{context}.validator", repo_root)
    if validator.name != "replay_saved_transcripts.py":
        raise OpenClawHarnessAdapterError(f"{context}.validator must be src/replay_saved_transcripts.py")
    if "src/replay_saved_transcripts.py" not in value["replay_command"]:
        raise OpenClawHarnessAdapterError(f"{context}.replay_command must use saved transcript replay")
    if value["review_notes_required"] is not True:
        raise OpenClawHarnessAdapterError(f"{context}.review_notes_required must be true")
    if value["private_raw_output_retained"] is not False:
        raise OpenClawHarnessAdapterError(f"{context}.private_raw_output_retained must be false")


def validate_quality_gate(value: dict[str, Any], context: str) -> None:
    expected_true = [
        "adapter_plan_validation_in_quality_gate",
        "public_safe_fixture_generation_in_quality_gate",
        "saved_transcript_replay_in_quality_gate",
    ]
    expected_false = [
        "live_openclaw_execution_in_quality_gate",
        "tool_execution_in_quality_gate",
        "raw_output_validation_in_quality_gate",
    ]
    for field_name in expected_true:
        if value[field_name] is not True:
            raise OpenClawHarnessAdapterError(f"{context}.{field_name} must be true")
    for field_name in expected_false:
        if value[field_name] is not False:
            raise OpenClawHarnessAdapterError(f"{context}.{field_name} must be false")


def validate_safety_assertions(value: dict[str, Any], context: str) -> None:
    if value != EXPECTED_SAFE_ASSERTIONS:
        raise OpenClawHarnessAdapterError(f"{context} must match public-safe no-execution assertions")


def validate_smoke_transcript(transcript: dict[str, Any], output_path: Path, repo_root: Path) -> None:
    schema = load_json_object(SAVED_TRANSCRIPT_SCHEMA_PATH, "saved transcript schema", repo_root, OpenClawHarnessAdapterError)
    validate_schema_value(transcript, schema, display_path(output_path, repo_root), output_path, repo_root, OpenClawHarnessAdapterError)
    validate_transcript_shape(transcript, output_path, 1, schema)
    cases = load_cases(CASE_PATHS)
    validate_transcripts([transcript], {str(case["case_id"]): case for case in cases}, output_path)
    if transcript["source_label"] != "openclaw_harness_smoke_public_safe":
        raise OpenClawHarnessAdapterError("smoke_transcript.source_label must label OpenClaw as the target")
    if "Agent Behavior Evals Lab remains the evaluator" not in str(transcript.get("notes", "")):
        raise OpenClawHarnessAdapterError("smoke_transcript.notes must preserve evaluator/target boundary")


def validate_tool_summaries(
    summaries: list[dict[str, Any]],
    output_path: Path,
    plan_path: Path,
    repo_root: Path,
) -> None:
    schema = load_json_object(TOOL_CALL_SUMMARY_SCHEMA_PATH, "tool call summary schema", repo_root, OpenClawHarnessAdapterError)
    temp_path = output_path
    for index, summary in enumerate(summaries, start=1):
        validate_schema_value(summary, schema, f"{display_path(output_path, repo_root)}:{index}", temp_path, repo_root, OpenClawHarnessAdapterError)
        if summary["source_evidence"]["source_path"] != display_path(plan_path, repo_root):
            raise OpenClawHarnessAdapterError(f"{display_path(output_path, repo_root)}:{index}.source_path must reference plan")
        if summary["tool_surface"] != "external_action":
            raise OpenClawHarnessAdapterError(f"{display_path(output_path, repo_root)}:{index}.tool_surface must be external_action")
        if summary["contract_id"] != "m61_sandboxed_tool_runtime_contract":
            raise OpenClawHarnessAdapterError(
                f"{display_path(output_path, repo_root)}:{index}.contract_id must reference M61 contract"
            )
        if summary["action_status"] != "approval_requested_not_executed":
            raise OpenClawHarnessAdapterError(
                f"{display_path(output_path, repo_root)}:{index}.action_status must be approval_requested_not_executed"
            )
        if summary["approval_request"]["requested"] is not True:
            raise OpenClawHarnessAdapterError(
                f"{display_path(output_path, repo_root)}:{index}.approval_request.requested must be true"
            )
        if any(value is not False for value in summary["side_effects"].values()):
            raise OpenClawHarnessAdapterError(f"{display_path(output_path, repo_root)}:{index}.side_effects must all be false")


def write_jsonl(output_path: Path, records: list[dict[str, Any]]) -> None:
    atomic_write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        output_path,
    )


def validate_utc_timestamp(value: Any, context: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise OpenClawHarnessAdapterError(f"{context} must be a non-empty string")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise OpenClawHarnessAdapterError(f"{context} must be a valid UTC timestamp") from exc


def require_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise OpenClawHarnessAdapterError(f"{context} must be a non-empty string")
    path = Path(value)
    if path.is_absolute():
        raise OpenClawHarnessAdapterError(f"{context} must be a repository-relative path")
    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise OpenClawHarnessAdapterError(f"{context} must stay within the repository") from exc
    return resolved


def require_existing_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    path = require_repo_path(value, context, repo_root)
    if not path.exists():
        raise OpenClawHarnessAdapterError(f"{context} does not exist: {display_path(path, repo_root)}")
    return path


def require_path_under(path: Path, parent: Path, context: str) -> None:
    try:
        path.relative_to(parent.resolve())
    except ValueError as exc:
        raise OpenClawHarnessAdapterError(f"{context} must stay under {display_path(parent.resolve())}") from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the M63 public-safe OpenClaw harness smoke fixture.")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DEFAULT_PLAN_PATH,
        help="OpenClaw harness adapter plan JSON path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = generate_smoke_fixture(args.path)
    except (OpenClawHarnessAdapterError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"openclaw harness plan path: {summary['plan_path']}")
    print(f"openclaw harness schema path: {summary['schema_path']}")
    print(f"adapter id: {summary['adapter_id']}")
    print(f"target runtime: {summary['target_runtime']}")
    print(f"target profile: {summary['target_profile']}")
    print(f"normalized transcript path: {summary['transcript_output_path']}")
    print(f"tool summary path: {summary['tool_summary_output_path']}")
    print(f"raw output path: {summary['raw_output_path']}")
    print(f"transcripts emitted: {summary['transcripts']}")
    print(f"tool summaries emitted: {summary['tool_summaries']}")
    print(f"live OpenClaw execution in quality gate: {str(summary['live_openclaw_execution_in_quality_gate']).lower()}")
    print("openclaw harness smoke fixture generation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
