"""Convert saved agent-framework traces into normalized adapter-output JSONL.

Supported input formats:

- ``langgraph``: a message-list dump — ``{"messages": [...]}`` with LangChain
  message dicts (``type``/``role`` of ``ai``/``assistant``/``tool``; AI
  messages may carry ``tool_calls``; tool messages may carry ``status``).
  Both flat dicts and ``{"type": ..., "data": {...}}`` envelopes are accepted.
- ``openai-agents``: the OpenAI Agents SDK ``result.to_input_list()`` item
  list (Responses API items: ``message``, ``function_call``,
  ``function_call_output``).
- ``crewai``: CrewAI has no standard tool-telemetry export, so the accepted
  shape is ``{"raw": "<final output text>", "tool_events": [...]}`` where
  ``tool_events`` entries are ``{"tool_name", "action"?, "status"?}``
  collected from CrewAI tool callbacks (see examples/adapters/crewai/).

Input path is either a directory of ``<case_id>.json`` files or a single JSON
file mapping case_id to trace payload. Output is adapter-output JSONL that
``gate_check`` scores directly; records carry ``tool_events`` so structural
tool-claim verification applies. Standard-library only; converts saved files,
never runs agents or calls providers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from validate_adapter_outputs import validate_adapter_output_record


ADAPTER_VERSION = "0.1.0"
DEFAULT_TARGET_PROFILE = "generic_assistant"
FRAMEWORKS = ("langgraph", "openai-agents", "crewai")


class TraceAdapterError(Exception):
    """Trace conversion error with case and framework context."""


def parse_langgraph_trace(payload: Any) -> tuple[str, list[dict[str, Any]]]:
    """Extract final AI text and tool events from a LangGraph message dump."""

    messages = payload.get("messages") if isinstance(payload, dict) else payload
    if not isinstance(messages, list) or not messages:
        raise TraceAdapterError("langgraph trace must contain a non-empty 'messages' list")

    output_text = ""
    tool_events: list[dict[str, Any]] = []
    pending_calls: dict[str, dict[str, Any]] = {}

    for entry in messages:
        message = _unwrap_message(entry)
        kind = str(message.get("type", message.get("role", ""))).lower()

        if kind in ("ai", "assistant"):
            text = _content_text(message.get("content"))
            if text.strip():
                output_text = text
            for tool_call in message.get("tool_calls") or []:
                if not isinstance(tool_call, dict):
                    continue
                call_id = str(tool_call.get("id", f"call_{len(pending_calls)}"))
                pending_calls[call_id] = {
                    "tool_name": str(tool_call.get("name", "unknown_tool")),
                    "action": _digest_args_text(tool_call.get("args")),
                    "arguments_digest": _digest(tool_call.get("args")),
                }
        elif kind == "tool":
            call_id = str(message.get("tool_call_id", ""))
            call = pending_calls.pop(call_id, None)
            status = str(message.get("status", "success")).lower()
            event = call or {
                "tool_name": str(message.get("name", "unknown_tool")),
                "action": "",
                "arguments_digest": _digest(None),
            }
            event["status"] = "failed" if status == "error" else "succeeded"
            tool_events.append(event)

    # ponytail: tool calls without a ToolMessage response never executed, so
    # they are dropped rather than guessed at.
    if not output_text.strip():
        raise TraceAdapterError("langgraph trace has no AI message with text content")
    return output_text, tool_events


def parse_openai_agents_trace(payload: Any) -> tuple[str, list[dict[str, Any]]]:
    """Extract final assistant text and tool events from a to_input_list() dump."""

    items = payload.get("items") if isinstance(payload, dict) and "items" in payload else payload
    if not isinstance(items, list) or not items:
        raise TraceAdapterError("openai-agents trace must be a non-empty item list")

    output_text = ""
    tool_events: list[dict[str, Any]] = []
    pending_calls: dict[str, dict[str, Any]] = {}

    for item in items:
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type", ""))
        role = str(item.get("role", ""))

        if item_type == "function_call":
            call_id = str(item.get("call_id", item.get("id", f"call_{len(pending_calls)}")))
            pending_calls[call_id] = {
                "tool_name": str(item.get("name", "unknown_tool")),
                "action": _digest_args_text(item.get("arguments")),
                "arguments_digest": _digest(item.get("arguments")),
            }
        elif item_type == "function_call_output":
            call_id = str(item.get("call_id", ""))
            call = pending_calls.pop(call_id, None)
            if call is None:
                call = {"tool_name": "unknown_tool", "action": "", "arguments_digest": _digest(None)}
            call["status"] = "succeeded"
            tool_events.append(call)
        elif role == "assistant" or item_type == "message":
            text = _content_text(item.get("content"))
            if text.strip():
                output_text = text

    if not output_text.strip():
        raise TraceAdapterError("openai-agents trace has no assistant message with text content")
    return output_text, tool_events


def parse_crewai_trace(payload: Any) -> tuple[str, list[dict[str, Any]]]:
    """Extract final output text and optional tool events from a CrewAI export."""

    if not isinstance(payload, dict) or not str(payload.get("raw", "")).strip():
        raise TraceAdapterError("crewai trace must be an object with a non-empty 'raw' output text")

    tool_events: list[dict[str, Any]] = []
    for entry in payload.get("tool_events") or []:
        if not isinstance(entry, dict) or not str(entry.get("tool_name", "")).strip():
            raise TraceAdapterError("crewai tool_events entries need a tool_name")
        status = str(entry.get("status", "succeeded"))
        if status not in ("succeeded", "failed", "denied"):
            raise TraceAdapterError(f"crewai tool event has unsupported status {status!r}")
        tool_events.append(
            {
                "tool_name": str(entry["tool_name"]),
                "action": str(entry.get("action", "")),
                "arguments_digest": _digest(entry.get("arguments")),
                "status": status,
            }
        )
    return str(payload["raw"]), tool_events


PARSERS: dict[str, Callable[[Any], tuple[str, list[dict[str, Any]]]]] = {
    "langgraph": parse_langgraph_trace,
    "openai-agents": parse_openai_agents_trace,
    "crewai": parse_crewai_trace,
}


def build_adapter_record(
    case_id: str,
    output_text: str,
    tool_events: list[dict[str, Any]],
    *,
    framework: str,
    target_profile: str = DEFAULT_TARGET_PROFILE,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Build one schema-valid adapter-output record from parsed trace content."""

    timestamp = created_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Normalized records are single-line by schema; raw formatting stays in
    # the caller's original trace files.
    output_text = " ".join(str(output_text).split()) or "(empty output)"
    record: dict[str, Any] = {
        "record_id": f"{framework}-{case_id}",
        "case_id": case_id,
        "target_profile": target_profile,
        "source_type": "saved_adapter_output",
        "adapter_name": f"{framework.replace('-', '_')}_trace_adapter",
        "adapter_version": ADAPTER_VERSION,
        "created_at": timestamp,
        "output_text": output_text,
        "provenance": {
            "public_safe": True,
            "live_execution": False,
            "external_actions": False,
            "contains_private_data": False,
        },
        "provenance_details": {
            "source_origin": "manual_saved_output",
            "execution_mode": "saved_output_only",
            "data_classification": "public_safe_fixture",
            "action_evidence": "trace_or_transcript_reference",
            "notes": f"Converted from a saved {framework} trace; no execution by the converter.",
        },
        "metadata": {"source_label": f"{framework}_trace_conversion"},
        # Converted traces always carry the evidence channel, even when empty:
        # an action claim with zero recorded tool events must fail structurally.
        "tool_events": tool_events,
    }
    return record


def load_case_payloads(input_path: Path) -> dict[str, Any]:
    """Load case_id -> trace payload from a directory of <case_id>.json or one JSON file."""

    if input_path.is_dir():
        payloads = {
            trace_path.stem: _load_json(trace_path)
            for trace_path in sorted(input_path.glob("*.json"))
        }
        if not payloads:
            raise TraceAdapterError(f"no .json trace files found in directory {input_path}")
        return payloads

    if input_path.is_file():
        data = _load_json(input_path)
        if not isinstance(data, dict) or not data:
            raise TraceAdapterError(f"{input_path}: single-file input must be a non-empty object keyed by case_id")
        return data

    raise TraceAdapterError(f"input path does not exist: {input_path}")


def convert_traces(
    framework: str,
    input_path: Path,
    output_path: Path,
    *,
    target_profile: str = DEFAULT_TARGET_PROFILE,
    created_at: str | None = None,
) -> int:
    """Convert saved traces to validated adapter-output JSONL; return record count."""

    if framework not in PARSERS:
        raise TraceAdapterError(f"unsupported framework {framework!r}; expected one of: {', '.join(FRAMEWORKS)}")

    parser = PARSERS[framework]
    records: list[dict[str, Any]] = []
    for case_id, payload in sorted(load_case_payloads(input_path).items()):
        try:
            output_text, tool_events = parser(payload)
        except TraceAdapterError as exc:
            raise TraceAdapterError(f"case {case_id}: {exc}") from exc
        record = build_adapter_record(
            case_id,
            output_text,
            tool_events,
            framework=framework,
            target_profile=target_profile,
            created_at=created_at,
        )
        validate_adapter_output_record(record, output_path, len(records) + 1)
        records.append(record)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output_file:
        for record in records:
            output_file.write(json.dumps(record, sort_keys=True) + "\n")
    return len(records)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise TraceAdapterError(f"{path}: could not read trace JSON: {exc}") from exc


def _unwrap_message(entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        return {}
    data = entry.get("data")
    if isinstance(data, dict) and "type" not in data:
        data = dict(data, type=entry.get("type", ""))
    return data if isinstance(data, dict) else entry


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "\n".join(parts)
    return ""


def _digest(arguments: Any) -> str:
    canonical = json.dumps(arguments, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _digest_args_text(arguments: Any, limit: int = 200) -> str:
    if arguments is None:
        return ""
    text = arguments if isinstance(arguments, str) else json.dumps(arguments, sort_keys=True, default=str)
    return text[:limit]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert saved agent-framework traces to adapter-output JSONL.")
    parser.add_argument("--framework", choices=list(FRAMEWORKS), required=True, help="Trace format to convert.")
    parser.add_argument("--input", type=Path, required=True, help="Directory of <case_id>.json traces or one JSON file keyed by case_id.")
    parser.add_argument("--output", type=Path, required=True, help="Adapter-output JSONL destination.")
    parser.add_argument("--target-profile", default=DEFAULT_TARGET_PROFILE, help="Registered target profile for the records.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        count = convert_traces(
            args.framework,
            args.input,
            args.output,
            target_profile=args.target_profile,
        )
    except TraceAdapterError as exc:
        print(f"trace adapter error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - surface validator errors with context
        print(f"trace adapter error: {exc}", file=sys.stderr)
        return 2

    print(f"converted {count} trace(s) to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
