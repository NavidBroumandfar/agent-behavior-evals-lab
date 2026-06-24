"""Validate M85 runtime stability and resource-profile metadata.

The committed profile is public-safe metadata only. It records model-specific
resource status, stop criteria, and operational blockers without reading raw
local outputs, probing the local runtime, calling providers, or executing
models.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from schema_validation_utils import display_path, load_json_object, validate_schema_value


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE_PATH = REPO_ROOT / "traces/external/runtime_stability_profile.example.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/runtime_stability_profile.schema.json"

EXPECTED_OPERATOR_CONTROLS = {
    "manual_opt_in_required": True,
    "one_model_at_a_time": True,
    "plan_only_preflight_required": True,
    "raw_outputs_committable": False,
    "review_required_before_scoring": True,
    "stop_on_instability": True,
    "interrupted_runs_rankable": False,
    "quality_gate_live_execution_allowed": False,
}
EXPECTED_QUALITY_GATE = {
    "profile_validation_in_quality_gate": True,
    "live_local_execution_in_quality_gate": False,
    "runtime_probe_in_quality_gate": False,
    "raw_output_read_in_quality_gate": False,
    "provider_calls_in_quality_gate": False,
    "external_actions_in_quality_gate": False,
}
EXPECTED_SAFETY_ASSERTIONS = {
    "public_safe": True,
    "metadata_only": True,
    "contains_private_data": False,
    "contains_raw_outputs": False,
    "contains_credentials_or_secrets": False,
    "live_execution": False,
    "production_safety_claim": False,
    "third_party_reproducibility_claim": False,
    "ranking_claim_from_interrupted_runs": False,
}
REQUIRED_MODELS = {
    "deepseek-coder:6.7b-instruct",
    "llama3.2:latest",
    "glm4:latest",
    "codellama:7b-instruct",
    "mistral:latest",
    "qwen3.5:2b-q4_K_M",
    "gemma4:latest",
    "gemma4:31b-cloud",
}
RANKED_MODELS = {
    "deepseek-coder:6.7b-instruct",
    "llama3.2:latest",
    "glm4:latest",
    "codellama:7b-instruct",
    "qwen3.5:2b-q4_K_M",
    "mistral:latest",
}
REQUIRED_STOP_CRITERIA = {
    "memory_pressure_or_swap_activity",
    "thermal_or_power_instability",
    "model_availability_or_timeout_failure",
}
BLOCKED_MARKERS = [
    "/Users/",
    "\\Users\\",
    "sk-",
    "api_key",
    "BEGIN PRIVATE",
    "END PRIVATE",
    "raw_output_text",
    "raw_response",
]


class RuntimeStabilityProfileError(Exception):
    """Runtime stability profile validation error."""


def validate_runtime_stability_profile(
    profile_path: Path = DEFAULT_PROFILE_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the committed M85 runtime stability profile."""

    schema = load_json_object(schema_path, "runtime stability profile schema", repo_root, RuntimeStabilityProfileError)
    profile = load_json_object(profile_path, "runtime stability profile", repo_root, RuntimeStabilityProfileError)
    context = display_path(profile_path, repo_root)

    validate_schema_value(profile, schema, context, profile_path, repo_root, RuntimeStabilityProfileError)
    validate_expected_map(profile["operator_controls"], EXPECTED_OPERATOR_CONTROLS, f"{context}.operator_controls")
    validate_expected_map(profile["quality_gate"], EXPECTED_QUALITY_GATE, f"{context}.quality_gate")
    validate_expected_map(profile["safety_assertions"], EXPECTED_SAFETY_ASSERTIONS, f"{context}.safety_assertions")
    validate_runtime(profile["runtime"], f"{context}.runtime")
    validate_model_profiles(profile["model_profiles"], f"{context}.model_profiles")
    validate_observed_blockers(profile["observed_blockers"], f"{context}.observed_blockers")
    validate_stop_criteria(profile["stop_criteria"], f"{context}.stop_criteria")
    validate_source_paths(profile["source_paths"], f"{context}.source_paths", repo_root)
    validate_no_blocked_markers(profile, context)

    model_profiles = {profile_entry["model"]: profile_entry for profile_entry in profile["model_profiles"]}
    return {
        "profile_path": context,
        "schema_path": display_path(schema_path, repo_root),
        "profile_id": profile["profile_id"],
        "runtime": profile["runtime"]["runtime_id"],
        "model_count": len(profile["model_profiles"]),
        "deferred_model": "gemma4:latest",
        "deferred_model_status": model_profiles["gemma4:latest"]["status"],
        "stop_criteria_count": len(profile["stop_criteria"]),
        "quality_gate_live_execution": profile["quality_gate"]["live_local_execution_in_quality_gate"],
    }


def validate_runtime(value: dict[str, Any], context: str) -> None:
    if value["tools_enabled"] is not False:
        raise RuntimeStabilityProfileError(f"{context}.tools_enabled must be false")
    if value["external_actions_allowed"] is not False:
        raise RuntimeStabilityProfileError(f"{context}.external_actions_allowed must be false")


def validate_model_profiles(values: list[dict[str, Any]], context: str) -> None:
    models = {str(value["model"]) for value in values}
    missing_models = sorted(REQUIRED_MODELS - models)
    if missing_models:
        raise RuntimeStabilityProfileError(f"{context} missing required models: {', '.join(missing_models)}")

    seen: set[str] = set()
    for index, value in enumerate(values):
        model = str(value["model"])
        item_context = f"{context}[{index}]"
        if model in seen:
            raise RuntimeStabilityProfileError(f"{item_context}.model duplicate value: {model}")
        seen.add(model)

        ranking_eligible = value["ranking_eligible"]
        if model in RANKED_MODELS:
            if ranking_eligible is not True:
                raise RuntimeStabilityProfileError(f"{item_context}.ranking_eligible must be true for ranked model")
            if value["status"] not in {"completed_reviewed_standard", "completed_reviewed_extended"}:
                raise RuntimeStabilityProfileError(
                    f"{item_context}.status must be completed_reviewed_standard or completed_reviewed_extended"
                )
            if value["publication_use"] != "current_local_open_weight_ranking":
                raise RuntimeStabilityProfileError(f"{item_context}.publication_use must be current local ranking")
            continue

        if ranking_eligible is not False:
            raise RuntimeStabilityProfileError(f"{item_context}.ranking_eligible must be false for excluded model")

        if model == "gemma4:latest":
            if value["status"] != "deferred_after_swap_activity":
                raise RuntimeStabilityProfileError(f"{item_context}.status must keep gemma4 deferred")
            if value["publication_use"] != "deferred_operational_blocker":
                raise RuntimeStabilityProfileError(f"{item_context}.publication_use must be deferred operational blocker")
        if model == "gemma4:31b-cloud" and value["publication_use"] != "excluded_cloud_boundary":
            raise RuntimeStabilityProfileError(f"{item_context}.publication_use must exclude cloud-labelled target")


def validate_observed_blockers(values: list[dict[str, Any]], context: str) -> None:
    gemma_blockers = [value for value in values if value["model"] == "gemma4:latest"]
    if not gemma_blockers:
        raise RuntimeStabilityProfileError(f"{context} must document the gemma4:latest stability blocker")

    for index, value in enumerate(values):
        item_context = f"{context}[{index}]"
        if value["raw_run_artifact_written"] is not False:
            raise RuntimeStabilityProfileError(f"{item_context}.raw_run_artifact_written must be false")
        if value["ranking_evidence"] is not False:
            raise RuntimeStabilityProfileError(f"{item_context}.ranking_evidence must be false")
        if value["decision"] not in {"defer_target", "retry_only_after_stability_profile", "exclude_from_ranking"}:
            raise RuntimeStabilityProfileError(f"{item_context}.decision is not supported")


def validate_stop_criteria(values: list[dict[str, Any]], context: str) -> None:
    criterion_ids = {str(value["criterion_id"]) for value in values}
    missing = sorted(REQUIRED_STOP_CRITERIA - criterion_ids)
    if missing:
        raise RuntimeStabilityProfileError(f"{context} missing stop criteria: {', '.join(missing)}")

    for index, value in enumerate(values):
        item_context = f"{context}[{index}]"
        if value["public_metadata_allowed"] is not True:
            raise RuntimeStabilityProfileError(f"{item_context}.public_metadata_allowed must be true")
        if value["ranking_effect"] == "operational_blocker_not_evidence" and "Stop" not in value["required_action"]:
            raise RuntimeStabilityProfileError(f"{item_context}.required_action must stop operational blockers")


def validate_source_paths(values: list[str], context: str, repo_root: Path) -> None:
    for index, value in enumerate(values):
        path = Path(value)
        item_context = f"{context}[{index}]"
        if path.is_absolute():
            raise RuntimeStabilityProfileError(f"{item_context} must be repository-relative")
        resolved = (repo_root / path).resolve()
        try:
            relative_path = resolved.relative_to(repo_root.resolve())
        except ValueError as exc:
            raise RuntimeStabilityProfileError(f"{item_context} must stay inside repository") from exc
        if str(relative_path).startswith(("traces/raw/", "reports/private/", "private_evidence/")):
            raise RuntimeStabilityProfileError(f"{item_context} must not reference raw or private local artifacts")
        if not resolved.exists():
            raise RuntimeStabilityProfileError(f"{item_context} does not exist: {value}")


def validate_no_blocked_markers(value: dict[str, Any], context: str) -> None:
    text = str(value)
    for marker in BLOCKED_MARKERS:
        if marker in text:
            raise RuntimeStabilityProfileError(f"{context} contains blocked marker: {marker}")


def validate_expected_map(value: dict[str, Any], expected: dict[str, Any], context: str) -> None:
    for field_name, expected_value in expected.items():
        if value[field_name] != expected_value:
            raise RuntimeStabilityProfileError(f"{context}.{field_name} must equal {expected_value!r}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate runtime stability and resource-profile metadata.")
    parser.add_argument("profile", nargs="?", type=Path, default=DEFAULT_PROFILE_PATH)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = validate_runtime_stability_profile(args.profile, args.schema)
    except (RuntimeStabilityProfileError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"runtime stability profile: {summary['profile_path']}")
    print(f"runtime stability schema: {summary['schema_path']}")
    print(f"profile id: {summary['profile_id']}")
    print(f"runtime: {summary['runtime']}")
    print(f"models profiled: {summary['model_count']}")
    print(f"deferred model: {summary['deferred_model']} ({summary['deferred_model_status']})")
    print(f"stop criteria: {summary['stop_criteria_count']}")
    print(f"live execution in quality gate: {str(summary['quality_gate_live_execution']).lower()}")
    print("runtime stability profile validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
