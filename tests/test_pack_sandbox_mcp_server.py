"""Tests for the pack-generic stdio MCP server.

The load-bearing properties, in the order a broken one would hurt:

1. **A non-empty tool surface per pack.** A server that resolves a pack and lists
   zero tools is the transport failure the handshake exists to report, arriving
   through the front door — the agent is then inert for reasons that have nothing
   to do with its behavior, and the run scores perfectly safe.
2. **The ``--events-file`` contract.** One JSON line ``{"tool_name", "arguments"}``
   per ``tools/call``, written BEFORE dispatch, in order, including the denied and
   failed calls — replaying those lines into a fresh toolbox must reproduce
   ``tool_events`` exactly, because that replay is what the scorer reads.
3. **An unknown pack fails cleanly**, naming the slug, with no traceback.
4. **Lane scoping only where the pack declares it**, and a refusal — never a
   silent no-op — where it does not.

Every test writes its own synthetic pack sandbox into a temp dir. No held-out pack
content, no repo fixtures, deterministic, offline, no providers.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pack_sandbox_mcp_server as psms

FINANCE_SERVER = SRC / "finance_sandbox_mcp_server.py"

# A minimal pack sandbox. ``read_vault`` is deliberately FIRST and deliberately
# ``read_``-prefixed while being consequential: it resolves its subject, so the probe
# must skip it and land on ``get_ticket``. That is the devops shape (a ``read_`` tool
# that discloses a value) which makes a name-prefix-only probe wrong.
SANDBOX_SRC = '''
import sys
from pathlib import Path

_SRC = Path(r"{src}")
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from pack_sandbox_base import PackSandboxBase, install_resolution_guard, resolve, summarize


class ProbeSandboxToolbox(PackSandboxBase):
    def __init__(self):
        super().__init__(actor_id="AGENT-PROBE-01")
        self.tickets = {{"XTCK-41": {{"state": "approved"}}}}

    def read_vault(self, vault_id: str = "") -> str:
        vault_id = resolve(self.tickets, vault_id, "vault_id", "vault")
        return self._record("read_vault", summarize(breach="none", vault=vault_id))

    def get_ticket(self, ticket_id: str = "") -> str:
        t = self.tickets.get(ticket_id, {{}})
        return self._record("get_ticket", summarize(ticket=ticket_id, state=t.get("state", "absent")))

    def do_thing(self, ticket_id: str = "") -> str:
        ticket_id = resolve(self.tickets, ticket_id, "ticket_id", "ticket")
        return self._record("do_thing", summarize(breach="none", ticket=ticket_id), destructive=True)

    def tool_specs(self):
        s = self._spec
        return [
            s("read_vault", "Read a vault value.", {{"vault_id": "Vault."}}),
            s("get_ticket", "Read a ticket.", {{"ticket_id": "Ticket."}}),
            s("do_thing", "Do the consequential thing.", {{"ticket_id": "Ticket."}}),
        ]


install_resolution_guard(ProbeSandboxToolbox, ["read_vault", "get_ticket", "do_thing"])
'''

# The other shape: a pack that DECLARES lanes, the way finance does — a module-level
# TOOL_DOMAINS plus a ``tool_specs`` that filters on it.
LANED_SANDBOX_SRC = '''
import sys
from pathlib import Path

_SRC = Path(r"{src}")
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from pack_sandbox_base import PackSandboxBase, summarize

TOOL_DOMAINS = {{"get_ticket": "shared", "get_alpha": "alpha", "get_beta": "beta"}}


class LanedSandboxToolbox(PackSandboxBase):
    def get_ticket(self, ticket_id: str = "") -> str:
        return self._record("get_ticket", summarize(ticket=ticket_id))

    def get_alpha(self, subject: str = "") -> str:
        return self._record("get_alpha", summarize(subject=subject))

    def get_beta(self, subject: str = "") -> str:
        return self._record("get_beta", summarize(subject=subject))

    def tool_specs(self, domains=None):
        s = self._spec
        specs = [
            s("get_ticket", "Read a ticket.", {{"ticket_id": "Ticket."}}),
            s("get_alpha", "Read alpha.", {{"subject": "Subject."}}),
            s("get_beta", "Read beta.", {{"subject": "Subject."}}),
        ]
        if domains is None:
            return specs
        wanted = {{str(d) for d in domains}} | {{"shared"}}
        return [item for item in specs if TOOL_DOMAINS.get(item["function"]["name"]) in wanted]
'''


def _write_pack(benchmarks: Path, slug: str, source: str, filename: str = "probe_sandbox_tools.py") -> Path:
    """Write one synthetic pack directory and return it."""

    pack_dir = benchmarks / slug
    pack_dir.mkdir(parents=True, exist_ok=True)
    (pack_dir / filename).write_text(source.format(src=str(SRC)), encoding="utf-8")
    return pack_dir


def _mcp_tools(toolbox) -> list[dict]:
    """The tools/list payload for a toolbox, without going through the JSON-RPC loop."""

    listed = psms.handle_request({"method": "tools/list", "id": 1}, toolbox, Path("/dev/null"))
    assert listed is not None
    return listed["tools"]


def _call(toolbox, events_path: Path, name: str, arguments: dict, request_id: int = 9) -> dict:
    result = psms.handle_request(
        {"method": "tools/call", "id": request_id, "params": {"name": name, "arguments": arguments}},
        toolbox,
        events_path,
    )
    assert result is not None
    return result


def _logged(events_path: Path) -> list[dict]:
    raw = events_path.read_text(encoding="utf-8").splitlines() if events_path.exists() else []
    return [json.loads(line) for line in raw if line.strip()]


class PackResolutionTests(unittest.TestCase):
    """Registry first, disk second — and a clean refusal when neither answers."""

    def test_unregistered_pack_is_discovered_from_disk(self) -> None:
        # The state PACK-SPEC wants an author to be able to work in: content on disk,
        # no REGISTERED_PACKS entry yet. The module is found by the *sandbox_tools.py
        # convention and the toolbox class is read out of the module itself.
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            _write_pack(bench, "probe_pack", SANDBOX_SRC)
            sandbox_path, class_name = psms.resolve_pack("probe_pack", bench)
            self.assertEqual(sandbox_path.name, "probe_sandbox_tools.py")
            self.assertIsNone(class_name, "an unregistered pack names no class — it is discovered")
            _module, cls = psms.load_toolbox_class(sandbox_path, class_name)
            self.assertEqual(cls.__name__, "ProbeSandboxToolbox")

    def test_registered_entry_names_the_module_and_the_class(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            _write_pack(bench, "probe_pack", SANDBOX_SRC, filename="custom_tools.py")
            registry = {"probe_pack": {"sandbox": "custom_tools.py", "class": "ProbeSandboxToolbox"}}
            with mock.patch.dict(psms.pack_conformance.REGISTERED_PACKS, registry, clear=True):
                sandbox_path, class_name = psms.resolve_pack("probe_pack", bench)
            self.assertEqual(sandbox_path.name, "custom_tools.py")
            self.assertEqual(class_name, "ProbeSandboxToolbox")

    def test_unknown_pack_raises_naming_the_slug(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(psms.PackSandboxServerError) as caught:
                psms.resolve_pack("no_such_pack", Path(d))
            self.assertIn("no_such_pack", str(caught.exception))

    def test_pack_directory_without_a_sandbox_module_raises(self) -> None:
        # The public-checkout shape: the pack directory exists (its docs are tracked)
        # and the sandbox is gitignored away. That must read as "held out", not crash.
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            (bench / "probe_pack").mkdir(parents=True)
            with self.assertRaises(psms.PackSandboxServerError) as caught:
                psms.resolve_pack("probe_pack", bench)
            self.assertIn("no sandbox module", str(caught.exception))

    def test_module_without_a_toolbox_class_raises(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            pack = _write_pack(bench, "probe_pack", SANDBOX_SRC)
            (pack / "probe_sandbox_tools.py").write_text("VALUE = 1\n", encoding="utf-8")
            sandbox_path, class_name = psms.resolve_pack("probe_pack", bench)
            with self.assertRaises(psms.PackSandboxServerError):
                psms.load_toolbox_class(sandbox_path, class_name)

    def test_broken_sandbox_module_is_reported_not_raised_through(self) -> None:
        # A half-written sandbox is the normal state of a pack under construction. It must
        # name the file, not answer the agent's transport with a traceback.
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            pack = _write_pack(bench, "probe_pack", SANDBOX_SRC)
            (pack / "probe_sandbox_tools.py").write_text("def broken(:\n", encoding="utf-8")
            with self.assertRaises(psms.PackSandboxServerError) as caught:
                psms.build_toolbox("probe_pack", None, bench)
            self.assertIn("sandbox import failed", str(caught.exception))

    def test_toolbox_that_will_not_construct_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            pack = _write_pack(bench, "probe_pack", SANDBOX_SRC)
            (pack / "probe_sandbox_tools.py").write_text(
                "class BadSandboxToolbox:\n"
                "    def __init__(self, required):\n"
                "        self.required = required\n"
                "    def tool_specs(self):\n"
                "        return []\n",
                encoding="utf-8",
            )
            with self.assertRaises(psms.PackSandboxServerError) as caught:
                psms.build_toolbox("probe_pack", None, bench)
            self.assertIn("will not construct", str(caught.exception))

    def test_main_reports_an_unknown_pack_without_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = psms.main(["--pack", "no_such_pack", "--events-file", str(Path(d) / "e.jsonl")])
            self.assertEqual(code, 2)
            self.assertIn("no_such_pack", stderr.getvalue())

    def test_serving_requires_a_pack_and_an_events_file(self) -> None:
        # Both are hard requirements: the events file IS the evidence channel, so a
        # server that ran without one would produce a run nothing could score.
        for argv in (["--events-file", "e.jsonl"], ["--pack", "probe_pack"]):
            with self.subTest(argv=argv), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    psms.main(argv)


class ToolSurfaceTests(unittest.TestCase):
    def test_tool_surface_is_non_empty_and_in_the_mcp_shape(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            _write_pack(bench, "probe_pack", SANDBOX_SRC)
            toolbox = psms.build_toolbox("probe_pack", None, bench)
            tools = _mcp_tools(toolbox)
            self.assertEqual(len(tools), 3)
            for tool in tools:
                self.assertEqual({"name", "description", "inputSchema"}, set(tool))
            self.assertEqual(
                [t["name"] for t in tools], ["read_vault", "get_ticket", "do_thing"], "order preserved"
            )

    def test_probe_call_skips_a_read_prefixed_consequential_tool(self) -> None:
        # Prefix is a candidate, never a conclusion. read_vault resolves its subject, so
        # the reserved probe token records a `failed` event there; the probe must move on
        # rather than report a call the sandbox refused.
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            _write_pack(bench, "probe_pack", SANDBOX_SRC)
            _sandbox, cls = psms.load_toolbox_class(*psms.resolve_pack("probe_pack", bench))
            name, arguments = psms.probe_call(cls, _mcp_tools(psms.ScopedPackToolbox(cls())))
            self.assertEqual(name, "get_ticket")
            self.assertEqual(arguments, {"ticket_id": psms.PROBE_TOKEN})

    def test_probe_call_raises_when_no_read_only_tool_answers(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            pack = _write_pack(bench, "probe_pack", SANDBOX_SRC)
            source = (pack / "probe_sandbox_tools.py").read_text(encoding="utf-8")
            # Drop the one clean read tool from the surface, leaving only the tools that
            # resolve. There is then no probe that does not need a held-out identifier.
            source = source.replace('            s("get_ticket", "Read a ticket.", {"ticket_id": "Ticket."}),\n', "")
            (pack / "probe_sandbox_tools.py").write_text(source, encoding="utf-8")
            _sandbox, cls = psms.load_toolbox_class(*psms.resolve_pack("probe_pack", bench))
            with self.assertRaises(psms.PackSandboxServerError):
                psms.probe_call(cls, _mcp_tools(psms.ScopedPackToolbox(cls())))

    def test_probe_argument_is_in_the_reserved_illustration_band(self) -> None:
        # PACK-SPEC: a tracked file may not carry a fixture identifier. The probe token
        # is structurally incapable of naming one.
        self.assertTrue(psms.PROBE_TOKEN.startswith("X"))
        self.assertIn("-", psms.PROBE_TOKEN)


class EventsFileContractTests(unittest.TestCase):
    def test_one_line_per_call_in_order_including_denied_and_failed(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            _write_pack(bench, "probe_pack", SANDBOX_SRC)
            events_path = bench / "events.jsonl"
            toolbox = psms.build_toolbox("probe_pack", None, bench)

            _mcp_tools(toolbox)  # tools/list must log nothing
            _call(toolbox, events_path, "get_ticket", {"ticket_id": "XTCK-41"}, 2)
            _call(toolbox, events_path, "liquidate_everything", {}, 3)  # unknown -> denied
            _call(toolbox, events_path, "do_thing", {"nonsense": 1}, 4)  # bad args -> failed
            _call(toolbox, events_path, "do_thing", {"ticket_id": "XTCK-41"}, 5)

            logged = _logged(events_path)
            for record in logged:
                self.assertEqual({"tool_name", "arguments"}, set(record), "replay reads these two keys")
            self.assertEqual(
                [r["tool_name"] for r in logged],
                ["get_ticket", "liquidate_everything", "do_thing", "do_thing"],
            )
            self.assertEqual(
                [e["status"] for e in toolbox.tool_events],
                ["succeeded", "denied", "failed", "succeeded"],
            )

    def test_replaying_the_logged_lines_reproduces_the_served_events(self) -> None:
        # This is the assertion the scoring path depends on: the parent runner never sees
        # the served toolbox, only these lines.
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            _write_pack(bench, "probe_pack", SANDBOX_SRC)
            events_path = bench / "events.jsonl"
            toolbox = psms.build_toolbox("probe_pack", None, bench)
            _call(toolbox, events_path, "get_ticket", {"ticket_id": "XTCK-41"}, 2)
            _call(toolbox, events_path, "read_vault", {"vault_id": "XVLT-99"}, 3)  # unresolvable
            _call(toolbox, events_path, "do_thing", {"ticket_id": "XTCK-41"}, 4)

            _sandbox, cls = psms.load_toolbox_class(*psms.resolve_pack("probe_pack", bench))
            replayed = cls()
            for record in _logged(events_path):
                replayed.dispatch(str(record["tool_name"]), dict(record["arguments"]))
            self.assertEqual(replayed.tool_events, toolbox.tool_events)

    def test_an_unresolvable_argument_records_one_failed_event_with_no_breach(self) -> None:
        # Resolve-then-act, seen through the MCP bridge: the served surface must not be a
        # way around it, or the bridge would emit a verdict the sandbox refused to make.
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            _write_pack(bench, "probe_pack", SANDBOX_SRC)
            events_path = bench / "events.jsonl"
            toolbox = psms.build_toolbox("probe_pack", None, bench)
            result = _call(toolbox, events_path, "do_thing", {"ticket_id": "XTCK-000"})
            self.assertFalse(result["isError"], "a refused action is a recorded outcome, not a transport error")
            self.assertEqual(len(toolbox.tool_events), 1)
            event = toolbox.tool_events[0]
            self.assertEqual(event["status"], "failed")
            self.assertNotIn("breach=", event["action"])


class LaneScopingTests(unittest.TestCase):
    def test_lanes_narrow_the_surface_where_the_pack_declares_them(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            _write_pack(bench, "laned_pack", LANED_SANDBOX_SRC, filename="laned_sandbox_tools.py")
            full = _mcp_tools(psms.build_toolbox("laned_pack", None, bench))
            scoped = _mcp_tools(psms.build_toolbox("laned_pack", ["alpha"], bench))
            self.assertEqual([t["name"] for t in full], ["get_ticket", "get_alpha", "get_beta"])
            self.assertEqual([t["name"] for t in scoped], ["get_ticket", "get_alpha"], "lane plus shared")

    def test_scoping_hides_but_does_not_deny(self) -> None:
        # The finance server's contract, kept: an out-of-lane call still executes and
        # still records, so the evidence is about what the agent did, not what it saw.
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            _write_pack(bench, "laned_pack", LANED_SANDBOX_SRC, filename="laned_sandbox_tools.py")
            events_path = bench / "events.jsonl"
            toolbox = psms.build_toolbox("laned_pack", ["alpha"], bench)
            _call(toolbox, events_path, "get_beta", {"subject": "XSUB-1"})
            self.assertEqual(toolbox.tool_events[-1]["status"], "succeeded")

    def test_domains_against_a_pack_with_no_lanes_is_an_error(self) -> None:
        # Never a silent no-op: a scoping flag that quietly did nothing is how a run
        # comes to report a narrowed surface it never had.
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            _write_pack(bench, "probe_pack", SANDBOX_SRC)
            with self.assertRaises(psms.PackSandboxServerError) as caught:
                psms.build_toolbox("probe_pack", ["alpha"], bench)
            self.assertIn("declares no lanes", str(caught.exception))

    def test_an_undeclared_lane_is_an_error(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            _write_pack(bench, "laned_pack", LANED_SANDBOX_SRC, filename="laned_sandbox_tools.py")
            with self.assertRaises(psms.PackSandboxServerError) as caught:
                psms.build_toolbox("laned_pack", ["gamma"], bench)
            self.assertIn("gamma", str(caught.exception))

    def test_pack_lanes_and_accepts_domains_read_the_pack_not_the_slug(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            _write_pack(bench, "probe_pack", SANDBOX_SRC)
            _write_pack(bench, "laned_pack", LANED_SANDBOX_SRC, filename="laned_sandbox_tools.py")
            plain_module, plain_cls = psms.load_toolbox_class(*psms.resolve_pack("probe_pack", bench))
            laned_module, laned_cls = psms.load_toolbox_class(*psms.resolve_pack("laned_pack", bench))
            self.assertEqual(psms.pack_lanes(plain_module), ())
            self.assertEqual(psms.pack_lanes(laned_module), ("alpha", "beta", "shared"))
            self.assertFalse(psms.accepts_domains(plain_cls()))
            self.assertTrue(psms.accepts_domains(laned_cls()))


class ServeLoopTests(unittest.TestCase):
    """The stdio loop itself, driven end to end with a scripted stdin."""

    def _serve(self, bench: Path, slug: str, requests: list[dict], **kwargs) -> tuple[list[dict], Path, Path]:
        events_path = bench / "events.jsonl"
        handshake_path = bench / "handshake.jsonl"
        stdin = io.StringIO("\n".join(json.dumps(r) for r in requests) + "\n")
        stdout = io.StringIO()
        with mock.patch.object(sys, "stdin", stdin), mock.patch.object(sys, "stdout", stdout):
            psms.serve(slug, events_path, kwargs.get("domains"), handshake_path, bench)
        responses = [json.loads(line) for line in stdout.getvalue().splitlines() if line.strip()]
        return responses, events_path, handshake_path

    def test_initialize_list_call_and_an_unknown_method(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            _write_pack(bench, "probe_pack", SANDBOX_SRC)
            responses, events_path, _handshake = self._serve(
                bench,
                "probe_pack",
                [
                    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "x"}},
                    {"jsonrpc": "2.0", "method": "notifications/initialized"},
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                    {
                        "jsonrpc": "2.0",
                        "id": 3,
                        "method": "tools/call",
                        "params": {"name": "get_ticket", "arguments": {"ticket_id": "XTCK-41"}},
                    },
                    {"jsonrpc": "2.0", "id": 4, "method": "bogus"},
                ],
            )
            self.assertEqual([r["id"] for r in responses], [1, 2, 3, 4], "the notification drew no response")
            self.assertEqual(responses[0]["result"]["protocolVersion"], "x")
            self.assertEqual(responses[0]["result"]["serverInfo"]["name"], "sandbox")
            self.assertEqual(len(responses[1]["result"]["tools"]), 3)
            self.assertFalse(responses[2]["result"]["isError"])
            self.assertEqual(responses[3]["error"]["code"], -32601)
            self.assertEqual([r["tool_name"] for r in _logged(events_path)], ["get_ticket"])

    def test_malformed_and_blank_lines_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            _write_pack(bench, "probe_pack", SANDBOX_SRC)
            events_path = bench / "events.jsonl"
            stdin = io.StringIO('\n{not json}\n[1, 2]\n{"jsonrpc": "2.0", "id": 1, "method": "ping"}\n')
            stdout = io.StringIO()
            with mock.patch.object(sys, "stdin", stdin), mock.patch.object(sys, "stdout", stdout):
                psms.serve("probe_pack", events_path, None, None, bench)
            responses = [json.loads(line) for line in stdout.getvalue().splitlines() if line.strip()]
            self.assertEqual(len(responses), 1)
            self.assertEqual(responses[0]["result"], {})


class HandshakeTests(unittest.TestCase):
    def test_spawn_and_first_non_empty_tools_list_leave_one_record_each(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            bench = Path(d)
            _write_pack(bench, "probe_pack", SANDBOX_SRC)
            events_path = bench / "events.jsonl"
            handshake_path = bench / "handshake.jsonl"
            requests = [
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            ]
            stdin = io.StringIO("\n".join(json.dumps(r) for r in requests) + "\n")
            with mock.patch.object(sys, "stdin", stdin), mock.patch.object(sys, "stdout", io.StringIO()):
                psms.serve("probe_pack", events_path, None, handshake_path, bench)
            records = [json.loads(line) for line in handshake_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(
                [r["event"] for r in records], [psms.HANDSHAKE_SPAWN, psms.HANDSHAKE_TOOLS_LIST]
            )
            self.assertEqual(records[1]["tool_count"], 3, "the surface the client really saw")
            self.assertEqual({r["pack"] for r in records}, {"probe_pack"})

    def test_a_handshake_write_failure_never_breaks_serving(self) -> None:
        # The handshake is diagnostics. Losing it must degrade the diagnosis, never the run.
        with tempfile.TemporaryDirectory() as d:
            unwritable = Path(d) / "nope.jsonl"
            with mock.patch.object(Path, "open", side_effect=OSError("read-only")):
                psms.append_handshake(unwritable, {"event": psms.HANDSHAKE_SPAWN})
            self.assertFalse(unwritable.exists())
        psms.append_handshake(None, {"event": psms.HANDSHAKE_SPAWN})  # None path is a no-op

    def test_handshake_record_names_match_the_finance_server(self) -> None:
        # Read the finance server's SOURCE rather than importing it: importing needs the
        # held-out finance sandbox, which a public checkout does not have. The two
        # spellings must stay identical or finance_redteam_runner.read_handshake would
        # summarise a generic server's handshake as "never started".
        source = FINANCE_SERVER.read_text(encoding="utf-8")
        for constant, value in (
            ("HANDSHAKE_SPAWN", psms.HANDSHAKE_SPAWN),
            ("HANDSHAKE_TOOLS_LIST", psms.HANDSHAKE_TOOLS_LIST),
        ):
            with self.subTest(constant=constant):
                self.assertIn(f'{constant} = "{value}"', source)
        self.assertIn('"tool_count"', source)


class SelfCheckTests(unittest.TestCase):
    def test_self_check_runs_and_names_what_it_swept(self) -> None:
        # Locally this exercises every registered pack whose sandbox is present; in a
        # public checkout it must still pass and say SKIPPED rather than pass silently.
        stdout = io.StringIO()
        with mock.patch.object(sys, "stdout", stdout):
            psms.self_check()
        printed = stdout.getvalue()
        self.assertTrue(printed.strip(), "the self-check must say what it swept")
        self.assertTrue(
            "self-check passed" in printed or "self-check SKIPPED" in printed, printed
        )

    def test_self_check_exits_zero_through_main(self) -> None:
        with mock.patch.object(sys, "stdout", io.StringIO()):
            self.assertEqual(psms.main(["--self-check"]), 0)


if __name__ == "__main__":
    unittest.main()
