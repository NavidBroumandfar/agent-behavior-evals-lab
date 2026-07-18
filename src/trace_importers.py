"""Config-driven importer: any JSON/JSONL agent log -> bring-your-own-trace records.

The framework adapters in ``trace_adapters`` cover LangGraph / OpenAI Agents /
CrewAI exports. Everything else — an in-house run log, an OpenTelemetry span
export, a vendor dump — is shaped differently, and hand-writing a converter is
the friction that stops a first evaluation. This module maps an arbitrary log
onto the trace-gate record shape from a small declarative config, so adopting
the gate is a mapping file rather than a script.

A mapping declares where the records live and which fields carry the record id,
the agent's prose, and the tool calls::

    {
      "name": "my-agent-log",
      "record_path": "runs",
      "record_id": "id",
      "output_text": "final.message",
      "tool_events": {
        "path": "steps",
        "tool_name": "tool",
        "action": "args.command",
        "status": "state"
      },
      "status_map": {"ok": "succeeded", "err": "failed"}
    }

Field selectors are dotted paths (``final.message``). Two prefixes handle the
shapes dotted paths cannot reach:

- ``attr:<key>`` looks the key up in an OpenTelemetry-style attribute list
  (``[{"key": ..., "value": {"stringValue": ...}}, ...]``) or a plain mapping.
- ``join:<a>,<b>`` concatenates the first non-empty of several selectors.

Deterministic and standard-library only: it reads a file you already have and
writes JSONL. No providers, no credentials, no external actions.

Exit codes:
    0 - records written
    2 - usage, mapping, or input error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PRESET_DIR = REPO_ROOT / "schemas/trace-mappings"

# Statuses understood downstream. Anything else passes through and is folded by
# the verifier as executed-with-unknown-outcome (see structural_tool_verifier).
KNOWN_STATUSES = ("succeeded", "failed", "denied")


class TraceImportError(Exception):
    """Mapping or input error with public-safe context."""


def _resolve(value: Any, selector: str) -> Any:
    """Resolve one selector against a value. Returns None when absent."""

    selector = selector.strip()
    if not selector:
        return None
    if selector.startswith("join:"):
        for part in selector[len("join:") :].split(","):
            resolved = _resolve(value, part)
            if resolved not in (None, ""):
                return resolved
        return None
    if selector.startswith("attr:"):
        return _resolve_attribute(value, selector[len("attr:") :].strip())
    current = value
    for segment in selector.split("."):
        if current is None:
            return None
        if isinstance(current, list):
            if not segment.isdigit():
                return None
            index = int(segment)
            current = current[index] if 0 <= index < len(current) else None
            continue
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
    return current


def _resolve_attribute(value: Any, key: str) -> Any:
    """Look up an attribute by key in an OTel-style list or a plain mapping."""

    if isinstance(value, dict):
        attributes = value.get("attributes", value)
    else:
        attributes = value
    if isinstance(attributes, dict):
        return attributes.get(key)
    if not isinstance(attributes, list):
        return None
    for entry in attributes:
        if not isinstance(entry, dict) or entry.get("key") != key:
            continue
        raw = entry.get("value")
        if isinstance(raw, dict):
            # OTel AnyValue: take whichever typed field is present.
            for field in ("stringValue", "intValue", "boolValue", "doubleValue"):
                if field in raw:
                    return raw[field]
            return None
        return raw
    return None


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    return json.dumps(value, sort_keys=True)


def load_mapping(path: Path) -> dict[str, Any]:
    """Load and validate a mapping config."""

    try:
        mapping = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TraceImportError(f"mapping file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise TraceImportError(f"{path.name}: invalid JSON mapping: {exc.msg}") from exc
    if not isinstance(mapping, dict):
        raise TraceImportError(f"{path.name}: mapping must be a JSON object")
    for required in ("record_id", "output_text"):
        if not isinstance(mapping.get(required), str) or not mapping[required].strip():
            raise TraceImportError(f"{path.name}: mapping.{required} must be a non-empty selector string")
    events = mapping.get("tool_events")
    if events is not None:
        if not isinstance(events, dict):
            raise TraceImportError(f"{path.name}: mapping.tool_events must be an object")
        if not isinstance(events.get("path"), str) or not events["path"].strip():
            raise TraceImportError(f"{path.name}: mapping.tool_events.path must be a non-empty selector string")
    status_map = mapping.get("status_map", {})
    if not isinstance(status_map, dict):
        raise TraceImportError(f"{path.name}: mapping.status_map must be an object")
    return mapping


def load_source(path: Path) -> list[Any]:
    """Load JSON or JSONL input into a list of top-level values."""

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise TraceImportError(f"input file does not exist: {path}") from exc
    stripped = text.strip()
    if not stripped:
        raise TraceImportError(f"{path.name}: input file is empty")
    if path.suffix == ".jsonl" or (not stripped.startswith(("[", "{"))):
        values = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                values.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise TraceImportError(f"{path.name}:{line_number}: invalid JSON line: {exc.msg}") from exc
        return values
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise TraceImportError(f"{path.name}: invalid JSON: {exc.msg}") from exc
    return parsed if isinstance(parsed, list) else [parsed]


def _iter_records(values: list[Any], mapping: dict[str, Any]) -> list[Any]:
    record_path = mapping.get("record_path")
    if not record_path:
        return values
    records: list[Any] = []
    for value in values:
        resolved = _resolve(value, record_path)
        if isinstance(resolved, list):
            records.extend(resolved)
        elif resolved is not None:
            records.append(resolved)
    return records


def _build_events(record: Any, mapping: dict[str, Any]) -> list[dict[str, Any]]:
    spec = mapping.get("tool_events")
    if not spec:
        return []
    raw_events = _resolve(record, spec["path"])
    if raw_events is None:
        return []
    if not isinstance(raw_events, list):
        raw_events = [raw_events]
    status_map = {str(k).lower(): v for k, v in mapping.get("status_map", {}).items()}
    events: list[dict[str, Any]] = []
    for raw in raw_events:
        tool_name = _as_text(_resolve(raw, spec.get("tool_name", "")))
        action = _as_text(_resolve(raw, spec.get("action", "")))
        status_selector = spec.get("status", "")
        status = _as_text(_resolve(raw, status_selector)) if status_selector else ""
        status = status_map.get(status.lower(), status)
        if not tool_name and not action:
            continue
        event = {"tool_name": tool_name or "unknown_tool", "action": action}
        if status:
            event["status"] = status
        events.append(event)
    return events


def import_records(source_path: Path, mapping: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert a source log into bring-your-own-trace records."""

    raw_records = _iter_records(load_source(source_path), mapping)
    if not raw_records:
        raise TraceImportError(
            f"{source_path.name}: no records found"
            + (f" at record_path {mapping['record_path']!r}" if mapping.get("record_path") else "")
        )
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_records, start=1):
        record_id = _as_text(_resolve(raw, mapping["record_id"])).strip()
        if not record_id:
            record_id = f"{source_path.stem}-{index}"
        if record_id in seen:
            record_id = f"{record_id}-{index}"
        seen.add(record_id)
        record: dict[str, Any] = {
            "record_id": record_id,
            "output_text": _as_text(_resolve(raw, mapping["output_text"])),
            "tool_events": _build_events(raw, mapping),
        }
        category_selector = mapping.get("category")
        if category_selector:
            category = _as_text(_resolve(raw, category_selector)).strip()
            if category:
                record["category"] = category
        records.append(record)
    return records


def write_records(records: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def resolve_mapping_path(value: str) -> Path:
    """Accept a preset name or a path to a mapping file."""

    candidate = Path(value)
    if candidate.exists():
        return candidate
    preset = PRESET_DIR / f"{value}.json"
    if preset.exists():
        return preset
    available = ", ".join(sorted(p.stem for p in PRESET_DIR.glob("*.json"))) or "none"
    raise TraceImportError(f"unknown mapping {value!r}; pass a file path or a preset name (available: {available})")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Map any JSON/JSONL agent log onto bring-your-own-trace records.",
    )
    parser.add_argument("--input", type=Path, required=True, help="Source log (.json or .jsonl).")
    parser.add_argument("--mapping", required=True, help="Mapping file path, or a preset name from schemas/trace-mappings/.")
    parser.add_argument("--output", type=Path, required=True, help="Destination JSONL for trace-gate records.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        mapping = load_mapping(resolve_mapping_path(args.mapping))
        records = import_records(args.input, mapping)
        write_records(records, args.output)
    except TraceImportError as exc:
        print(f"trace import error: {exc}", file=sys.stderr)
        return 2
    with_events = sum(1 for record in records if record["tool_events"])
    print(
        f"imported {len(records)} record(s) ({with_events} with tool events) "
        f"using mapping {mapping.get('name', args.mapping)!r} -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
