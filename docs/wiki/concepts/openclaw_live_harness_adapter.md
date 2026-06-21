# OpenClaw Live Harness Adapter

The OpenClaw live harness adapter is the M63 adapter boundary for evaluating
OpenClaw-style agent behavior through the M61 sandbox and M62 action-boundary
evidence contracts.

The committed M63 adapter is a public-safe smoke fixture generator, not a live
OpenClaw launcher. It validates a schema-backed adapter plan and emits:

- one normalized saved-transcript fixture;
- one M61-compatible public-safe tool-call summary;
- one scored smoke trace and reader-facing report through saved transcript
  replay.

## Artifacts

- Adapter plan: `traces/external/openclaw_harness_adapter_plan.example.json`
- Adapter schema: `schemas/openclaw_harness_adapter.schema.json`
- Fixture generator: `src/openclaw_harness_adapter.py`
- Normalized transcript: `traces/external/openclaw_harness_smoke_transcript.example.jsonl`
- Tool summary: `traces/external/openclaw_harness_tool_summaries.example.jsonl`
- Scored trace: `traces/scored/openclaw_harness_smoke_eval.jsonl`
- Smoke report: `reports/comparisons/openclaw_harness_smoke_report.md`
- Tests: `tests/test_openclaw_harness_adapter.py`

## Runtime Boundary

The plan names the future opt-in controls for live OpenClaw collection:

- `--live-openclaw`
- `AGENT_EVALS_ENABLE_LIVE_OPENCLAW`
- disposable workspace required
- raw output path under `traces/raw/*.local.jsonl`
- tools disabled, mocked, or sandboxed
- no credentials, network access, or external actions in committed examples

Those controls are metadata in M63. The deterministic quality gate validates
the plan, generates the public-safe fixture, and replays the saved transcript.
It does not launch OpenClaw, execute tools, read raw runtime output, or touch
external systems.

## Interpretation

OpenClaw is labeled as the system under test. Agent Behavior Evals Lab remains
the evaluator. The smoke report confirms that normalized transcript evidence can
flow through the existing scoring path, but it is not a live OpenClaw benchmark
and does not support production-safety or leaderboard claims.
