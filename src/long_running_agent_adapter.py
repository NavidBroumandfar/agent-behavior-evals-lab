"""Generate the M64 public-safe Hermes long-running agent fixture.

This adapter is a deterministic, metadata-only stand-in for a future opt-in
Hermes or memory-capable agent adapter. It emits public-safe saved transcripts,
session-boundary metadata, and memory checks from a committed plan. It does not
launch Hermes, execute tools, read private memory, read raw runtime logs, call
networks, use credentials, mutate files, or perform external actions.
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
from target_registry import allowed_manual_output_profiles


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN_PATH = REPO_ROOT / "traces/external/long_running_agent_adapter_plan.example.json"
DEFAULT_PLAN_SCHEMA_PATH = REPO_ROOT / "schemas/long_running_agent_adapter.schema.json"
SAVED_TRANSCRIPT_SCHEMA_PATH = REPO_ROOT / "schemas/saved_transcript.schema.json"
SESSION_BOUNDARY_SCHEMA_PATH = REPO_ROOT / "schemas/session_boundary_metadata.schema.json"
MEMORY_CHECK_SCHEMA_PATH = REPO_ROOT / "schemas/memory_persistence_check.schema.json"

EXPECTED_SAFE_ASSERTIONS = {
    "public_safe": True,
    "live_execution": False,
    "tool_execution": False,
    "external_actions": False,
    "contains_private_data": False,
    "credentials_required": False,
    "raw_private_logs": False,
    "private_memory": False,
}
REQUIRED_MEMORY_CHECK_TYPES = {
    "memory_disclosure",
    "persistence_boundary",
    "approval_continuity",
    "uncertainty_boundary",
}


class LongRunningAgentAdapterError(Exception):
    """Long-running agent adapter validation or generation error."""


def generate_session_fixture(
    plan_path: Path = DEFAULT_PLAN_PATH,
    plan_schema_path: Path = DEFAULT_PLAN_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the M64 plan and emit public-safe session artifacts."""

    plan_schema = load_json_object(
        plan_schema_path,
        "long-running agent adapter schema",
        repo_root,
        LongRunningAgentAdapterError,
    )
    plan = load_json_object(plan_path, "long-running agent adapter plan", repo_root, LongRunningAgentAdapterError)
    context = display_path(plan_path, repo_root)
    validate_schema_value(plan, plan_schema, context, plan_path, repo_root, LongRunningAgentAdapterError)
    validate_utc_timestamp(plan["created_at"], f"{context}.created_at")
    validate_plan_semantics(plan, context, repo_root)

    transcript_output_path = require_repo_path(
        plan["outputs"]["normalized_transcript_path"],
        f"{context}.outputs.normalized_transcript_path",
        repo_root,
    )
    session_boundary_output_path = require_repo_path(
        plan["outputs"]["session_boundary_path"],
        f"{context}.outputs.session_boundary_path",
        repo_root,
    )
    memory_check_output_path = require_repo_path(
        plan["outputs"]["memory_check_path"],
        f"{context}.outputs.memory_check_path",
        repo_root,
    )

    transcripts = [dict(transcript) for transcript in plan["smoke_transcripts"]]
    session_boundaries = [dict(boundary) for boundary in plan["session_boundaries"]]
    memory_checks = [dict(check) for check in plan["memory_checks"]]

    validate_smoke_transcripts(transcripts, transcript_output_path, repo_root)
    validate_session_boundaries(session_boundaries, transcripts, session_boundary_output_path, plan, repo_root)
    validate_memory_checks(memory_checks, transcripts, session_boundaries, memory_check_output_path, plan, repo_root)

    write_jsonl(transcript_output_path, transcripts)
    write_jsonl(session_boundary_output_path, session_boundaries)
    write_jsonl(memory_check_output_path, memory_checks)

    return {
        "plan_path": context,
        "schema_path": display_path(plan_schema_path, repo_root),
        "adapter_id": str(plan["adapter_id"]),
        "target_runtime": str(plan["target_runtime"]),
        "target_profile": str(plan["target_profile"]),
        "transcript_output_path": display_path(transcript_output_path, repo_root),
        "session_boundary_output_path": display_path(session_boundary_output_path, repo_root),
        "memory_check_output_path": display_path(memory_check_output_path, repo_root),
        "raw_output_path": str(plan["outputs"]["raw_output_path"]),
        "raw_memory_path": str(plan["outputs"]["raw_memory_path"]),
        "transcripts": len(transcripts),
        "session_boundaries": len(session_boundaries),
        "memory_checks": len(memory_checks),
        "live_hermes_execution_in_quality_gate": plan["quality_gate"]["live_hermes_execution_in_quality_gate"],
        "private_memory_read_in_quality_gate": plan["quality_gate"]["private_memory_read_in_quality_gate"],
    }


def validate_plan_semantics(plan: dict[str, Any], context: str, repo_root: Path) -> None:
    """Validate target labeling, opt-in controls, outputs, memory controls, and safety."""

    if plan["target_runtime"] != "hermes":
        raise LongRunningAgentAdapterError(f"{context}.target_runtime must be hermes")
    if plan["target_profile"] != "hermes_long_running_agent":
        raise LongRunningAgentAdapterError(f"{context}.target_profile must be hermes_long_running_agent")
    if plan["target_profile"] not in allowed_manual_output_profiles():
        raise LongRunningAgentAdapterError(f"{context}.target_profile must be registered for saved transcript replay")

    contract_path = require_existing_repo_path(plan["sandbox_contract_path"], f"{context}.sandbox_contract_path", repo_root)
    if contract_path.name != "tool_sandbox_contract.example.json":
        raise LongRunningAgentAdapterError(f"{context}.sandbox_contract_path must reference the M61 sandbox contract")

    validate_case_selection(plan["case_selection"], f"{context}.case_selection", repo_root)
    validate_runtime_controls(plan["runtime_controls"], f"{context}.runtime_controls")
    validate_outputs(plan["outputs"], f"{context}.outputs", repo_root)
    validate_memory_controls(plan["memory_controls"], f"{context}.memory_controls")
    validate_promotion_path(plan["promotion_path"], f"{context}.promotion_path", repo_root)
    validate_quality_gate(plan["quality_gate"], f"{context}.quality_gate")
    validate_safety_assertions(plan["safety_assertions"], f"{context}.safety_assertions")

    selected_case_ids = set(str(case_id) for case_id in plan["case_selection"]["case_ids"])
    for index, transcript in enumerate(plan["smoke_transcripts"]):
        transcript_context = f"{context}.smoke_transcripts[{index}]"
        if transcript["target_profile"] != plan["target_profile"]:
            raise LongRunningAgentAdapterError(f"{transcript_context}.target_profile must match target_profile")
        if transcript["case_id"] not in selected_case_ids:
            raise LongRunningAgentAdapterError(f"{transcript_context}.case_id must be selected in case_selection")


def validate_case_selection(value: dict[str, Any], context: str, repo_root: Path) -> None:
    case_ids = [str(case_id) for case_id in value["case_ids"]]
    if int(value["case_count"]) != len(case_ids):
        raise LongRunningAgentAdapterError(f"{context}.case_count must match case_ids length")
    for index, source_path in enumerate(value["case_source_paths"]):
        resolved = require_existing_repo_path(source_path, f"{context}.case_source_paths[{index}]", repo_root)
        if resolved.suffix != ".jsonl":
            raise LongRunningAgentAdapterError(f"{context}.case_source_paths[{index}] must point to JSONL")

    known_case_ids = {str(case["case_id"]) for case in load_cases(CASE_PATHS)}
    unknown = sorted(set(case_ids) - known_case_ids)
    if unknown:
        raise LongRunningAgentAdapterError(f"{context}.case_ids contains unknown case IDs: {', '.join(unknown)}")


def validate_runtime_controls(value: dict[str, Any], context: str) -> None:
    expected_true = [
        "opt_in_required",
        "tools_disabled_or_sandboxed",
        "raw_output_local_only",
        "disposable_workspace_required",
        "public_safe_memory_summary_allowed",
    ]
    expected_false = [
        "live_execution_allowed",
        "network_access",
        "credentials_required",
        "external_actions",
        "private_memory_read_allowed",
    ]
    for field_name in expected_true:
        if value[field_name] is not True:
            raise LongRunningAgentAdapterError(f"{context}.{field_name} must be true")
    for field_name in expected_false:
        if value[field_name] is not False:
            raise LongRunningAgentAdapterError(f"{context}.{field_name} must be false")
    if value["opt_in_flag"] != "--live-hermes":
        raise LongRunningAgentAdapterError(f"{context}.opt_in_flag must be --live-hermes")
    if value["environment_variable"] != "AGENT_EVALS_ENABLE_LIVE_HERMES":
        raise LongRunningAgentAdapterError(
            f"{context}.environment_variable must be AGENT_EVALS_ENABLE_LIVE_HERMES"
        )


def validate_outputs(value: dict[str, Any], context: str, repo_root: Path) -> None:
    raw_output_path = require_repo_path(value["raw_output_path"], f"{context}.raw_output_path", repo_root)
    raw_memory_path = require_repo_path(value["raw_memory_path"], f"{context}.raw_memory_path", repo_root)
    transcript_path = require_repo_path(value["normalized_transcript_path"], f"{context}.normalized_transcript_path", repo_root)
    session_boundary_path = require_repo_path(value["session_boundary_path"], f"{context}.session_boundary_path", repo_root)
    memory_check_path = require_repo_path(value["memory_check_path"], f"{context}.memory_check_path", repo_root)
    scored_trace_path = require_repo_path(value["scored_trace_path"], f"{context}.scored_trace_path", repo_root)
    report_path = require_repo_path(value["report_path"], f"{context}.report_path", repo_root)

    require_path_under(raw_output_path, repo_root / "traces/raw", f"{context}.raw_output_path")
    require_path_under(raw_memory_path, repo_root / "traces/raw", f"{context}.raw_memory_path")
    require_path_under(transcript_path, repo_root / "traces/external", f"{context}.normalized_transcript_path")
    require_path_under(session_boundary_path, repo_root / "traces/external", f"{context}.session_boundary_path")
    require_path_under(memory_check_path, repo_root / "traces/external", f"{context}.memory_check_path")
    require_path_under(scored_trace_path, repo_root / "traces/scored", f"{context}.scored_trace_path")
    require_path_under(report_path, repo_root / "reports/comparisons", f"{context}.report_path")

    for field_name, path in [
        ("raw_output_path", raw_output_path),
        ("raw_memory_path", raw_memory_path),
    ]:
        if not path.name.endswith(".local.jsonl"):
            raise LongRunningAgentAdapterError(f"{context}.{field_name} must end with .local.jsonl")
        if path.exists():
            raise LongRunningAgentAdapterError(f"{context}.{field_name} must not exist in committed fixtures")

    for field_name, path in [
        ("normalized_transcript_path", transcript_path),
        ("session_boundary_path", session_boundary_path),
        ("memory_check_path", memory_check_path),
    ]:
        if not path.name.endswith(".example.jsonl"):
            raise LongRunningAgentAdapterError(f"{context}.{field_name} must end with .example.jsonl")
    if not scored_trace_path.name.endswith(".jsonl"):
        raise LongRunningAgentAdapterError(f"{context}.scored_trace_path must end with .jsonl")
    if report_path.suffix != ".md":
        raise LongRunningAgentAdapterError(f"{context}.report_path must point to Markdown")

    if value["raw_outputs_committable"] is not False:
        raise LongRunningAgentAdapterError(f"{context}.raw_outputs_committable must be false")
    if value["private_memory_committable"] is not False:
        raise LongRunningAgentAdapterError(f"{context}.private_memory_committable must be false")
    if value["public_derivatives_committable"] is not True:
        raise LongRunningAgentAdapterError(f"{context}.public_derivatives_committable must be true")


def validate_memory_controls(value: dict[str, Any], context: str) -> None:
    expected_true = [
        "raw_memory_local_only",
        "public_safe_derivatives_only",
        "discloses_memory_scope",
        "uncertainty_when_boundary_missing",
        "previous_approval_requires_current_confirmation",
        "prohibits_private_memory_reconstruction",
    ]
    for field_name in expected_true:
        if value[field_name] is not True:
            raise LongRunningAgentAdapterError(f"{context}.{field_name} must be true")
    if value["private_memory_committable"] is not False:
        raise LongRunningAgentAdapterError(f"{context}.private_memory_committable must be false")


def validate_promotion_path(value: dict[str, Any], context: str, repo_root: Path) -> None:
    validator = require_existing_repo_path(value["validator"], f"{context}.validator", repo_root)
    if validator.name != "replay_saved_transcripts.py":
        raise LongRunningAgentAdapterError(f"{context}.validator must be src/replay_saved_transcripts.py")
    if "src/replay_saved_transcripts.py" not in value["replay_command"]:
        raise LongRunningAgentAdapterError(f"{context}.replay_command must use saved transcript replay")
    for field_name in ["review_notes_required"]:
        if value[field_name] is not True:
            raise LongRunningAgentAdapterError(f"{context}.{field_name} must be true")
    for field_name in ["private_raw_output_retained", "private_memory_retained"]:
        if value[field_name] is not False:
            raise LongRunningAgentAdapterError(f"{context}.{field_name} must be false")


def validate_quality_gate(value: dict[str, Any], context: str) -> None:
    expected_true = [
        "adapter_plan_validation_in_quality_gate",
        "public_safe_fixture_generation_in_quality_gate",
        "session_boundary_metadata_validation_in_quality_gate",
        "memory_check_validation_in_quality_gate",
        "saved_transcript_replay_in_quality_gate",
    ]
    expected_false = [
        "live_hermes_execution_in_quality_gate",
        "local_model_execution_in_quality_gate",
        "private_memory_read_in_quality_gate",
        "tool_execution_in_quality_gate",
        "raw_output_validation_in_quality_gate",
    ]
    for field_name in expected_true:
        if value[field_name] is not True:
            raise LongRunningAgentAdapterError(f"{context}.{field_name} must be true")
    for field_name in expected_false:
        if value[field_name] is not False:
            raise LongRunningAgentAdapterError(f"{context}.{field_name} must be false")


def validate_safety_assertions(value: dict[str, Any], context: str) -> None:
    if value != EXPECTED_SAFE_ASSERTIONS:
        raise LongRunningAgentAdapterError(f"{context} must match public-safe no-memory/no-execution assertions")


def validate_smoke_transcripts(transcripts: list[dict[str, Any]], output_path: Path, repo_root: Path) -> None:
    schema = load_json_object(SAVED_TRANSCRIPT_SCHEMA_PATH, "saved transcript schema", repo_root, LongRunningAgentAdapterError)
    for index, transcript in enumerate(transcripts, start=1):
        validate_schema_value(
            transcript,
            schema,
            f"{display_path(output_path, repo_root)}:{index}",
            output_path,
            repo_root,
            LongRunningAgentAdapterError,
        )
        validate_transcript_shape(transcript, output_path, index, schema)
        if transcript["source_label"] != "hermes_long_running_memory_public_safe":
            raise LongRunningAgentAdapterError(
                f"{display_path(output_path, repo_root)}:{index}.source_label must label Hermes as the target"
            )
        if "Agent Behavior Evals Lab remains the evaluator" not in str(transcript.get("notes", "")):
            raise LongRunningAgentAdapterError(
                f"{display_path(output_path, repo_root)}:{index}.notes must preserve evaluator/target boundary"
            )
    cases = load_cases(CASE_PATHS)
    validate_transcripts(transcripts, {str(case["case_id"]): case for case in cases}, output_path)


def validate_session_boundaries(
    boundaries: list[dict[str, Any]],
    transcripts: list[dict[str, Any]],
    output_path: Path,
    plan: dict[str, Any],
    repo_root: Path,
) -> None:
    schema = load_json_object(SESSION_BOUNDARY_SCHEMA_PATH, "session boundary metadata schema", repo_root, LongRunningAgentAdapterError)
    transcript_ids = {str(transcript["transcript_id"]) for transcript in transcripts}
    seen_boundary_ids: set[str] = set()
    seen_session_ids: set[str] = set()
    cross_session_seen = False

    for index, boundary in enumerate(boundaries, start=1):
        context = f"{display_path(output_path, repo_root)}:{index}"
        validate_schema_value(boundary, schema, context, output_path, repo_root, LongRunningAgentAdapterError)
        validate_utc_timestamp(boundary["created_at"], f"{context}.created_at")
        validate_safety_assertions(boundary["safety_assertions"], f"{context}.safety_assertions")
        if boundary["adapter_id"] != plan["adapter_id"]:
            raise LongRunningAgentAdapterError(f"{context}.adapter_id must match plan adapter_id")
        if boundary["target_runtime"] != plan["target_runtime"]:
            raise LongRunningAgentAdapterError(f"{context}.target_runtime must match plan target_runtime")
        if boundary["target_profile"] != plan["target_profile"]:
            raise LongRunningAgentAdapterError(f"{context}.target_profile must match plan target_profile")
        if boundary["private_memory_included"] is not False or boundary["raw_memory_included"] is not False:
            raise LongRunningAgentAdapterError(f"{context} must not include private or raw memory")

        boundary_id = str(boundary["boundary_id"])
        session_id = str(boundary["session_id"])
        if boundary_id in seen_boundary_ids:
            raise LongRunningAgentAdapterError(f"{context}.boundary_id duplicate value: {boundary_id}")
        if session_id in seen_session_ids:
            raise LongRunningAgentAdapterError(f"{context}.session_id duplicate value: {session_id}")
        seen_boundary_ids.add(boundary_id)

        if "previous_session_id" in boundary and boundary["previous_session_id"] not in seen_session_ids:
            raise LongRunningAgentAdapterError(f"{context}.previous_session_id must reference an earlier session")
        seen_session_ids.add(session_id)

        unknown_transcripts = sorted(set(str(item) for item in boundary["transcript_ids"]) - transcript_ids)
        if unknown_transcripts:
            raise LongRunningAgentAdapterError(
                f"{context}.transcript_ids contains unknown transcript IDs: {', '.join(unknown_transcripts)}"
            )
        if boundary["boundary_type"] == "cross_session_replay":
            cross_session_seen = True
            if boundary["memory_summary_available"] is not True:
                raise LongRunningAgentAdapterError(f"{context}.memory_summary_available must be true for cross-session replay")
            if boundary["memory_summary_scope"] != "public_safe_summary_only":
                raise LongRunningAgentAdapterError(f"{context}.memory_summary_scope must be public_safe_summary_only")

    if not cross_session_seen:
        raise LongRunningAgentAdapterError(f"{display_path(output_path, repo_root)} must include a cross_session_replay boundary")


def validate_memory_checks(
    checks: list[dict[str, Any]],
    transcripts: list[dict[str, Any]],
    boundaries: list[dict[str, Any]],
    output_path: Path,
    plan: dict[str, Any],
    repo_root: Path,
) -> None:
    schema = load_json_object(MEMORY_CHECK_SCHEMA_PATH, "memory persistence check schema", repo_root, LongRunningAgentAdapterError)
    transcript_by_id = {str(transcript["transcript_id"]): transcript for transcript in transcripts}
    session_ids = {str(boundary["session_id"]) for boundary in boundaries}
    seen_check_ids: set[str] = set()
    seen_check_types: set[str] = set()

    for index, check in enumerate(checks, start=1):
        context = f"{display_path(output_path, repo_root)}:{index}"
        validate_schema_value(check, schema, context, output_path, repo_root, LongRunningAgentAdapterError)
        validate_utc_timestamp(check["created_at"], f"{context}.created_at")
        validate_safety_assertions(check["safety_assertions"], f"{context}.safety_assertions")
        if check["adapter_id"] != plan["adapter_id"]:
            raise LongRunningAgentAdapterError(f"{context}.adapter_id must match plan adapter_id")
        if check["target_runtime"] != plan["target_runtime"]:
            raise LongRunningAgentAdapterError(f"{context}.target_runtime must match plan target_runtime")
        if check["target_profile"] != plan["target_profile"]:
            raise LongRunningAgentAdapterError(f"{context}.target_profile must match plan target_profile")
        if check["private_memory_included"] is not False or check["raw_memory_referenced"] is not False:
            raise LongRunningAgentAdapterError(f"{context} must not include or reference private memory")
        if check["passed"] is not True:
            raise LongRunningAgentAdapterError(f"{context}.passed must be true for the M64 public-safe smoke fixture")

        check_id = str(check["check_id"])
        if check_id in seen_check_ids:
            raise LongRunningAgentAdapterError(f"{context}.check_id duplicate value: {check_id}")
        seen_check_ids.add(check_id)
        seen_check_types.add(str(check["check_type"]))

        transcript = transcript_by_id.get(str(check["transcript_id"]))
        if transcript is None:
            raise LongRunningAgentAdapterError(f"{context}.transcript_id must reference a generated transcript")
        if check["case_id"] != transcript["case_id"]:
            raise LongRunningAgentAdapterError(f"{context}.case_id must match referenced transcript")
        if check["selected_turn_id"] != transcript["selected_assistant_turn_id"]:
            raise LongRunningAgentAdapterError(f"{context}.selected_turn_id must match referenced transcript")
        if check["session_id"] not in session_ids:
            raise LongRunningAgentAdapterError(f"{context}.session_id must reference a generated session boundary")
        evidence_path = require_repo_path(check["public_safe_evidence_path"], f"{context}.public_safe_evidence_path", repo_root)
        require_path_under(evidence_path, repo_root / "traces/external", f"{context}.public_safe_evidence_path")
        planned_transcript_path = require_repo_path(
            plan["outputs"]["normalized_transcript_path"],
            f"{context}.planned_transcript_path",
            repo_root,
        )
        if not evidence_path.exists() and evidence_path.resolve() != planned_transcript_path.resolve():
            raise LongRunningAgentAdapterError(
                f"{context}.public_safe_evidence_path does not exist: {display_path(evidence_path, repo_root)}"
            )

    missing_check_types = sorted(REQUIRED_MEMORY_CHECK_TYPES - seen_check_types)
    if missing_check_types:
        raise LongRunningAgentAdapterError(
            f"{display_path(output_path, repo_root)} missing memory check types: {', '.join(missing_check_types)}"
        )


def write_jsonl(output_path: Path, records: list[dict[str, Any]]) -> None:
    atomic_write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        output_path,
    )


def validate_utc_timestamp(value: Any, context: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise LongRunningAgentAdapterError(f"{context} must be a non-empty string")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise LongRunningAgentAdapterError(f"{context} must be a valid UTC timestamp") from exc


def require_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise LongRunningAgentAdapterError(f"{context} must be a non-empty string")
    path = Path(value)
    if path.is_absolute():
        raise LongRunningAgentAdapterError(f"{context} must be a repository-relative path")
    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise LongRunningAgentAdapterError(f"{context} must stay within the repository") from exc
    return resolved


def require_existing_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    path = require_repo_path(value, context, repo_root)
    if not path.exists():
        raise LongRunningAgentAdapterError(f"{context} does not exist: {display_path(path, repo_root)}")
    return path


def require_path_under(path: Path, parent: Path, context: str) -> None:
    try:
        path.relative_to(parent.resolve())
    except ValueError as exc:
        raise LongRunningAgentAdapterError(f"{context} must stay under {display_path(parent.resolve())}") from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the M64 public-safe Hermes long-running agent fixture.")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DEFAULT_PLAN_PATH,
        help="Long-running agent adapter plan JSON path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = generate_session_fixture(args.path)
    except (LongRunningAgentAdapterError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"long-running agent plan path: {summary['plan_path']}")
    print(f"long-running agent schema path: {summary['schema_path']}")
    print(f"adapter id: {summary['adapter_id']}")
    print(f"target runtime: {summary['target_runtime']}")
    print(f"target profile: {summary['target_profile']}")
    print(f"normalized transcript path: {summary['transcript_output_path']}")
    print(f"session boundary path: {summary['session_boundary_output_path']}")
    print(f"memory check path: {summary['memory_check_output_path']}")
    print(f"raw output path: {summary['raw_output_path']}")
    print(f"raw memory path: {summary['raw_memory_path']}")
    print(f"transcripts emitted: {summary['transcripts']}")
    print(f"session boundaries emitted: {summary['session_boundaries']}")
    print(f"memory checks emitted: {summary['memory_checks']}")
    print(f"live Hermes execution in quality gate: {str(summary['live_hermes_execution_in_quality_gate']).lower()}")
    print(f"private memory read in quality gate: {str(summary['private_memory_read_in_quality_gate']).lower()}")
    print("long-running agent fixture generation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
