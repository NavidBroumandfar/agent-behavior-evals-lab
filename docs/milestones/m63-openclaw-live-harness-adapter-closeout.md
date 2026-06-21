# Milestone 63 - OpenClaw Live Harness Adapter

Date: 2026-06-21

Status: Complete / public-safe smoke review-ready

Milestone 63 adds a schema-backed OpenClaw harness adapter boundary. The
committed adapter is a deterministic public-safe smoke fixture generator, not a
live OpenClaw launcher. It emits normalized saved-transcript evidence and
tool-boundary summaries that can be scored through the existing replay path.

M63 does not add provider credentials, local model calls, hosted provider calls,
private logs, browser/email actions, messaging, purchases, shell execution,
filesystem mutation as a system under test, network collection, live Hermes or
OpenClaw execution inside the deterministic gate, gated LLM review, or live
local execution inside `scripts/dev.py check` or `scripts/check_all.py`.

## Completed Slices

- M63.1 Added `schemas/openclaw_harness_adapter.schema.json`.
- M63.2 Added `traces/external/openclaw_harness_adapter_plan.example.json`.
- M63.3 Added `src/openclaw_harness_adapter.py` to validate the adapter plan and emit public-safe smoke artifacts.
- M63.4 Added generated normalized transcript evidence at `traces/external/openclaw_harness_smoke_transcript.example.jsonl`.
- M63.5 Added generated tool-boundary summary evidence at `traces/external/openclaw_harness_tool_summaries.example.jsonl`.
- M63.6 Replayed the generated transcript into `traces/scored/openclaw_harness_smoke_eval.jsonl`.
- M63.7 Added `reports/comparisons/openclaw_harness_smoke_report.md`.
- M63.8 Added tests for opt-in controls, quality-gate exclusion, raw-output locality, target/evaluator labeling, case selection, and tool-summary provenance.
- M63.9 Wired generation, replay, report verification, schema coverage, report manifest coverage, and compile coverage into `scripts/check_all.py`.
- M63.10 Updated roadmap, wiki, schema coverage, release-note inputs, and closeout documentation.

## Key Artifacts

Adapter and evidence:

- `traces/external/openclaw_harness_adapter_plan.example.json`
- `traces/external/openclaw_harness_smoke_transcript.example.jsonl`
- `traces/external/openclaw_harness_tool_summaries.example.jsonl`
- `traces/scored/openclaw_harness_smoke_eval.jsonl`
- `reports/comparisons/openclaw_harness_smoke_report.md`
- `schemas/openclaw_harness_adapter.schema.json`
- `src/openclaw_harness_adapter.py`
- `tests/test_openclaw_harness_adapter.py`

Documentation:

- `docs/wiki/concepts/openclaw_live_harness_adapter.md`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/live_benchmark_roadmap.md`
- `docs/roadmap.md`

## Smoke Outcome

- Target runtime: `openclaw`
- Target profile: `openclaw_reference_agent`
- Normalized transcript records: 1
- Tool summaries emitted: 1
- Scored trace records: 1
- Smoke replay pass count: 1
- Live OpenClaw execution in quality gate: false

The smoke fixture is synthetic and public-safe. It proves the adapter evidence
path, not live OpenClaw behavior.

## Evidence Boundary

OpenClaw remains the system under test. Agent Behavior Evals Lab remains the
evaluator. M63 creates a controlled adapter boundary and public-safe smoke
artifact; it does not collect live OpenClaw evidence or support leaderboard,
production-policy, or real tool-capability claims.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic, local, credential-free, public-safe, and does
not execute tools, agents, providers, local models, browser/email/network
actions, shell commands, or external actions.

## Recommended Next Step

Proceed to M64 Hermes Or Long-Running Agent Adapter with the same evidence
boundary: public-safe fixtures and metadata in the deterministic gate, with any
live or private runtime collection opt-in and local-only.
