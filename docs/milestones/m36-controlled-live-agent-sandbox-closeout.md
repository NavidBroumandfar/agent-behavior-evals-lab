# Milestone 36 - Controlled Live Agent Sandbox

Date: 2026-06-20

Status: Complete / review-ready

Milestone 36 adds a tiny controlled local agent sandbox path for a future live-agent workflow without adding live provider execution, local model execution, live OpenClaw or Hermes execution, credentials, network collection, browser/email actions, messaging, purchases, file mutation, shell execution, autonomous actions, private runtime-log ingestion, or sandbox execution inside the deterministic quality gate.

## Completed Slices

- M36.1 Added `src/controlled_live_agent_sandbox.py`, a metadata-driven local no-tool sandbox runner.
- M36.2 Added `traces/external/controlled_live_agent_sandbox_metadata.example.json` for the M36 pilot plan.
- M36.3 Selected a tiny case subset: `APPROVAL-014`, `REFUSAL-007`, and `UNCERTAINTY-008`.
- M36.4 Required ignored raw output paths ending in `.local.jsonl`, with repo-local output constrained to `traces/raw/`.
- M36.5 Added guardrails that reject metadata allowing manual network collection, credentials, external actions, quality-gate live runs, or unblocked tool execution.
- M36.6 Added unit tests for metadata validation, raw-output generation to temporary paths, output-path enforcement, and sandbox guardrail failures.
- M36.7 Wired quality-gate metadata validation and `py_compile` coverage without running the sandbox command in the gate.
- M36.8 Updated roadmap, wiki docs, schema coverage reference, and adapter sandbox documentation.

## Key Artifacts

Code and tests:

- `src/controlled_live_agent_sandbox.py`
- `tests/test_controlled_live_agent_sandbox.py`
- `scripts/check_all.py`

Metadata and docs:

- `traces/external/controlled_live_agent_sandbox_metadata.example.json`
- `targets/adapters/controlled_adapter_sandbox.md`
- `targets/adapters/future_adapter_types.md`
- `docs/wiki/concepts/controlled_adapter_sandbox.md`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/roadmap.md`
- `docs/wiki/index.md`

## Pilot Scope

The committed M36 metadata describes one local no-tool sandbox runtime label, one profile, and three existing cases:

- Runtime label: `local_no_tool_agent_sandbox`
- Profile: `openclaw_reference_agent`
- Cases: `APPROVAL-014`, `REFUSAL-007`, `UNCERTAINTY-008`

The manual command is:

```bash
python3 src/controlled_live_agent_sandbox.py
```

By default it writes `traces/raw/m36_controlled_live_agent_sandbox.local.jsonl`. That path is ignored and is not a committed fixture, scored trace, report input, or benchmark artifact.

## Boundary

M36 validates and tests the sandbox controls, not a live runtime result.

The deterministic quality gate:

- Validates the M36 committed metadata plan.
- Runs unit tests for local guardrails using temporary output paths.
- Compiles the sandbox runner.

The deterministic quality gate does not:

- Run the default sandbox command.
- Commit raw sandbox output.
- Import, score, or report M36 raw output.
- Execute providers, models, OpenClaw, Hermes, CLI agents, tools, shell commands, browser/email actions, or external actions.

## What Remains Intentionally Blocked

- Live Hermes, OpenClaw, hosted-model, local-model, or CLI-agent execution.
- Deep harness integration.
- Any raw private transcript, log, prompt, memory, workspace path, credential, secret, or account identifier.
- Browser, email, messaging, purchase, deployment, file mutation, shell execution, or other external actions.
- Treating M36 as benchmark evidence for a real runtime.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

Milestone 37 should consider optional harness integration only if saved transcripts, reviewed saved outputs, and the M36 local sandbox controls are insufficient. Any real harness bridge should remain non-gated first, use disposable workspaces, and keep external actions blocked unless a later milestone explicitly governs them.
