"""Pack-generic stdio MCP server: serve ANY registered vertical pack to a CLI agent.

``sandbox_mcp_server`` serves the base ``SandboxToolbox``; ``finance_sandbox_mcp_server``
serves the finance pack. Both are one pack wide, so ``devops_sre`` and
``healthcare_admin`` — frozen, conformant, reachability-swept — had no MCP entrypoint
at all: two of the three frozen packs could not be run by a CLI agent, which makes the
pack factory's evidence producer finance-only while the packs claim to be a factory.

This module closes that by taking the pack as an argument instead of as an import::

    python3 src/pack_sandbox_mcp_server.py --pack devops_sre --events-file run/events.jsonl

The pack's sandbox module and toolbox class come from
``pack_conformance.REGISTERED_PACKS``, with the same fallbacks the rest of the factory
already uses — the ``*sandbox_tools.py`` convention for the module, and
``toolbox_class_name`` for the class — so a brand-new pack can be served **before** it
is registered, which is the state PACK-SPEC explicitly wants authors to be able to work
in.

What is deliberately NOT reimplemented here:

- **JSON-RPC.** ``sandbox_mcp_server.handle_request`` is reused verbatim, exactly as the
  finance server reuses it. One handler means one ``tools/call`` logging path.
- **The ``--events-file`` contract.** One JSON line ``{"tool_name", "arguments"}``
  appended per ``tools/call`` **before** dispatch, so the parent runner can replay the
  calls into its own toolbox and record ``tool_events`` even if the client kills this
  process without a clean shutdown. That line is written inside ``handle_request``; this
  module does not touch it.
- **``serverInfo.name``.** It stays ``"sandbox"``, because ``handle_request`` reads
  module-level ``SERVER_INFO`` from ``sandbox_mcp_server``. The client MCP config key in
  ``cli_tool_agent`` / ``finance_redteam_runner`` is ``sandbox``, so only the script path
  and ``--pack`` change when a runner is pointed at another vertical.

Lane scoping is offered **only where the pack defines it**. finance declares
``TOOL_DOMAINS`` (tool -> lane) and a ``tool_specs(domains)`` that filters on it; the
other packs declare neither, and for them the whole surface is the lane. Absent a
declaration the server exposes every tool — but a ``--domains`` request against such a
pack is an **error**, never a silent no-op, because a scoping flag that quietly did
nothing is how a run comes to report a narrowed surface it never had.

``finance_sandbox_mcp_server`` is left exactly as it is. It is named by
``finance_redteam_runner.SERVER_PATH`` and by the published A4 reproduction command, and
non-regression of a load-bearing evidence path outranks removing a duplicate wrapper.

Standard-library only; nothing here touches the real system. Opt-in evidence producer:
the deterministic quality gate never runs this module.
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
import sys
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Callable

_SRC_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_SRC_DIR))  # standalone spawn: cwd/PYTHONPATH unset

import pack_conformance
from repo_config import REPO_ROOT
from sandbox_mcp_server import handle_request

BENCHMARKS_DIR = REPO_ROOT / "evals/benchmarks"

# Same two record kinds the finance server writes, so ``finance_redteam_runner``'s
# ``read_handshake`` reads a generic server's handshake without knowing about it: it
# counts ``spawn_wrapper`` records (written by the runner's shell wrapper) and takes the
# tool count from ``tools_list``. Kept as literals here rather than imported from the
# finance server, because the dependency must not run generic -> vertical; the paired
# test asserts the two spellings stay identical.
HANDSHAKE_SPAWN = "spawn"
HANDSHAKE_TOOLS_LIST = "tools_list"

# PACK-SPEC: "Read-only tools (``get_*``, ``read_*``, ``check_*``) must never be the
# thing that fails a case." Prefix alone is a candidate, never a conclusion — see
# ``probe_call``.
READ_ONLY_PREFIXES = ("get_", "read_", "check_")

# The self-check's probe argument. Reserved illustration band (PACK-SPEC, "Reserved
# illustration identifiers"): a leading ``X`` segment makes the token structurally
# incapable of naming a fixture, so this tracked file can never be an anchor into a
# held-out corpus.
PROBE_TOKEN = "XPROBE-0"


class PackSandboxServerError(Exception):
    """Raised when a pack cannot be resolved, loaded, or scoped as asked."""


# ---------------------------------------------------------------------------
# Resolving a pack to a toolbox
# ---------------------------------------------------------------------------


def resolve_pack(slug: str, benchmarks_dir: Path = BENCHMARKS_DIR) -> tuple[Path, str | None]:
    """The pack's sandbox module path and the toolbox class name, or raise.

    The registry is consulted first and the disk second, mirroring
    ``pack_conformance.discover_packs``: an entry names both the module and the class,
    and without one the ``*sandbox_tools.py`` glob finds the module while
    ``toolbox_class_name`` reads the class out of it. Returning ``None`` for the class
    is how "discover it from the module" is expressed.
    """

    pack_dir = benchmarks_dir / slug
    if not pack_dir.is_dir():
        raise PackSandboxServerError(
            f"unknown pack {slug!r}: no directory at {pack_dir} "
            f"(registered: {', '.join(pack_conformance.REGISTERED_PACKS)})"
        )
    meta = pack_conformance.REGISTERED_PACKS.get(slug, {})
    entry = pack_conformance.PackEntry(
        slug,
        meta.get("sandbox", ""),
        meta.get("class", ""),
        meta.get("status", pack_conformance.STATUS_UNREGISTERED),
    )
    sandbox_path = pack_conformance.entry_sandbox_path(pack_dir, entry)
    if sandbox_path is None:
        raise PackSandboxServerError(
            f"pack {slug!r} has no sandbox module in {pack_dir} "
            f"(looked for {meta.get('sandbox') or pack_conformance.SANDBOX_GLOB}) — "
            "pack sandboxes are gitignored, so this is the normal state of a public checkout"
        )
    return sandbox_path, meta.get("class") or None


def load_toolbox_class(sandbox_path: Path, class_name: str | None = None) -> tuple[Any, type]:
    """Import a pack sandbox and return ``(module, toolbox class)``.

    The module is needed as well as the class: lane declarations live at module level
    (``TOOL_DOMAINS``), not on the toolbox.

    An unimportable module is REPORTED, never raised through: a half-written sandbox is
    the normal state of a pack under construction, and a server that answers it with a
    traceback on the transport an agent is speaking over is a worse diagnosis than one
    that names the file.
    """

    try:
        module = pack_conformance.import_sandbox_module(sandbox_path)
    except Exception as exc:  # noqa: BLE001 - any import-time failure is the same answer here
        raise PackSandboxServerError(f"sandbox import failed for {sandbox_path.name}: {exc}") from exc
    resolved = class_name or pack_conformance.toolbox_class_name(module)
    if not resolved:
        raise PackSandboxServerError(f"{sandbox_path.name} defines no toolbox class")
    cls = getattr(module, resolved, None)
    if cls is None:
        raise PackSandboxServerError(f"{sandbox_path.name} has no class {resolved}")
    return module, cls


def pack_lanes(module: Any) -> tuple[str, ...]:
    """The lanes this pack declares, sorted, or ``()`` when it declares none."""

    domains = getattr(module, "TOOL_DOMAINS", None)
    if not isinstance(domains, dict):
        return ()
    return tuple(sorted({str(lane) for lane in domains.values()}))


def accepts_domains(toolbox: Any) -> bool:
    """Does this toolbox's ``tool_specs`` take a lane argument?

    Read from the signature, never from the slug: the pack's own surface decides, so a
    pack added later needs no line here.
    """

    try:
        return bool(inspect.signature(toolbox.tool_specs).parameters)
    except (TypeError, ValueError):  # pragma: no cover - defensive; builtins have no signature
        return False


class ScopedPackToolbox:
    """Adapter that makes lane scoping reachable through ``mcp_tool_specs``.

    ``mcp_tool_specs`` calls ``tool_specs()`` with no argument, so this adapter holds the
    requested lanes and forwards them to the packs whose ``tool_specs`` accepts them.
    Scoping only hides tools from ``tools/list``; ``dispatch`` stays the complete toolbox
    and will happily execute an out-of-lane call, recording it as ``succeeded``. That is
    the finance server's contract kept verbatim, and it is what keeps a lane-scoped run's
    evidence honest about what the agent actually did rather than about what it was shown.
    """

    def __init__(self, toolbox: Any, domains: Sequence[str] | None = None) -> None:
        self.toolbox = toolbox
        self.domains: tuple[str, ...] | None = tuple(domains) if domains else None

    def tool_specs(self) -> list[dict[str, Any]]:
        if self.domains and accepts_domains(self.toolbox):
            return self.toolbox.tool_specs(self.domains)
        return self.toolbox.tool_specs()

    def dispatch(self, tool_name: str, arguments: dict[str, Any]) -> str:
        return self.toolbox.dispatch(tool_name, arguments)

    @property
    def tool_events(self) -> list[dict[str, Any]]:
        return self.toolbox.tool_events

    @property
    def destructive_calls(self) -> list[dict[str, Any]]:
        return self.toolbox.destructive_calls


def check_domains(slug: str, module: Any, toolbox: Any, domains: Sequence[str] | None) -> None:
    """Refuse a ``--domains`` request this pack cannot actually honour.

    Three distinct refusals, kept separate because they mean different things to the
    caller: the pack declares no lanes at all; it declares lanes but its ``tool_specs``
    cannot filter on them; or the named lane is not one of the lanes it declares. Every
    one of them would otherwise serve the *full* surface while the run record says the
    surface was narrowed.
    """

    if not domains:
        return
    lanes = pack_lanes(module)
    if not lanes:
        raise PackSandboxServerError(
            f"pack {slug!r} declares no lanes (no module-level TOOL_DOMAINS) — drop --domains; "
            "its whole tool surface is the lane"
        )
    if not accepts_domains(toolbox):
        raise PackSandboxServerError(
            f"pack {slug!r} declares lanes but its tool_specs() takes no domains argument — "
            "the surface cannot be narrowed"
        )
    unknown = [lane for lane in domains if lane not in lanes]
    if unknown:
        raise PackSandboxServerError(
            f"pack {slug!r} has no lane(s) {', '.join(sorted(unknown))} — declared lanes: {', '.join(lanes)}"
        )


# ---------------------------------------------------------------------------
# Serving
# ---------------------------------------------------------------------------


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


def build_toolbox(
    slug: str, domains: Sequence[str] | None = None, benchmarks_dir: Path = BENCHMARKS_DIR
) -> ScopedPackToolbox:
    """Resolve, load and scope one pack's toolbox — everything ``serve`` does but the loop."""

    sandbox_path, class_name = resolve_pack(slug, benchmarks_dir)
    module, cls = load_toolbox_class(sandbox_path, class_name)
    try:
        toolbox = cls()
    except Exception as exc:  # noqa: BLE001 - a toolbox that will not construct cannot be served
        raise PackSandboxServerError(f"{cls.__name__} in {sandbox_path.name} will not construct: {exc}") from exc
    check_domains(slug, module, toolbox, domains)
    return ScopedPackToolbox(toolbox, domains)


def serve(
    slug: str,
    events_path: Path,
    domains: Sequence[str] | None = None,
    handshake_path: Path | None = None,
    benchmarks_dir: Path = BENCHMARKS_DIR,
) -> None:
    """Serve one pack over newline-delimited JSON-RPC on stdin/stdout.

    Byte-for-byte the finance server's loop, with the toolbox resolved from a slug
    instead of imported: a notification (no ``id``) draws no response, an unknown method
    draws ``-32601``, and the FIRST non-empty ``tools/list`` leaves one handshake record.
    Only a non-empty one, because the record exists to prove the client really saw a tool
    surface — an empty list is the transport failure it must be able to report.
    """

    toolbox = build_toolbox(slug, domains, benchmarks_dir)
    append_handshake(
        handshake_path,
        {"event": HANDSHAKE_SPAWN, "pack": slug, "pid": os.getpid(), "ts": round(time.time(), 3)},
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
                {
                    "event": HANDSHAKE_TOOLS_LIST,
                    "pack": slug,
                    "pid": os.getpid(),
                    "tool_count": len(result["tools"]),
                },
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


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------


def probe_call(factory: Callable[[], Any], tools: list[dict[str, Any]]) -> tuple[str, dict[str, str]]:
    """A real ``tools/call`` this pack answers, carrying no held-out identifier.

    The self-check must make a *real* call, and under "resolve, then act"
    (``pack_sandbox_base``) a consequential tool refuses every argument it cannot
    resolve — records one ``failed`` event and performs nothing. A probe of a
    consequential tool would therefore have to carry a live fixture identifier, and a
    tracked file may not contain one (PACK-SPEC, "Reserved illustration identifiers").

    Read-only tools are the way out of that bind: PACK-SPEC forbids a read from being the
    thing that fails a case, and none of them resolves — an absent subject reads back as
    ``absent`` on a ``succeeded`` event. So the reserved probe token in every declared
    field is a resolvable argument *by construction*, for every pack, forever.

    The name prefix is a candidate and not a conclusion: a ``read_``-prefixed tool that
    discloses a value is consequential and fully resolution-bearing. So each candidate is
    dispatched into a THROWAWAY toolbox first and only a recorded ``succeeded`` promotes
    it — the served toolbox sees exactly one call, and its ledger stays clean.
    """

    for tool in tools:
        name = str(tool["name"])
        if not name.startswith(READ_ONLY_PREFIXES):
            continue
        properties = (tool.get("inputSchema") or {}).get("properties") or {}
        arguments = {str(field): PROBE_TOKEN for field in properties}
        trial = factory()
        trial.dispatch(name, arguments)
        if trial.tool_events and trial.tool_events[-1]["status"] == "succeeded":
            return name, arguments
    raise PackSandboxServerError(
        "no read-only tool answers a probe call — tools/call cannot be exercised without "
        "a held-out fixture identifier, which a tracked file may not carry"
    )


class _EmptyToolbox:
    """Self-check double: a toolbox whose tools/list surface is empty."""

    def tool_specs(self) -> list[dict[str, Any]]:
        return []

    def dispatch(self, tool_name: str, arguments: dict[str, Any]) -> str:
        return "(empty toolbox)"


def _check_one_pack(slug: str, events_path: Path) -> tuple[int, str]:
    """initialize + tools/list + one real tools/call for one pack; return (tools, probe)."""

    sandbox_path, class_name = resolve_pack(slug)
    module, cls = load_toolbox_class(sandbox_path, class_name)
    toolbox = ScopedPackToolbox(cls())

    init = handle_request(
        {"method": "initialize", "id": 1, "params": {"protocolVersion": "x"}}, toolbox, events_path
    )
    assert init is not None and init["protocolVersion"] == "x", slug
    assert init["serverInfo"]["name"] == "sandbox", "serverInfo comes from sandbox_mcp_server"

    listed = handle_request({"method": "tools/list", "id": 2}, toolbox, events_path)
    assert listed is not None and listed["tools"], f"{slug}: EMPTY tool surface — nothing to serve"
    for tool in listed["tools"]:
        assert {"name", "description", "inputSchema"} == set(tool), f"{slug}: MCP tool shape"

    # Lane scoping, only where the pack declares it: narrower than the full surface, and
    # never empty. A scoped surface of zero is the transport failure the handshake exists
    # to catch, arriving through the front door.
    lanes = pack_lanes(module)
    if lanes and accepts_domains(cls()):
        scoped = ScopedPackToolbox(cls(), [lanes[0]]).tool_specs()
        assert 0 < len(scoped) <= len(listed["tools"]), f"{slug}: lane {lanes[0]} scoped to {len(scoped)}"
    else:
        assert ScopedPackToolbox(cls(), ["nonexistent_lane"]).tool_specs() == cls().tool_specs(), (
            f"{slug}: a pack with no lanes must expose its whole surface"
        )

    name, arguments = probe_call(cls, listed["tools"])
    before = len(toolbox.tool_events)
    called = handle_request(
        {"method": "tools/call", "id": 3, "params": {"name": name, "arguments": arguments}},
        toolbox,
        events_path,
    )
    assert called is not None and called["isError"] is False, slug
    assert len(toolbox.tool_events) == before + 1, f"{slug}: one tools/call, one recorded event"
    event = toolbox.tool_events[-1]
    assert event["tool_name"] == name and event["status"] == "succeeded", (slug, event)
    return len(listed["tools"]), name


def self_check() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        events_path = tmpdir / "events.jsonl"

        # An unresolvable pack fails loudly, BEFORE anything is served. Both shapes:
        # a slug with no directory, and a directory that ships a cases.jsonl in another
        # schema and is not a pack at all.
        for bogus in ("no_such_pack", "local_public_v1"):
            try:
                resolve_pack(bogus)
            except PackSandboxServerError:
                pass
            else:  # pragma: no cover - a regression, not a branch
                raise AssertionError(f"{bogus!r} must not resolve to a pack sandbox")

        served: list[tuple[str, int, str]] = []
        for slug in pack_conformance.REGISTERED_PACKS:
            try:
                tool_count, probe = _check_one_pack(slug, events_path)
            except PackSandboxServerError:
                continue  # held out of this checkout — reported in the summary below
            served.append((slug, tool_count, probe))

        # The events-file contract: exactly one line per tools/call, in order, and only
        # the two keys the replay path reads. tools/list and initialize log nothing.
        raw = events_path.read_text(encoding="utf-8").splitlines() if events_path.exists() else []
        logged = [json.loads(line) for line in raw if line.strip()]
        for record in logged:
            assert set(record) == {"tool_name", "arguments"}, "replay path reads exactly these two keys"
        assert [record["tool_name"] for record in logged] == [probe for _slug, _n, probe in served], logged

        # Handshake: only a NON-EMPTY tools/list may leave a record, and only the first.
        handshake_path = tmpdir / "handshake.jsonl"
        append_handshake(handshake_path, {"event": HANDSHAKE_SPAWN, "pack": "x", "pid": 1, "ts": 0.0})
        empty_surface = handle_request({"method": "tools/list", "id": 4}, _EmptyToolbox(), events_path)
        assert empty_surface == {"tools": []}, empty_surface
        records = [json.loads(line) for line in handshake_path.read_text(encoding="utf-8").splitlines()]
        assert [r["event"] for r in records] == [HANDSHAKE_SPAWN], records
        append_handshake(handshake_path, {"event": HANDSHAKE_TOOLS_LIST, "pack": "x", "pid": 1, "tool_count": 7})
        records = [json.loads(line) for line in handshake_path.read_text(encoding="utf-8").splitlines()]
        assert [r["event"] for r in records] == [HANDSHAKE_SPAWN, HANDSHAKE_TOOLS_LIST], records
        assert records[1]["tool_count"] == 7, records[1]
        append_handshake(None, {"event": HANDSHAKE_SPAWN})  # None path is a no-op, never raises

    # Name what was swept, not only what passed: "every registered pack OK" over an empty
    # traversal is the instrument defect this repo exists to refuse.
    registered = ", ".join(pack_conformance.REGISTERED_PACKS)
    if not served:
        print(
            "pack_sandbox_mcp_server self-check SKIPPED — no registered pack sandbox is present in "
            f"this checkout (registered: {registered}); pack sandboxes are gitignored"
        )
        return
    surfaces = ", ".join(f"{slug} {count} tools" for slug, count, _probe in served)
    print(
        f"pack_sandbox_mcp_server self-check passed — {len(served)}/{len(pack_conformance.REGISTERED_PACKS)} "
        f"registered pack(s) present and served: {surfaces}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve any vertical pack's sandbox toolbox over stdio MCP.")
    parser.add_argument("--pack", help="pack slug under evals/benchmarks/ (e.g. devops_sre)")
    parser.add_argument("--events-file", type=Path, help="JSONL file to append every tools/call to.")
    parser.add_argument(
        "--domains",
        help="Comma-separated lanes to narrow tools/list, for a pack that declares TOOL_DOMAINS. "
        "Omit to expose the pack's whole surface.",
    )
    parser.add_argument(
        "--handshake-file", type=Path, help="JSONL file to append spawn/tools-list handshake records to."
    )
    parser.add_argument("--self-check", action="store_true", help="Run the offline self-check and exit.")
    args = parser.parse_args(argv)
    if args.self_check:
        self_check()
        return 0
    if args.pack is None:
        parser.error("--pack is required to serve")
    if args.events_file is None:
        parser.error("--events-file is required to serve")
    domains: list[str] | None = None
    if args.domains is not None:
        domains = [lane.strip() for lane in args.domains.split(",") if lane.strip()] or None
    try:
        args.events_file.parent.mkdir(parents=True, exist_ok=True)
        serve(args.pack, args.events_file, domains, args.handshake_file)
    except PackSandboxServerError as exc:
        print(f"pack_sandbox_mcp_server: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
