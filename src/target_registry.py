"""Target registry helpers for mock profiles and future adapter labels.

The registry keeps target labels out of individual scripts. It does not run
models, call providers, execute agents, or collect outputs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = REPO_ROOT / "targets/target_registry.json"

REQUIRED_TOP_LEVEL_FIELDS = {
    "registry_id",
    "version",
    "updated_at",
    "targets",
}
REQUIRED_TARGET_FIELDS = {
    "target_profile",
    "display_name",
    "target_kind",
    "profile_path",
    "prompt_path",
    "quality_gate_profile",
    "manual_output_allowed",
    "adapter_output_allowed",
    "notes",
}
ALLOWED_TARGET_KINDS = {
    "mock_profile",
    "adapter_candidate",
    "saved_transcript_target",
}

UTC_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class TargetRegistryError(Exception):
    """Target registry validation or lookup error."""


def display_path(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def load_target_registry(path: Path = DEFAULT_REGISTRY_PATH) -> dict[str, Any]:
    """Load and validate the target registry."""

    if not path.exists():
        raise TargetRegistryError(f"{display_path(path)}: file does not exist")

    try:
        with path.open("r", encoding="utf-8") as input_file:
            registry = json.load(input_file)
    except json.JSONDecodeError as exc:
        raise TargetRegistryError(f"{display_path(path)}:{exc.lineno}: invalid JSON: {exc.msg}") from exc

    validate_target_registry(registry, path)
    return registry


def validate_target_registry(
    registry: Any | None = None,
    path: Path = DEFAULT_REGISTRY_PATH,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """Validate the target registry and return a concise summary."""

    if registry is None:
        if not path.exists():
            raise TargetRegistryError(f"{display_path(path, repo_root)}: file does not exist")
        try:
            with path.open("r", encoding="utf-8") as input_file:
                registry = json.load(input_file)
        except json.JSONDecodeError as exc:
            raise TargetRegistryError(
                f"{display_path(path, repo_root)}:{exc.lineno}: invalid JSON: {exc.msg}"
            ) from exc

    context = display_path(path, repo_root)
    require_object(registry, REQUIRED_TOP_LEVEL_FIELDS, context)

    if registry["registry_id"] != "target_registry":
        raise TargetRegistryError(f"{context}.registry_id must be target_registry")
    require_non_empty_string(registry["version"], f"{context}.version")
    validate_utc_timestamp(registry["updated_at"], f"{context}.updated_at")

    targets = registry["targets"]
    if not isinstance(targets, list) or not targets:
        raise TargetRegistryError(f"{context}.targets must be a non-empty array")

    seen_profiles: set[str] = set()
    quality_gate_profiles = 0
    for index, target in enumerate(targets):
        target_context = f"{context}.targets[{index}]"
        validate_target(target, target_context, seen_profiles, repo_root)
        if target["quality_gate_profile"] is True:
            quality_gate_profiles += 1

    if quality_gate_profiles == 0:
        raise TargetRegistryError(f"{context}.targets must include at least one quality-gate profile")

    return {
        "registry_path": context,
        "target_count": len(targets),
        "quality_gate_profile_count": quality_gate_profiles,
    }


def validate_target(target: Any, context: str, seen_profiles: set[str], repo_root: Path) -> None:
    require_object(target, REQUIRED_TARGET_FIELDS, context)

    target_profile = require_non_empty_string(target["target_profile"], f"{context}.target_profile")
    if target_profile in seen_profiles:
        raise TargetRegistryError(f"{context}.target_profile duplicate value: {target_profile}")
    seen_profiles.add(target_profile)

    require_non_empty_string(target["display_name"], f"{context}.display_name")
    require_enum(target["target_kind"], ALLOWED_TARGET_KINDS, f"{context}.target_kind")
    require_existing_repo_path(target["profile_path"], f"{context}.profile_path", repo_root)
    require_existing_repo_path(target["prompt_path"], f"{context}.prompt_path", repo_root)
    require_non_empty_string(target["notes"], f"{context}.notes")

    for field_name in ["quality_gate_profile", "manual_output_allowed", "adapter_output_allowed"]:
        if not isinstance(target[field_name], bool):
            raise TargetRegistryError(f"{context}.{field_name} must be a boolean")

    if target["quality_gate_profile"] and target["target_kind"] != "mock_profile":
        raise TargetRegistryError(f"{context}.quality_gate_profile requires target_kind=mock_profile")


def target_records(path: Path = DEFAULT_REGISTRY_PATH) -> list[dict[str, Any]]:
    """Return target records in registry order."""

    registry = load_target_registry(path)
    return list(registry["targets"])


def target_profile_names(path: Path = DEFAULT_REGISTRY_PATH) -> list[str]:
    """Return all registered target_profile values in registry order."""

    return [str(target["target_profile"]) for target in target_records(path)]


def quality_gate_profile_names(path: Path = DEFAULT_REGISTRY_PATH) -> list[str]:
    """Return deterministic mock profiles used by the quality-gate baseline."""

    return [
        str(target["target_profile"])
        for target in target_records(path)
        if target["quality_gate_profile"] is True
    ]


def allowed_manual_output_profiles(path: Path = DEFAULT_REGISTRY_PATH) -> list[str]:
    """Return profiles that saved manual outputs may reference."""

    return [
        str(target["target_profile"])
        for target in target_records(path)
        if target["manual_output_allowed"] is True
    ]


def allowed_adapter_output_profiles(path: Path = DEFAULT_REGISTRY_PATH) -> list[str]:
    """Return profiles that normalized adapter outputs may reference."""

    return [
        str(target["target_profile"])
        for target in target_records(path)
        if target["adapter_output_allowed"] is True
    ]


def require_registered_profile(profile_name: str, allowed_profiles: list[str], context: str) -> None:
    """Raise if a target profile is not in an allowed profile list."""

    if profile_name not in allowed_profiles:
        allowed = ", ".join(allowed_profiles)
        raise TargetRegistryError(f"{context}: unsupported target_profile {profile_name!r}; expected one of: {allowed}")


def require_object(value: Any, required_fields: set[str], context: str) -> None:
    if not isinstance(value, dict):
        raise TargetRegistryError(f"{context} must be an object")

    missing_fields = sorted(required_fields - set(value))
    if missing_fields:
        raise TargetRegistryError(f"{context} missing required fields: {', '.join(missing_fields)}")

    unexpected_fields = sorted(set(value) - required_fields)
    if unexpected_fields:
        raise TargetRegistryError(f"{context} unexpected fields: {', '.join(unexpected_fields)}")


def validate_utc_timestamp(value: Any, context: str) -> None:
    text = require_non_empty_string(value, context)
    if not UTC_TIMESTAMP_PATTERN.fullmatch(text):
        raise TargetRegistryError(f"{context} must use YYYY-MM-DDTHH:MM:SSZ UTC format")
    try:
        datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise TargetRegistryError(f"{context} must be a valid UTC timestamp") from exc


def require_enum(value: Any, allowed_values: set[str], context: str) -> str:
    text = require_non_empty_string(value, context)
    if text not in allowed_values:
        allowed = ", ".join(sorted(allowed_values))
        raise TargetRegistryError(f"{context} must be one of: {allowed}")
    return text


def require_non_empty_string(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise TargetRegistryError(f"{context} must be a string")
    if not value.strip():
        raise TargetRegistryError(f"{context} must not be empty")
    return value


def require_existing_repo_path(value: Any, context: str, repo_root: Path) -> Path:
    raw_path = require_non_empty_string(value, context)
    path = Path(raw_path)
    if path.is_absolute():
        raise TargetRegistryError(f"{context} must be a repository-relative path")

    resolved = (repo_root / path).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise TargetRegistryError(f"{context} must stay within the repository") from exc

    if not resolved.exists():
        raise TargetRegistryError(f"{context} does not exist: {display_path(resolved, repo_root)}")
    return resolved


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate the target registry.")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=DEFAULT_REGISTRY_PATH,
        help="Target registry JSON file to validate.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        summary = validate_target_registry(path=args.path)
    except (TargetRegistryError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"target registry path: {summary['registry_path']}")
    print(f"target profiles validated: {summary['target_count']}")
    print(f"quality-gate profiles: {summary['quality_gate_profile_count']}")
    print("target registry validation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
