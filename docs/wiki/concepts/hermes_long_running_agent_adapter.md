# Hermes Long-Running Agent Adapter

The Hermes long-running agent adapter is the M64 adapter boundary for evaluating
memory and cross-session behavior from public-safe derivatives. Hermes or a
memory-capable long-running agent is the system under test; Agent Behavior Evals
Lab remains the evaluator.

The committed M64 adapter is a public-safe fixture generator, not a live Hermes
launcher. It validates a schema-backed adapter plan and emits:

- two normalized saved-transcript records;
- two session-boundary metadata records;
- four memory disclosure, persistence, approval-continuity, and uncertainty
  checks;
- one scored trace and reader-facing report through saved transcript replay.

## Artifacts

- Adapter plan: `traces/external/long_running_agent_adapter_plan.example.json`
- Adapter schema: `schemas/long_running_agent_adapter.schema.json`
- Session-boundary schema: `schemas/session_boundary_metadata.schema.json`
- Memory-check schema: `schemas/memory_persistence_check.schema.json`
- Fixture generator: `src/long_running_agent_adapter.py`
- Normalized transcripts: `traces/external/hermes_long_running_transcripts.example.jsonl`
- Session boundaries: `traces/external/hermes_session_boundaries.example.jsonl`
- Memory checks: `traces/external/hermes_memory_checks.example.jsonl`
- Scored trace: `traces/scored/hermes_long_running_agent_eval.jsonl`
- Report: `reports/comparisons/hermes_long_running_agent_report.md`
- Tests: `tests/test_long_running_agent_adapter.py`

## Runtime Boundary

The plan names the future opt-in controls for live Hermes-style collection:

- `--live-hermes`
- `AGENT_EVALS_ENABLE_LIVE_HERMES`
- disposable workspace required
- raw output and raw memory paths under `traces/raw/*.local.jsonl`
- tools disabled, mocked, or sandboxed
- private memory reads excluded from the deterministic quality gate
- public-safe memory summaries allowed only as reviewed derivatives

Those controls are metadata in M64. The deterministic quality gate validates the
plan, generates public-safe fixtures, validates session and memory metadata, and
replays selected assistant turns. It does not launch Hermes, read private
memory, execute tools, read raw runtime output, or touch external systems.

## Interpretation

M64 can show whether a public-safe saved transcript says the right things about
continuity, stale approval, and uncertainty. It cannot prove live Hermes
behavior, private-memory safety, production policy compliance, or leaderboard
quality. Private memory remains local-only and absent from committed fixtures;
only reviewed public-safe derivatives may be committed.
