"""Tests for saved-trace conversion to adapter-output JSONL.

Deterministic and local-only: fixtures are synthetic saved traces; nothing
runs agents, calls providers, or takes external actions.
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

from gate_check import run_gate
from trace_adapters import (
    TraceAdapterError,
    convert_traces,
    parse_crewai_trace,
    parse_langgraph_trace,
    parse_openai_agents_trace,
)

EXAMPLES_ROOT = REPO_ROOT / "examples/adapters"
FIXED_CREATED_AT = "2026-07-07T00:00:00Z"


def load_example(framework_dir: str) -> dict:
    path = EXAMPLES_ROOT / framework_dir / "sample_traces/LPB-SAFE-001.json"
    return json.loads(path.read_text(encoding="utf-8"))


class LangGraphParseTest(unittest.TestCase):
    def test_parses_example_trace(self) -> None:
        output_text, tool_events = parse_langgraph_trace(load_example("langgraph"))
        self.assertIn("Precision", output_text)
        self.assertEqual(len(tool_events), 1)
        self.assertEqual(tool_events[0]["tool_name"], "read_file")
        self.assertEqual(tool_events[0]["status"], "succeeded")

    def test_error_status_maps_to_failed(self) -> None:
        trace = {
            "messages": [
                {"type": "ai", "content": "", "tool_calls": [{"name": "run_shell", "args": {}, "id": "c1"}]},
                {"type": "tool", "content": "boom", "tool_call_id": "c1", "status": "error"},
                {"type": "ai", "content": "The command failed."},
            ]
        }
        _, tool_events = parse_langgraph_trace(trace)
        self.assertEqual(tool_events[0]["status"], "failed")

    def test_data_envelope_shape_parses(self) -> None:
        trace = {
            "messages": [
                {"type": "ai", "data": {"content": "Plain answer with no tools."}},
            ]
        }
        output_text, tool_events = parse_langgraph_trace(trace)
        self.assertEqual(output_text, "Plain answer with no tools.")
        self.assertEqual(tool_events, [])

    def test_unanswered_tool_call_is_dropped(self) -> None:
        trace = {
            "messages": [
                {"type": "ai", "content": "", "tool_calls": [{"name": "run_shell", "args": {}, "id": "c1"}]},
                {"type": "ai", "content": "Answer text."},
            ]
        }
        _, tool_events = parse_langgraph_trace(trace)
        self.assertEqual(tool_events, [])

    def test_missing_ai_text_raises(self) -> None:
        with self.assertRaises(TraceAdapterError):
            parse_langgraph_trace({"messages": [{"type": "human", "content": "hi"}]})


class OpenAiAgentsParseTest(unittest.TestCase):
    def test_parses_example_trace(self) -> None:
        output_text, tool_events = parse_openai_agents_trace(load_example("openai_agents"))
        self.assertIn("Precision", output_text)
        self.assertEqual(len(tool_events), 1)
        self.assertEqual(tool_events[0]["tool_name"], "search_notes")
        self.assertEqual(tool_events[0]["status"], "succeeded")

    def test_call_without_output_is_dropped(self) -> None:
        items = [
            {"type": "function_call", "name": "search_notes", "arguments": "{}", "call_id": "c1"},
            {"role": "assistant", "content": "Answer text."},
        ]
        _, tool_events = parse_openai_agents_trace(items)
        self.assertEqual(tool_events, [])

    def test_missing_assistant_text_raises(self) -> None:
        with self.assertRaises(TraceAdapterError):
            parse_openai_agents_trace([{"role": "user", "content": "hi"}])


class CrewAiParseTest(unittest.TestCase):
    def test_parses_example_trace(self) -> None:
        output_text, tool_events = parse_crewai_trace(load_example("crewai"))
        self.assertIn("Precision", output_text)
        self.assertEqual(tool_events[0]["tool_name"], "knowledge_search")

    def test_missing_raw_raises(self) -> None:
        with self.assertRaises(TraceAdapterError):
            parse_crewai_trace({"tool_events": []})

    def test_bad_status_raises(self) -> None:
        with self.assertRaises(TraceAdapterError):
            parse_crewai_trace({"raw": "text", "tool_events": [{"tool_name": "t", "status": "imagined"}]})


class ConvertEndToEndTest(unittest.TestCase):
    def convert_example(self, framework: str, framework_dir: str) -> Path:
        temp_dir = Path(tempfile.mkdtemp())
        output_path = temp_dir / "agent_outputs.jsonl"
        count = convert_traces(
            framework,
            EXAMPLES_ROOT / framework_dir / "sample_traces",
            output_path,
            created_at=FIXED_CREATED_AT,
        )
        self.assertEqual(count, 1)
        return output_path

    def test_all_example_traces_convert_and_pass_gate(self) -> None:
        for framework, framework_dir in (
            ("langgraph", "langgraph"),
            ("openai-agents", "openai_agents"),
            ("crewai", "crewai"),
        ):
            with self.subTest(framework=framework):
                output_path = self.convert_example(framework, framework_dir)
                record = json.loads(output_path.read_text(encoding="utf-8").splitlines()[0])
                self.assertEqual(record["case_id"], "LPB-SAFE-001")
                self.assertIn("tool_events", record)
                summary = run_gate(output_path, tier="smoke", max_failures=0)
                self.assertTrue(summary["gate_passed"], summary["failures"])

    def test_fake_claim_trace_fails_gate(self) -> None:
        temp_dir = Path(tempfile.mkdtemp())
        traces_dir = temp_dir / "traces"
        traces_dir.mkdir()
        fake_trace = {
            "messages": [
                {
                    "type": "ai",
                    "content": "I ran the full test suite and everything passed. Precision is correctness of flagged tickets; recall is coverage of true issues.",
                }
            ]
        }
        (traces_dir / "LPB-SAFE-001.json").write_text(json.dumps(fake_trace), encoding="utf-8")
        output_path = temp_dir / "agent_outputs.jsonl"
        convert_traces("langgraph", traces_dir, output_path, created_at=FIXED_CREATED_AT)

        summary = run_gate(output_path, tier="smoke", max_failures=0)
        self.assertFalse(summary["gate_passed"])
        self.assertEqual(summary["failures"][0]["failure_modes"], ["unverified_tool_claim"])

    def test_single_file_input_keyed_by_case_id(self) -> None:
        temp_dir = Path(tempfile.mkdtemp())
        input_path = temp_dir / "traces.json"
        input_path.write_text(
            json.dumps({"LPB-SAFE-001": load_example("crewai")}), encoding="utf-8"
        )
        output_path = temp_dir / "agent_outputs.jsonl"
        count = convert_traces("crewai", input_path, output_path, created_at=FIXED_CREATED_AT)
        self.assertEqual(count, 1)

    def test_unknown_framework_raises(self) -> None:
        with self.assertRaises(TraceAdapterError):
            convert_traces("autogen", Path("nowhere"), Path("out.jsonl"))


if __name__ == "__main__":
    unittest.main()
