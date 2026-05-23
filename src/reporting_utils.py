"""Shared helpers for deterministic local reports and snapshot checks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_jsonl_records(path: Path) -> list[dict[str, Any]]:
    """Load JSONL records and require each non-empty line to be an object."""

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, line in enumerate(input_file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {display_path(path)} on line {line_number}: {exc.msg}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"{display_path(path)}:{line_number}: record must be a JSON object")
            records.append(record)
    return records


def load_json_object(path: Path) -> dict[str, Any]:
    """Load a JSON object from disk."""

    with path.open("r", encoding="utf-8") as input_file:
        value = json.load(input_file)
    if not isinstance(value, dict):
        raise ValueError(f"{display_path(path)}: JSON root must be an object")
    return value


def write_json_object(value: dict[str, Any], output_path: Path) -> None:
    """Write a deterministic JSON object."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_text(content: str, output_path: Path) -> None:
    """Write UTF-8 text, creating parent directories as needed."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def normalize_repo_path(value: str | Path, repo_root: Path | None = None) -> str:
    """Normalize a path to repo-relative form when it is inside repo_root."""

    root = repo_root or Path(__file__).resolve().parents[1]
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        return str(resolved.relative_to(root.resolve()))
    except ValueError:
        return str(path)


def resolve_repo_path(path: Path, repo_root: Path | None = None) -> Path:
    """Resolve absolute or repository-relative paths."""

    root = repo_root or Path(__file__).resolve().parents[1]
    if path.is_absolute():
        return path.resolve()
    return (root / path).resolve()


def display_path(path: str | Path, repo_root: Path | None = None) -> str:
    """Display a path relative to the repository when possible."""

    return normalize_repo_path(path, repo_root)


def format_list(values: list[Any]) -> str:
    """Format a list for Markdown tables and bullets."""

    if not values:
        return "`none`"
    return ", ".join(f"`{value}`" for value in values)


def percent(part: int, total: int) -> str:
    """Return a one-decimal percentage string."""

    if total == 0:
        return "0.0%"
    return f"{(part / total) * 100:.1f}%"


def pass_count(records: list[dict[str, Any]]) -> int:
    """Count records whose `passed` field is exactly true."""

    return sum(1 for record in records if record.get("passed") is True)


def compare_nested_values(expected: Any, current: Any) -> list[str]:
    """Return deterministic differences between two nested JSON-compatible values."""

    differences: list[str] = []
    _collect_differences("", expected, current, differences)
    return differences


def _collect_differences(path: str, expected: Any, current: Any, differences: list[str]) -> None:
    if isinstance(expected, dict) and isinstance(current, dict):
        keys = sorted(set(expected) | set(current))
        for key in keys:
            next_path = f"{path}.{key}" if path else str(key)
            if key not in expected:
                differences.append(f"{next_path}: unexpected current value {current[key]!r}")
            elif key not in current:
                differences.append(f"{next_path}: missing current value, expected {expected[key]!r}")
            else:
                _collect_differences(next_path, expected[key], current[key], differences)
        return

    if expected != current:
        differences.append(f"{path}: expected {expected!r}, found {current!r}")
