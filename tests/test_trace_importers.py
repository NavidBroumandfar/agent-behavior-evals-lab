"""Tests for the config-driven trace importer.

Deterministic and local-only: synthetic public-safe logs, no providers,
no live agents, no external actions.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from trace_gate import run_trace_gate
from trace_importers import (
    TraceImportError,
    import_records,
    load_mapping,
    main,
    resolve_mapping_path,
    write_records,
)

EXAMPLES = REPO_ROOT / "examples/importers"
PRESETS = REPO_ROOT / "schemas/trace-mappings"


def write_json(payload, suffix=".json") -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8")
    if suffix == ".jsonl":
        for row in payload:
            handle.write(json.dumps(row) + "\n")
    else:
        json.dump(payload, handle)
    handle.close()
    return Path(handle.name)


class MappingValidationTests(unittest.TestCase):
    def test_presets_load(self) -> None:
        for preset in sorted(PRESETS.glob("*.json")):
            mapping = load_mapping(preset)
            self.assertTrue(mapping.get("name"), f"{preset.name} needs a name")

    def test_preset_resolves_by_name(self) -> None:
        self.assertEqual(resolve_mapping_path("generic-run-log").name, "generic-run-log.json")

    def test_unknown_preset_errors(self) -> None:
        with self.assertRaises(TraceImportError):
            resolve_mapping_path("no-such-mapping")

    def test_missing_required_selector_errors(self) -> None:
        path = write_json({"name": "x", "output_text": "out"})
        with self.assertRaises(TraceImportError):
            load_mapping(path)

    def test_invalid_json_mapping_errors(self) -> None:
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        handle.write("{not json")
        handle.close()
        with self.assertRaises(TraceImportError):
            load_mapping(Path(handle.name))


class GenericImportTests(unittest.TestCase):
    MAPPING = {
        "name": "t",
        "record_id": "id",
        "output_text": "output",
        "tool_events": {"path": "tool_calls", "tool_name": "name", "action": "arguments", "status": "status"},
        "status_map": {"ok": "succeeded", "error": "failed"},
    }

    def test_dotted_paths_and_status_map(self) -> None:
        source = write_json([{"id": "r1", "output": "I ran it.", "tool_calls": [{"name": "shell", "arguments": "pytest -q", "status": "ok"}]}])
        records = import_records(source, self.MAPPING)
        self.assertEqual(records[0]["record_id"], "r1")
        self.assertEqual(records[0]["tool_events"][0]["status"], "succeeded")

    def test_jsonl_input(self) -> None:
        source = write_json([{"id": "r1", "output": "a", "tool_calls": []}, {"id": "r2", "output": "b", "tool_calls": []}], suffix=".jsonl")
        self.assertEqual(len(import_records(source, self.MAPPING)), 2)

    def test_nested_record_path(self) -> None:
        mapping = dict(self.MAPPING, record_path="runs")
        source = write_json({"runs": [{"id": "r1", "output": "a", "tool_calls": []}]})
        self.assertEqual(import_records(source, mapping)[0]["record_id"], "r1")

    def test_missing_record_id_is_synthesized_and_unique(self) -> None:
        source = write_json([{"output": "a"}, {"output": "b"}])
        records = import_records(source, self.MAPPING)
        self.assertEqual(len({r["record_id"] for r in records}), 2)

    def test_missing_output_text_becomes_empty_string(self) -> None:
        source = write_json([{"id": "r1"}])
        self.assertEqual(import_records(source, self.MAPPING)[0]["output_text"], "")

    def test_unknown_status_passes_through(self) -> None:
        source = write_json([{"id": "r1", "output": "x", "tool_calls": [{"name": "t", "arguments": "a", "status": "weird"}]}])
        self.assertEqual(import_records(source, self.MAPPING)[0]["tool_events"][0]["status"], "weird")

    def test_empty_source_errors(self) -> None:
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        handle.write("")
        handle.close()
        with self.assertRaises(TraceImportError):
            import_records(Path(handle.name), self.MAPPING)


class OtelAttributeTests(unittest.TestCase):
    def test_otel_example_imports_with_attributes(self) -> None:
        mapping = load_mapping(PRESETS / "otel-genai.json")
        records = import_records(EXAMPLES / "otel_genai_spans.json", mapping)
        self.assertEqual(len(records), 2)
        self.assertIn("migration", records[0]["output_text"])
        event = records[0]["tool_events"][0]
        self.assertEqual(event["tool_name"], "shell")
        self.assertEqual(event["action"], "alembic upgrade head")
        self.assertEqual(event["status"], "succeeded")

    def test_plain_mapping_attributes_also_resolve(self) -> None:
        mapping = {
            "name": "t",
            "record_id": "id",
            "output_text": "attr:gen_ai.output.messages",
            "tool_events": {"path": "tools", "tool_name": "attr:gen_ai.tool.name", "action": "attr:args"},
        }
        source = write_json([{ "id": "r1", "attributes": {"gen_ai.output.messages": "hello"}, "tools": [{"attributes": {"gen_ai.tool.name": "shell", "args": "ls"}}]}])
        record = import_records(source, mapping)[0]
        self.assertEqual(record["output_text"], "hello")
        self.assertEqual(record["tool_events"][0]["tool_name"], "shell")


class EndToEndGateTests(unittest.TestCase):
    """Imported records must gate correctly — the whole point of the importer."""

    def _import_and_gate(self, example: str, preset: str):
        mapping = load_mapping(PRESETS / f"{preset}.json")
        records = import_records(EXAMPLES / example, mapping)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "records.jsonl"
            write_records(records, out)
            return run_trace_gate(out, max_failures=0)

    def test_generic_example_catches_lie_and_laundered_refusal(self) -> None:
        summary = self._import_and_gate("generic_run_log.json", "generic-run-log")
        self.assertFalse(summary["gate_passed"])
        by_id = {entry["record_id"]: entry for entry in summary["scored_records"]}
        self.assertTrue(by_id["run-101"]["passed"], "honest test-run record must pass")
        self.assertIn("unverified_tool_claim", by_id["run-102"]["failure_modes"])
        self.assertIn("contradicted_refusal_claim", by_id["run-103"]["failure_modes"])

    def test_otel_example_catches_partial_object_lie(self) -> None:
        summary = self._import_and_gate("otel_genai_spans.json", "otel-genai")
        self.assertFalse(summary["gate_passed"])
        self.assertEqual(summary["fail_count"], 1)


class PackRunLogRefusalTests(unittest.TestCase):
    """An imported trace is out of domain for pack scoring — refuse, don't approximate.

    A pack contract decides a violation from a breach verdict the pack's sandbox
    computes from its own fixture state. Nothing in a customer's log carries it,
    so a rebuilt ``action`` string cannot be scored against a pack either way
    round: reproduced on a frozen honest control, the sandbox-emitted action
    scores ``performed`` and the re-serialised one scores ``violation``, while
    widening the contract to tolerate the absent field scores a real, executed
    violation as clean. See ``src/validate_pack_run_log.py``.
    """

    BASE = {
        "name": "t",
        "record_id": "id",
        "output_text": "output",
        "tool_events": {"path": "tool_calls", "tool_name": "name", "action": "arguments"},
    }

    def test_mapping_naming_case_id_is_refused(self) -> None:
        path = write_json(dict(self.BASE, case_id="id"))
        with self.assertRaises(TraceImportError) as caught:
            load_mapping(path)
        self.assertIn("case_id", str(caught.exception))
        self.assertIn("pack", str(caught.exception))

    def test_mapping_naming_a_pack_is_refused(self) -> None:
        for key in ("pack", "pack_slug"):
            with self.subTest(key=key):
                with self.assertRaises(TraceImportError):
                    load_mapping(write_json(dict(self.BASE, **{key: "devops_sre"})))

    def test_mapping_naming_arguments_digest_is_refused(self) -> None:
        with self.assertRaises(TraceImportError):
            load_mapping(write_json(dict(self.BASE, arguments_digest="digest")))

    def test_event_level_arguments_digest_is_refused(self) -> None:
        events = dict(self.BASE["tool_events"], arguments_digest="digest")
        with self.assertRaises(TraceImportError):
            load_mapping(write_json(dict(self.BASE, tool_events=events)))

    def test_refusal_names_the_two_supported_routes(self) -> None:
        with self.assertRaises(TraceImportError) as caught:
            load_mapping(write_json(dict(self.BASE, case_id="id")))
        message = str(caught.exception)
        self.assertIn("gate_check", message)
        self.assertIn("sandbox", message)

    def test_ordinary_mappings_still_load(self) -> None:
        self.assertEqual(load_mapping(write_json(self.BASE))["record_id"], "id")

    def test_emitted_records_cannot_masquerade_as_a_pack_run_log(self) -> None:
        """The structural half of the refusal: the shape is never pack-shaped."""

        source = write_json([{"id": "r1", "output": "x", "tool_calls": [{"name": "t", "arguments": "a=b"}]}])
        record = import_records(source, self.BASE)[0]
        self.assertEqual(set(record), {"record_id", "output_text", "tool_events"})
        self.assertNotIn("case_id", record)
        for event in record["tool_events"]:
            self.assertNotIn("arguments_digest", event)


class CliTests(unittest.TestCase):
    def test_cli_writes_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.jsonl"
            code = main(["--input", str(EXAMPLES / "generic_run_log.json"), "--mapping", "generic-run-log", "--output", str(out)])
            self.assertEqual(code, 0)
            self.assertEqual(len(out.read_text(encoding="utf-8").strip().splitlines()), 3)

    def test_cli_returns_2_on_bad_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code = main(["--input", str(EXAMPLES / "generic_run_log.json"), "--mapping", "nope", "--output", str(Path(tmp) / "o.jsonl")])
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
