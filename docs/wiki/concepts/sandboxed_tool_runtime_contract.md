# Sandboxed Tool Runtime Contract

The sandboxed tool runtime contract is the M61 boundary for future
tool-capable agent benchmarks. It defines how a runtime may describe attempted
tool use without allowing the deterministic evaluator to execute tools or touch
external systems.

The contract is intentionally default-deny. Filesystem, shell, browser, email,
network, and external-action surfaces all start blocked. The committed contract
allows only public-safe metadata summaries of attempted actions, blocked
actions, approval requests, and simulated no-op events.

## Artifacts

- Contract: `traces/external/tool_sandbox_contract.example.json`
- Contract schema: `schemas/tool_sandbox_contract.schema.json`
- Tool-call summary schema: `schemas/tool_call_summary.schema.json`
- Public-safe summary examples: `traces/external/tool_call_summaries.example.jsonl`
- Validator: `src/validate_tool_sandbox_contract.py`
- Tests: `tests/test_tool_sandbox_contract.py`

## Default Sandbox Rules

- Unknown tools are denied.
- Real actions are not allowed by default.
- Approval requests may be recorded, but approval does not grant execution in
  the default sandbox.
- Raw private logs are not captured in committed summaries.
- Disposable workspaces are required for future opt-in runtime pilots and must
  stay outside the repository.
- Public-safe summaries may be scored without raw private logs.

## Evidence Boundary

M61 does not run OpenClaw, Hermes, CLI agents, local models, providers, browser
tools, email tools, shell commands, network collectors, filesystem tools, or
external actions. The deterministic gate validates only schemas, committed
contract metadata, fake public-safe summary records, and default-deny safety
semantics.

Future milestones can build recorders or runtime adapters on this contract, but
they must keep live runtime execution opt-in and outside `python3 scripts/dev.py
check` unless a later roadmap explicitly changes that boundary.
