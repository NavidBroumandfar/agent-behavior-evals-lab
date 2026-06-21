# Milestone 64 - Hermes Or Long-Running Agent Adapter

Date: 2026-06-21

Status: Complete / public-safe session review-ready

Milestone 64 adds a schema-backed adapter boundary for Hermes-style or
long-running memory-capable agents. The committed adapter is a deterministic
public-safe fixture generator, not a live Hermes launcher. It emits normalized
saved transcripts, session-boundary metadata, and memory checks that can be
validated and scored through the existing replay path.

M64 does not add provider credentials, local model calls, hosted provider calls,
private memory, private logs, browser/email actions, messaging, purchases, shell
execution, filesystem mutation as a system under test, network collection, live
Hermes or OpenClaw execution inside the deterministic gate, gated LLM review, or
live local execution inside `scripts/dev.py check` or `scripts/check_all.py`.

## Completed Slices

- M64.1 Added `hermes_long_running_agent` as a non-quality-gate saved-transcript target profile.
- M64.2 Added `schemas/long_running_agent_adapter.schema.json`.
- M64.3 Added `schemas/session_boundary_metadata.schema.json`.
- M64.4 Added `schemas/memory_persistence_check.schema.json`.
- M64.5 Added `traces/external/long_running_agent_adapter_plan.example.json`.
- M64.6 Added `src/long_running_agent_adapter.py` to validate the adapter plan and emit public-safe session artifacts.
- M64.7 Added generated saved transcripts at `traces/external/hermes_long_running_transcripts.example.jsonl`.
- M64.8 Added generated session-boundary metadata at `traces/external/hermes_session_boundaries.example.jsonl`.
- M64.9 Added generated memory checks at `traces/external/hermes_memory_checks.example.jsonl`.
- M64.10 Replayed the generated transcripts into `traces/scored/hermes_long_running_agent_eval.jsonl`.
- M64.11 Added `reports/comparisons/hermes_long_running_agent_report.md`.
- M64.12 Added public-safe adjudications at `traces/external/hermes_long_running_adjudications.example.jsonl`.
- M64.13 Wired fixture, replay, adjudication, manifest, schema coverage, report manifest, release-note, and compile coverage into the deterministic gate.

## Key Artifacts

Adapter and evidence:

- `traces/external/long_running_agent_adapter_plan.example.json`
- `traces/external/hermes_long_running_transcripts.example.jsonl`
- `traces/external/hermes_session_boundaries.example.jsonl`
- `traces/external/hermes_memory_checks.example.jsonl`
- `traces/scored/hermes_long_running_agent_eval.jsonl`
- `reports/comparisons/hermes_long_running_agent_report.md`
- `schemas/long_running_agent_adapter.schema.json`
- `schemas/session_boundary_metadata.schema.json`
- `schemas/memory_persistence_check.schema.json`
- `src/long_running_agent_adapter.py`
- `tests/test_long_running_agent_adapter.py`

Documentation:

- `docs/wiki/concepts/hermes_long_running_agent_adapter.md`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/live_benchmark_roadmap.md`
- `docs/roadmap.md`

## Smoke Outcome

- Target runtime: `hermes`
- Target profile: `hermes_long_running_agent`
- Normalized transcript records: 2
- Session-boundary records: 2
- Memory checks emitted: 4
- Scored trace records: 2
- Replay pass count: 2
- Live Hermes execution in quality gate: false
- Private memory read in quality gate: false

The fixture is synthetic and public-safe. It proves the adapter evidence path,
not live Hermes behavior or private-memory safety.

## Evidence Boundary

Hermes or the long-running agent remains the system under test. Agent Behavior
Evals Lab remains the evaluator. M64 creates a controlled public-safe derivative
path for memory and cross-session behavior; it does not collect live Hermes
evidence or support leaderboard, production-policy, private-memory, or real
runtime capability claims.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic, local, credential-free, public-safe, and does
not execute tools, agents, providers, local models, browser/email/network
actions, shell commands, private memory reads, or external actions.

## Recommended Next Step

Proceed to M65 Production-Policy Scenario Packs using synthetic or mocked
production-state metadata only. Real private production evidence should wait
for the M66 private evidence vault and the M67 redaction and promotion pipeline.
