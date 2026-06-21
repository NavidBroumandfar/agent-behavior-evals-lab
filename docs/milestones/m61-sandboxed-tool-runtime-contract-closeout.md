# Milestone 61 - Sandboxed Tool Runtime Contract

Date: 2026-06-21

Status: Complete / review-ready

Milestone 61 defines the default sandbox contract for future tool-capable agent
runtime benchmarks. The contract is metadata-only and default-deny: it can
represent attempted actions, blocked actions, approval requests, and public-safe
tool summaries without allowing the deterministic quality gate to execute tools
or touch external systems.

M61 does not add provider credentials, local model calls, hosted provider calls,
private logs, browser/email actions, messaging, purchases, shell execution,
filesystem mutation as a system under test, network collection, live Hermes or
OpenClaw execution, gated LLM review, or live local execution inside
`scripts/dev.py check` or `scripts/check_all.py`.

## Completed Slices

- M61.1 Added `schemas/tool_sandbox_contract.schema.json`.
- M61.2 Added `schemas/tool_call_summary.schema.json`.
- M61.3 Added `traces/external/tool_sandbox_contract.example.json`.
- M61.4 Added `traces/external/tool_call_summaries.example.jsonl`.
- M61.5 Added `src/validate_tool_sandbox_contract.py` to enforce default-deny tool surfaces, disposable workspace policy, quality-gate exclusions, and public-safe summary semantics.
- M61.6 Added unit tests for missing surfaces, forbidden execution, raw-log capture, approval execution, blocked capabilities, side effects, contract ID mismatches, and approval-request semantics.
- M61.7 Wired validation and compile coverage into `scripts/check_all.py`.
- M61.8 Updated roadmap, wiki, schema coverage, and release-note inputs.

## Key Artifacts

Contract and validation:

- `traces/external/tool_sandbox_contract.example.json`
- `traces/external/tool_call_summaries.example.jsonl`
- `schemas/tool_sandbox_contract.schema.json`
- `schemas/tool_call_summary.schema.json`
- `src/validate_tool_sandbox_contract.py`
- `tests/test_tool_sandbox_contract.py`

Documentation:

- `docs/wiki/concepts/sandboxed_tool_runtime_contract.md`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/live_benchmark_roadmap.md`
- `docs/roadmap.md`

## Contract Outcome

- Sandbox mode: `default_deny_metadata_only`
- Tool surfaces covered: filesystem, shell, browser, email, network, external action
- Runtime execution in quality gate: false
- Tool execution in quality gate: false
- Raw private log validation in quality gate: false
- Public-safe summary records: 3

The summary examples are synthetic and public-safe. They prove the contract can
record blocked actions and approval requests without executing tools or
publishing raw private logs.

## Evidence Boundary

The M61 contract is not a live runtime harness and does not support capability
claims about real tool-using agents. It is a validated boundary for later
milestones to use when they add approval recorders, action-denial recorders, or
opt-in runtime adapters.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic, local, credential-free, public-safe, and does
not execute tools or local models.

## Recommended Next Step

Proceed to M62 Approval And Action Boundary Recorder by deriving approval-event
and action-denial records from the M61 public-safe tool-call summary contract.
