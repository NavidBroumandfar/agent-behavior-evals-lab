"""Minimal stdio MCP server exposing the mock sandbox toolbox to CLI agents.

Lets MCP-speaking agent harnesses (Claude Code, Codex CLI) call the fake
sandbox tools (`sandbox_tools.SandboxToolbox`) over newline-delimited
JSON-RPC on stdin/stdout. Every ``tools/call`` is appended to
``--events-file`` as one JSON line ``{"tool_name", "arguments"}`` before
dispatch, so the parent runner can replay the calls into its own toolbox and
record ``tool_events`` exactly as for in-process agents — even if the client
kills this process without a clean shutdown.

Standard-library only; nothing here touches the real system. Opt-in evidence
producer: the deterministic quality gate never runs this module.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # standalone spawn: cwd/PYTHONPATH unset

from sandbox_tools import SandboxToolbox


SERVER_INFO = {"name": "sandbox", "version": "1.0.0"}


def mcp_tool_specs(toolbox: SandboxToolbox) -> list[dict[str, Any]]:
    """Toolbox specs (OpenAI function shape) converted to the MCP tool shape."""

    return [
        {
            "name": spec["function"]["name"],
            "description": spec["function"]["description"],
            "inputSchema": spec["function"]["parameters"],
        }
        for spec in toolbox.tool_specs()
    ]


def handle_request(request: dict[str, Any], toolbox: SandboxToolbox, events_path: Path) -> dict[str, Any] | None:
    """Return the JSON-RPC result for one request, or None for unknown methods."""

    method = request.get("method")
    if method == "initialize":
        client_version = str(request.get("params", {}).get("protocolVersion", "2025-06-18"))
        return {
            "protocolVersion": client_version,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        }
    if method == "tools/list":
        return {"tools": mcp_tool_specs(toolbox)}
    if method == "tools/call":
        params = request.get("params", {})
        name = str(params.get("name", "unknown_tool"))
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            arguments = {"value": str(arguments)}
        # Log before dispatch, append + close per call: the record must survive
        # a client that kills the server mid-run.
        with events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"tool_name": name, "arguments": arguments}, sort_keys=True) + "\n")
        result = toolbox.dispatch(name, arguments)
        return {"content": [{"type": "text", "text": result}], "isError": False}
    if method == "ping":
        return {}
    return None


def serve(events_path: Path) -> None:
    toolbox = SandboxToolbox()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(request, dict) or "id" not in request:
            continue  # notification (e.g. notifications/initialized) — no response
        result = handle_request(request, toolbox, events_path)
        if result is None:
            response: dict[str, Any] = {
                "jsonrpc": "2.0",
                "id": request["id"],
                "error": {"code": -32601, "message": f"method not found: {request.get('method')}"},
            }
        else:
            response = {"jsonrpc": "2.0", "id": request["id"], "result": result}
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


def self_check() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        events_path = Path(tmp) / "events.jsonl"
        toolbox = SandboxToolbox()
        init = handle_request({"method": "initialize", "id": 1, "params": {"protocolVersion": "x"}}, toolbox, events_path)
        assert init is not None and init["protocolVersion"] == "x" and init["serverInfo"]["name"] == "sandbox"
        listed = handle_request({"method": "tools/list", "id": 2}, toolbox, events_path)
        assert listed is not None and {t["name"] for t in listed["tools"]} == {
            "run_shell", "read_file", "write_file", "send_email", "db_query",
        }
        called = handle_request(
            {"method": "tools/call", "id": 3, "params": {"name": "run_shell", "arguments": {"command": "rm -rf build/"}}},
            toolbox,
            events_path,
        )
        assert called is not None and "ok" in called["content"][0]["text"]
        assert toolbox.destructive_calls, "destructive call must be recorded in the serving toolbox"
        logged = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
        assert logged == [{"arguments": {"command": "rm -rf build/"}, "tool_name": "run_shell"}]
        assert handle_request({"method": "bogus", "id": 4}, toolbox, events_path) is None
    print("sandbox_mcp_server self-check passed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the mock sandbox toolbox over stdio MCP.")
    parser.add_argument("--events-file", type=Path, help="JSONL file to append every tools/call to.")
    parser.add_argument("--self-check", action="store_true", help="Run the offline self-check and exit.")
    args = parser.parse_args(argv)
    if args.self_check:
        self_check()
        return 0
    if args.events_file is None:
        parser.error("--events-file is required to serve")
    args.events_file.parent.mkdir(parents=True, exist_ok=True)
    serve(args.events_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
