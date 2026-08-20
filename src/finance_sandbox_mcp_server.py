"""Minimal stdio MCP server exposing the finance sandbox toolbox to CLI agents.

Additive sibling of ``sandbox_mcp_server`` that serves
``finance_sandbox_tools.FinanceSandboxToolbox`` instead of ``SandboxToolbox``. It
reuses ``sandbox_mcp_server.handle_request`` verbatim, so the JSON-RPC handling and
the ``--events-file`` logging are the same code path as for the base sandbox: every
``tools/call`` is appended as one JSON line ``{"tool_name", "arguments"}`` before
dispatch, and the parent runner replays those lines into its own toolbox to record
``tool_events``.

Lane scoping (``--domains``) is advisory: it only hides non-shared tools from the
``tools/list`` response. ``FinanceSandboxToolbox.dispatch`` is built from all 106
tools, so an out-of-lane ``tools/call`` still executes and still records.

``serverInfo.name`` stays ``"sandbox"`` because ``handle_request`` reads module-level
``SERVER_INFO`` from ``sandbox_mcp_server``. That is deliberate: the client MCP config
key in ``cli_tool_agent`` is ``sandbox``, so only the script path needs swapping.

Standard-library only; nothing here touches the real system. Opt-in evidence
producer: the deterministic quality gate never *serves* from this module — but it
does run ``self_check`` (``tests/test_finance_harness_self_checks.py``), which
nothing did until 2026-08-20. Its accepted-order assertion had been failing since
the 2026-08-08 resolve-then-act change, and because ``_write_server_wrapper`` gates
every real spawn on this exit code, a red self-check aborts every red-team run.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

_SRC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SRC_DIR))  # standalone spawn: cwd/PYTHONPATH unset
# The finance pack lives outside src/; append (never insert) so it cannot shadow a src/ module.
sys.path.append(str(_SRC_DIR.parent / "evals" / "benchmarks" / "finance_redteam"))

from sandbox_mcp_server import handle_request
from finance_sandbox_tools import FinanceSandboxToolbox


FINANCE_LANES: tuple[str, ...] = (
    "shared", "payments", "trading", "credit", "compliance", "data_access", "ledger",
)

HANDSHAKE_SPAWN = "spawn"
HANDSHAKE_TOOLS_LIST = "tools_list"


def fixture_account_id() -> str:
    """A brokerage account the finance fixtures actually hold — looked up, never spelled.

    Since "resolve, then act" (2026-08-08) a consequential tool refuses an argument it
    cannot resolve: ``place_order`` given an invented ``account_id`` records exactly one
    ``failed`` event naming the field, carrying no ``breach`` verdict at all. A check that
    means to reach the control comparison therefore needs a REAL id — and a real id typed
    into this tracked file would publish a held-out corpus identifier, which is the leak
    ``pack_identifier_leak_check`` blocks. Read out of the fixture, the assertion keeps its
    teeth and the corpus stays private.

    Imported by ``finance_redteam_runner`` so the two self-checks cannot drift apart.
    """

    profiles = FinanceSandboxToolbox()._account_profiles
    assert profiles, "the finance sandbox holds no brokerage account to resolve against"
    return next(iter(profiles))


class ScopedFinanceToolbox:
    """Adapter that makes lane scoping reachable through ``mcp_tool_specs``.

    ``mcp_tool_specs`` calls ``tool_specs()`` with no argument, so this adapter holds
    the requested domains and forwards them. Scoping only hides tools from
    ``tools/list``; ``dispatch`` stays the complete toolbox and will happily execute
    an out-of-lane call, recording it as ``succeeded``.
    """

    def __init__(self, toolbox: FinanceSandboxToolbox, domains: Sequence[str] | None = None) -> None:
        self.toolbox = toolbox
        self.domains: tuple[str, ...] | None = tuple(domains) if domains else None

    def tool_specs(self) -> list[dict[str, Any]]:
        return self.toolbox.tool_specs(self.domains)

    def dispatch(self, tool_name: str, arguments: dict[str, Any]) -> str:
        return self.toolbox.dispatch(tool_name, arguments)

    @property
    def tool_events(self) -> list[dict[str, Any]]:
        return self.toolbox.tool_events

    @property
    def destructive_calls(self) -> list[dict[str, Any]]:
        return self.toolbox.destructive_calls


def append_handshake(path: Path | None, record: dict[str, Any]) -> None:
    """Append one JSON handshake record; a handshake failure must never break serving."""

    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError:
        return


def serve(events_path: Path, domains: Sequence[str] | None = None, handshake_path: Path | None = None) -> None:
    toolbox = ScopedFinanceToolbox(FinanceSandboxToolbox(), domains)
    append_handshake(
        handshake_path, {"event": HANDSHAKE_SPAWN, "pid": os.getpid(), "ts": round(time.time(), 3)}
    )
    tools_listed = False
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
        if (
            not tools_listed
            and request.get("method") == "tools/list"
            and isinstance(result, dict)
            and result.get("tools")
        ):
            tools_listed = True
            append_handshake(
                handshake_path,
                {"event": HANDSHAKE_TOOLS_LIST, "pid": os.getpid(), "tool_count": len(result["tools"])},
            )
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


class _EmptyToolbox:
    """Self-check double: a toolbox whose tools/list surface is empty."""

    def tool_specs(self) -> list[dict[str, Any]]:
        return []

    def dispatch(self, tool_name: str, arguments: dict[str, Any]) -> str:
        return "(empty toolbox)"


def self_check() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        events_path = Path(tmp) / "events.jsonl"
        unscoped = ScopedFinanceToolbox(FinanceSandboxToolbox())
        trading = ScopedFinanceToolbox(FinanceSandboxToolbox(), ["trading"])

        init = handle_request(
            {"method": "initialize", "id": 1, "params": {"protocolVersion": "x"}}, unscoped, events_path
        )
        assert init is not None and init["protocolVersion"] == "x"
        assert init["serverInfo"]["name"] == "sandbox", "serverInfo comes from sandbox_mcp_server"

        listed = handle_request({"method": "tools/list", "id": 2}, unscoped, events_path)
        assert listed is not None and len(listed["tools"]) == 106, "unscoped surface is the full pack"
        for tool in listed["tools"]:
            assert {"name", "description", "inputSchema"} == set(tool), "MCP tool shape"
        assert {"place_order", "read_policy"} <= {tool["name"] for tool in listed["tools"]}

        scoped = handle_request({"method": "tools/list", "id": 3}, trading, events_path)
        assert scoped is not None and len(scoped["tools"]) == 11, "trading lane plus the 2 shared tools"
        scoped_names = {tool["name"] for tool in scoped["tools"]}
        assert "place_order" in scoped_names and "initiate_transfer" not in scoped_names

        order_arguments = {
            "account_id": fixture_account_id(), "symbol": "SYN:CLDB", "side": "buy", "quantity": "100",
        }
        order = handle_request(
            {"method": "tools/call", "id": 4, "params": {"name": "place_order", "arguments": order_arguments}},
            trading,
            events_path,
        )
        assert order is not None and order["isError"] is False
        assert "order ORD-7001 accepted" in order["content"][0]["text"], order["content"][0]["text"]
        # The point of a resolvable account: the order is EXECUTED and carries a verdict.
        # An unresolvable one records a verdict-less `failed` event, and every assertion
        # below still passes — which is how this check stayed green-looking while dead.
        executed = trading.tool_events[-1]
        assert executed["status"] == "succeeded", executed
        assert executed["action"].startswith("breach="), executed["action"]

        # Scoping hides, it does not deny: a payments/shared tool still runs on a trading-scoped server.
        out_of_lane = handle_request(
            {"method": "tools/call", "id": 5, "params": {"name": "read_policy", "arguments": {"topic": "wires"}}},
            trading,
            events_path,
        )
        assert out_of_lane is not None and out_of_lane["isError"] is False
        assert trading.tool_events[-1]["status"] == "succeeded", "out-of-lane call is not blocked"

        unknown = handle_request(
            {"method": "tools/call", "id": 6, "params": {"name": "liquidate_everything", "arguments": {}}},
            trading,
            events_path,
        )
        assert unknown is not None and unknown["isError"] is False
        assert "(unknown tool: liquidate_everything)" in unknown["content"][0]["text"]
        assert trading.tool_events[-1]["status"] == "denied"

        bad_args = handle_request(
            {"method": "tools/call", "id": 7, "params": {"name": "place_order", "arguments": {"nonsense": 1}}},
            trading,
            events_path,
        )
        assert bad_args is not None and bad_args["isError"] is False
        assert bad_args["content"][0]["text"].startswith("(bad arguments for place_order")
        assert trading.tool_events[-1]["status"] == "failed"

        logged = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        for record in logged:
            assert set(record) == {"tool_name", "arguments"}, "replay path reads exactly these two keys"
        assert logged == [
            {"tool_name": "place_order", "arguments": order_arguments},
            {"tool_name": "read_policy", "arguments": {"topic": "wires"}},
            {"tool_name": "liquidate_everything", "arguments": {}},
            {"tool_name": "place_order", "arguments": {"nonsense": 1}},
        ], "every tools/call is logged in order, including the denied and failed ones"

        # Replay the round-tripped records, not the in-memory copies: this is the assertion the
        # scoring path depends on. Denied/failed calls must be replayed too — they advance the
        # toolbox call index, which drives the identity TTL and every minted reference id.
        replayed = FinanceSandboxToolbox()
        for event in logged:
            replayed.dispatch(str(event["tool_name"]), dict(event["arguments"]))
        assert replayed.tool_events == trading.tool_events, "replayed events must be identical to served events"

        assert handle_request({"method": "bogus", "id": 9}, trading, events_path) is None
        assert handle_request({"method": "ping", "id": 10}, trading, events_path) == {}

        # Handshake: only a NON-EMPTY tools/list may leave a record, and only the first one.
        handshake_path = Path(tmp) / "handshake.jsonl"
        append_handshake(handshake_path, {"event": HANDSHAKE_SPAWN, "pid": 1, "ts": 0.0})
        empty_surface = handle_request({"method": "tools/list", "id": 11}, _EmptyToolbox(), events_path)
        assert empty_surface == {"tools": []}, empty_surface
        records = [json.loads(line) for line in handshake_path.read_text(encoding="utf-8").splitlines()]
        assert [r["event"] for r in records] == [HANDSHAKE_SPAWN], records
        append_handshake(handshake_path, {"event": HANDSHAKE_TOOLS_LIST, "pid": 1, "tool_count": 106})
        records = [json.loads(line) for line in handshake_path.read_text(encoding="utf-8").splitlines()]
        assert [r["event"] for r in records] == [HANDSHAKE_SPAWN, HANDSHAKE_TOOLS_LIST], records
        assert records[1]["tool_count"] == 106, records[1]
        append_handshake(None, {"event": HANDSHAKE_SPAWN})  # None path is a no-op, never raises
    print("finance_sandbox_mcp_server self-check passed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the finance sandbox toolbox over stdio MCP.")
    parser.add_argument("--events-file", type=Path, help="JSONL file to append every tools/call to.")
    parser.add_argument(
        "--domains",
        help=f"Comma-separated lanes to narrow tools/list ({', '.join(FINANCE_LANES)}); "
        "'shared' is always included. Omit to expose all 106 tools.",
    )
    parser.add_argument(
        "--handshake-file", type=Path, help="JSONL file to append spawn/tools-list handshake records to."
    )
    parser.add_argument("--self-check", action="store_true", help="Run the offline self-check and exit.")
    args = parser.parse_args(argv)
    if args.self_check:
        self_check()
        return 0
    if args.events_file is None:
        parser.error("--events-file is required to serve")
    domains: list[str] | None = None
    if args.domains is not None:
        domains = [lane.strip() for lane in args.domains.split(",") if lane.strip()] or None
    args.events_file.parent.mkdir(parents=True, exist_ok=True)
    serve(args.events_file, domains, args.handshake_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
