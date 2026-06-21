"""Validate the M56 local adapter registry.

The registry defines opt-in local text-only adapter classes for future local
model runs. This validator reads committed local metadata only. It does not
call Ollama, local OpenAI-compatible servers, providers, agents, networks,
tools, credentials, or external actions.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from schema_validation_utils import display_path, load_json_object, validate_schema_value
from target_registry import allowed_adapter_output_profiles


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = REPO_ROOT / "targets/adapters/local_adapter_registry.json"
DEFAULT_SCHEMA_PATH = REPO_ROOT / "schemas/local_adapter_registry.schema.json"
LOCAL_BENCHMARK_MANIFEST_PATH = REPO_ROOT / "evals/benchmarks/local_public_v1/manifest.json"
LOCAL_BENCHMARK_CASE_PATH = REPO_ROOT / "evals/benchmarks/local_public_v1/cases.jsonl"

EXPECTED_ADAPTER_IDS = {
    "ollama_text_only",
    "local_openai_compatible_text_only",
    "manual_saved_output",
}
LOCAL_LIVE_ADAPTER_IDS = {
    "ollama_text_only",
    "local_openai_compatible_text_only",
}
EXPECTED_SPLITS = ["smoke", "standard", "extended"]
EXPECTED_SAFE_ASSERTIONS = {
    "public_safe": True,
    "live_execution": False,
    "external_actions": False,
    "contains_private_data": False,
    "credentials_required": False,
}


class LocalAdapterRegistryValidationError(Exception):
    """Local adapter registry validation error."""


def validate_registry(
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the local adapter registry and return a deterministic summary."""

    schema = load_json_object(schema_path, "schema", repo_root, LocalAdapterRegistryValidationError)
    registry = load_json_object(registry_path, "local adapter registry", repo_root, LocalAdapterRegistryValidationError)
    context = display_path(registry_path, repo_root)

    validate_schema_value(registry, schema, context, registry_path, repo_root, LocalAdapterRegistryValidationError)
    validate_case_set(registry["case_set"], context, repo_root)
    validate_live_execution_policy(registry["live_execution_policy"], context)
    validate_adapters(registry["adapters"], context)
    validate_future_extension_points(registry["future_extension_points"], context)
    validate_source_paths(registry["source_paths"], context, repo_root)
    validate_safety_assertions(registry["safety_assertions"], context)

    return {
        "registry_path": context,
        "schema_path": display_path(schema_path, repo_root),
        "adapter_count": len(registry["adapters"]),
        "adapter_ids": sorted(str(adapter["adapter_id"]) for adapter in registry["adapters"]),
        "live_local_required_adapters": sorted(
            str(adapter["adapter_id"])
            for adapter in registry["adapters"]
            if adapter["live_local_required"] is True
        ),
        "case_set_id": str(registry["case_set"]["case_set_id"]),
        "supported_splits": list(registry["case_set"]["supported_splits"]),
        "live_local_required_flag": str(registry["live_execution_policy"]["live_local_required_flag"]),
    }


def validate_case_set(case_set: dict[str, Any], context: str, repo_root: Path) -> None:
    case_context = f"{context}.case_set"
    manifest_path = require_existing_repo_path(case_set["manifest_path"], f"{case_context}.manifest_path", repo_root)
    case_path = require_existing_repo_path(case_set["case_path"], f"{case_context}.case_path", repo_root)

    if manifest_path != LOCAL_BENCHMARK_MANIFEST_PATH:
        raise LocalAdapterRegistryValidationError(
            f"{case_context}.manifest_path must equal {display_path(LOCAL_BENCHMARK_MANIFEST_PATH, repo_root)}"
        )
    if case_path != LOCAL_BENCHMARK_CASE_PATH:
        raise LocalAdapterRegistryValidationError(
            f"{case_context}.case_path must equal {display_path(LOCAL_BENCHMARK_CASE_PATH, repo_root)}"
        )
    if case_set["supported_splits"] != EXPECTED_SPLITS:
        raise LocalAdapterRegistryValidationError(f"{case_context}.supported_splits must equal {EXPECTED_SPLITS}")

    manifest = load_json_object(manifest_path, "local benchmark corpus manifest", repo_root, LocalAdapterRegistryValidationError)
    if manifest["case_set_id"] != case_set["case_set_id"]:
        raise LocalAdapterRegistryValidationError(f"{case_context}.case_set_id must match corpus manifest")
    if manifest["version"] != case_set["version"]:
        raise LocalAdapterRegistryValidationError(f"{case_context}.version must match corpus manifest")
    if sorted(manifest["splits"]) != sorted(case_set["supported_splits"]):
        raise LocalAdapterRegistryValidationError(f"{case_context}.supported_splits must match corpus manifest")


def validate_live_execution_policy(policy: dict[str, Any], context: str) -> None:
    policy_context = f"{context}.live_execution_policy"
    if policy["live_local_required_flag"] != "--live-local":
        raise LocalAdapterRegistryValidationError(f"{policy_context}.live_local_required_flag must equal --live-local")
    if policy["live_local_required_env"] != "AGENT_EVALS_ENABLE_LIVE_LOCAL":
        raise LocalAdapterRegistryValidationError(
            f"{policy_context}.live_local_required_env must equal AGENT_EVALS_ENABLE_LIVE_LOCAL"
        )
    expected_booleans = {
        "live_local_in_quality_gate": False,
        "dry_run_in_quality_gate": True,
        "tools_enabled": False,
        "external_actions_allowed": False,
        "raw_outputs_committable": False,
        "normalized_outputs_require_review": True,
    }
    for field_name, expected_value in expected_booleans.items():
        if policy[field_name] is not expected_value:
            raise LocalAdapterRegistryValidationError(
                f"{policy_context}.{field_name} must equal {expected_value!r}"
            )


def validate_adapters(adapters: list[dict[str, Any]], context: str) -> None:
    observed_ids = [str(adapter["adapter_id"]) for adapter in adapters]
    duplicate_ids = sorted({adapter_id for adapter_id in observed_ids if observed_ids.count(adapter_id) > 1})
    if duplicate_ids:
        raise LocalAdapterRegistryValidationError(f"{context}.adapters duplicate adapter_id values: {', '.join(duplicate_ids)}")
    if set(observed_ids) != EXPECTED_ADAPTER_IDS:
        raise LocalAdapterRegistryValidationError(
            f"{context}.adapters must contain exactly: {', '.join(sorted(EXPECTED_ADAPTER_IDS))}"
        )

    allowed_profiles = set(allowed_adapter_output_profiles())
    for adapter in adapters:
        adapter_id = str(adapter["adapter_id"])
        adapter_context = f"{context}.adapters[{adapter_id}]"
        if adapter["target_profile"] not in allowed_profiles:
            raise LocalAdapterRegistryValidationError(
                f"{adapter_context}.target_profile must be a registered adapter-output profile"
            )
        if adapter["supported_splits"] != EXPECTED_SPLITS:
            raise LocalAdapterRegistryValidationError(f"{adapter_context}.supported_splits must equal {EXPECTED_SPLITS}")
        if adapter["quality_gate_execution_allowed"] is not False:
            raise LocalAdapterRegistryValidationError(
                f"{adapter_context}.quality_gate_execution_allowed must be false"
            )
        if adapter["dry_run_validation_allowed"] is not True:
            raise LocalAdapterRegistryValidationError(f"{adapter_context}.dry_run_validation_allowed must be true")
        if adapter["credentials_required"] is not False:
            raise LocalAdapterRegistryValidationError(f"{adapter_context}.credentials_required must be false")

        if adapter_id in LOCAL_LIVE_ADAPTER_IDS:
            validate_local_live_adapter(adapter, adapter_context)
        else:
            validate_manual_adapter(adapter, adapter_context)


def validate_local_live_adapter(adapter: dict[str, Any], context: str) -> None:
    if adapter["live_local_required"] is not True:
        raise LocalAdapterRegistryValidationError(f"{context}.live_local_required must be true")
    if adapter["credential_policy"] != "none_required":
        raise LocalAdapterRegistryValidationError(f"{context}.credential_policy must be none_required")
    if adapter["tool_availability"] != "text_only_no_tools":
        raise LocalAdapterRegistryValidationError(f"{context}.tool_availability must be text_only_no_tools")
    if adapter["endpoint_template"].startswith("http://127.0.0.1") is not True:
        raise LocalAdapterRegistryValidationError(f"{context}.endpoint_template must point to loopback")
    if int(adapter["default_parameters"]["timeout_seconds"]) <= 0:
        raise LocalAdapterRegistryValidationError(f"{context}.default_parameters.timeout_seconds must be positive")
    if int(adapter["default_parameters"]["max_output_tokens"]) <= 0:
        raise LocalAdapterRegistryValidationError(f"{context}.default_parameters.max_output_tokens must be positive")
    if int(adapter["default_parameters"]["context_window_tokens"]) <= 0:
        raise LocalAdapterRegistryValidationError(
            f"{context}.default_parameters.context_window_tokens must be positive"
        )


def validate_manual_adapter(adapter: dict[str, Any], context: str) -> None:
    if adapter["adapter_id"] != "manual_saved_output":
        raise LocalAdapterRegistryValidationError(f"{context}.adapter_id must be manual_saved_output")
    if adapter["live_local_required"] is not False:
        raise LocalAdapterRegistryValidationError(f"{context}.live_local_required must be false")
    if adapter["credential_policy"] != "not_applicable":
        raise LocalAdapterRegistryValidationError(f"{context}.credential_policy must be not_applicable")
    if adapter["endpoint_class"] != "not_applicable":
        raise LocalAdapterRegistryValidationError(f"{context}.endpoint_class must be not_applicable")
    if adapter["tool_availability"] != "none":
        raise LocalAdapterRegistryValidationError(f"{context}.tool_availability must be none")
    if any(int(adapter["default_parameters"][field_name]) != 0 for field_name in ["context_window_tokens", "max_output_tokens", "timeout_seconds"]):
        raise LocalAdapterRegistryValidationError(f"{context}.default_parameters token and timeout fields must be zero")


def validate_future_extension_points(extension_points: list[dict[str, Any]], context: str) -> None:
    observed_ids = [str(item["extension_id"]) for item in extension_points]
    duplicate_ids = sorted({extension_id for extension_id in observed_ids if observed_ids.count(extension_id) > 1})
    if duplicate_ids:
        raise LocalAdapterRegistryValidationError(
            f"{context}.future_extension_points duplicate extension_id values: {', '.join(duplicate_ids)}"
        )
    for item in extension_points:
        if item["status"] != "reserved_not_active":
            raise LocalAdapterRegistryValidationError(
                f"{context}.future_extension_points[{item['extension_id']}].status must be reserved_not_active"
            )


def validate_source_paths(source_paths: list[str], context: str, repo_root: Path) -> None:
    for index, value in enumerate(source_paths):
        require_existing_repo_path(value, f"{context}.source_paths[{index}]", repo_root)


def validate_safety_assertions(value: dict[str, Any], context: str) -> None:
    for field_name, expected_value in EXPECTED_SAFE_ASSERTIONS.items():
        if value[field_name] is not expected_value:
            raise LocalAdapterRegistryValidationError(
                f"{context}.safety_assertions.{field_name} must equal {expected_value!r}"
            )


def require_existing_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise LocalAdapterRegistryValidationError(f"{context} must be a non-empty string")
    path = Path(value)
    if path.is_absolute():
        raise LocalAdapterRegistryValidationError(f"{context} must be repository-relative")
    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise LocalAdapterRegistryValidationError(f"{context} must stay within the repository") from exc
    if not resolved.exists():
        raise LocalAdapterRegistryValidationError(f"{context} does not exist: {display_path(resolved, repo_root)}")
    return resolved


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the M56 local adapter registry.")
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_REGISTRY_PATH)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA_PATH)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        summary = validate_registry(args.path, args.schema)
    except (LocalAdapterRegistryValidationError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"local adapter registry path: {summary['registry_path']}")
    print(f"local adapter registry schema: {summary['schema_path']}")
    print(f"case set id: {summary['case_set_id']}")
    print(f"adapters validated: {summary['adapter_count']}")
    print(f"adapter ids: {', '.join(summary['adapter_ids'])}")
    print(f"live-local required adapters: {', '.join(summary['live_local_required_adapters'])}")
    print(f"live-local flag: {summary['live_local_required_flag']}")
    print("local adapter registry validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
