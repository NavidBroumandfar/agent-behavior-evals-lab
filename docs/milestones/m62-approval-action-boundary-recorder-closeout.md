# Milestone 62 - Approval And Action Boundary Recorder

Date: 2026-06-21

Status: Complete / review-ready

Milestone 62 adds deterministic approval and action-boundary evidence derived
from public-safe tool-call summaries. It can distinguish missing approval,
vague approval, specific approval requests, denied actions, and fake completion
claims without executing any tools or reading raw private logs.

M62 does not add provider credentials, local model calls, hosted provider calls,
private logs, browser/email actions, messaging, purchases, shell execution,
filesystem mutation as a system under test, network collection, live Hermes or
OpenClaw execution, gated LLM review, or live local execution inside
`scripts/dev.py check` or `scripts/check_all.py`.

## Completed Slices

- M62.1 Added `schemas/approval_event.schema.json`.
- M62.2 Added `schemas/action_denial.schema.json`.
- M62.3 Added `traces/external/action_boundary_tool_summaries.example.jsonl`.
- M62.4 Added `src/action_boundary_recorder.py` to convert public-safe tool-call summaries into approval-event and action-denial evidence.
- M62.5 Added generated public-safe evidence outputs: `traces/external/approval_events.example.jsonl` and `traces/external/action_denials.example.jsonl`.
- M62.6 Added unit tests for missing approval, vague approval, denied action, fake completion claims, duplicate summaries, and side-effect rejection.
- M62.7 Wired generation, schema validation, JSONL count checks, and compile coverage into `scripts/check_all.py`.
- M62.8 Updated roadmap, wiki, schema coverage, release-note inputs, and closeout documentation.

## Key Artifacts

Evidence and validation:

- `traces/external/action_boundary_tool_summaries.example.jsonl`
- `traces/external/approval_events.example.jsonl`
- `traces/external/action_denials.example.jsonl`
- `schemas/approval_event.schema.json`
- `schemas/action_denial.schema.json`
- `src/action_boundary_recorder.py`
- `tests/test_action_boundary_recorder.py`

Documentation:

- `docs/wiki/concepts/approval_action_boundary_recorder.md`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/live_benchmark_roadmap.md`
- `docs/roadmap.md`

## Evidence Outcome

- Source tool summaries: 4
- Approval events: 4
- Action denials: 4
- Missing approval examples: 2
- Vague approval examples: 1
- Fake completion claim examples: 1

All committed examples are synthetic public-safe metadata. They exercise the
M62 evidence contract without raw private logs or real external actions.

## Evidence Boundary

The M62 recorder is not a live runtime adapter. It is a deterministic converter
for evidence that a future sandboxed runtime can emit. The generated records
support scoring and reporting of approval behavior without claiming real
tool-agent benchmark results.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic, local, credential-free, public-safe, and does
not execute tools, agents, providers, local models, browser/email/network
actions, shell commands, or external actions.

## Recommended Next Step

Proceed to M63 OpenClaw Live Harness Adapter only as an opt-in adapter that
emits M61/M62-compatible public-safe summaries and keeps raw runtime output
local-only.
