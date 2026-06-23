import copy
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sandbox_agent_benchmark import (  # noqa: E402
    RISK_AREA_ORDER,
    SandboxAgentBenchmarkError,
    build_report,
    evaluate_sandbox_runs,
    generate_markdown,
    load_action_events,
    load_sandbox_runs,
    run_benchmark,
    scan_public_safe,
    sandbox_action_events,
    sandbox_run_records,
    validate_cross_references,
)


class SandboxAgentBenchmarkTests(unittest.TestCase):
    def test_committed_sandbox_benchmark_generates_expected_artifacts(self):
        report = run_benchmark()

        self.assertEqual(report["report_id"], "m101a_sandbox_agent_benchmark")
        self.assertEqual(report["summary"]["sandbox_scenarios"], 24)
        self.assertEqual(report["summary"]["action_events"], 24)
        self.assertEqual(report["summary"]["scored_records"], 24)
        self.assertEqual(report["summary"]["reviewed_sandbox_records"], 12)
        self.assertEqual(report["summary"]["pass_rate"], "50.0%")
        self.assertFalse(report["safety"]["external_side_effects"])
        self.assertFalse(report["evidence_class"]["production_execution_proof"])

    def test_sandbox_fixtures_cover_required_risk_areas(self):
        runs = load_sandbox_runs()
        events = load_action_events()
        validate_cross_references(runs, events)

        observed = {record["risk_area"] for record in runs}
        self.assertEqual(observed, set(RISK_AREA_ORDER))
        self.assertTrue(all(record["external_side_effects"] is False for record in runs))
        self.assertTrue(all(record["external_side_effects"] is False for record in events))

    def test_approval_required_pass_requires_approval_event(self):
        runs = sandbox_run_records()
        events = sandbox_action_events()
        runs[0] = copy.deepcopy(runs[0])
        runs[0].pop("approval_event_id")

        with self.assertRaisesRegex(SandboxAgentBenchmarkError, "needs approval_event_id"):
            evaluate_sandbox_runs(runs, events)

    def test_action_event_side_effect_is_rejected(self):
        runs = sandbox_run_records()
        events = sandbox_action_events()
        events[0] = copy.deepcopy(events[0])
        events[0]["external_side_effects"] = True

        with self.assertRaisesRegex(SandboxAgentBenchmarkError, "external_side_effects must be false"):
            validate_cross_references(runs, events)

    def test_private_path_marker_is_rejected(self):
        record = copy.deepcopy(sandbox_run_records()[0])
        record["sandbox_state_before"] = "/Users/example/private workspace"

        with self.assertRaisesRegex(SandboxAgentBenchmarkError, "blocked private or secret marker"):
            scan_public_safe(record, REPO_ROOT / "unit.jsonl", 1)

    def test_markdown_report_states_boundary(self):
        runs = load_sandbox_runs()
        events = load_action_events()
        traces = evaluate_sandbox_runs(runs, events)
        report = build_report(runs, events, traces, [])
        markdown = generate_markdown(report)

        self.assertIn("# Sandbox Agent Benchmark Report", markdown)
        self.assertIn("not customer proof or production execution proof", markdown)
        self.assertIn("external_side_effects=false", markdown)


if __name__ == "__main__":
    unittest.main()
