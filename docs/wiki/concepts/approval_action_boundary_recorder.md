# Approval And Action Boundary Recorder

The approval and action boundary recorder is the M62 evidence layer for
tool-capable agent behavior. It converts public-safe tool-call summaries into
two normalized evidence streams:

- approval events, which show whether approval was missing, vague, or specific;
- action denials, which show whether a consequential action was blocked before
  execution and whether the assistant claimed completion anyway.

The recorder is deterministic and local. It reads committed public-safe
metadata only and does not run agents, execute tools, inspect private runtime
logs, use credentials, call networks, mutate files, or perform external
actions.

## Artifacts

- Source summaries: `traces/external/action_boundary_tool_summaries.example.jsonl`
- Approval events: `traces/external/approval_events.example.jsonl`
- Action denials: `traces/external/action_denials.example.jsonl`
- Approval-event schema: `schemas/approval_event.schema.json`
- Action-denial schema: `schemas/action_denial.schema.json`
- Converter: `src/action_boundary_recorder.py`
- Tests: `tests/test_action_boundary_recorder.py`

## Evidence Labels

The converter records labels that reports and future scoring layers can use
without raw logs:

- `missing_approval`
- `vague_approval`
- `specific_approval_request`
- `denied_action`
- `fake_completion_claim`

The committed examples intentionally cover all four M62 review cases: missing
approval, vague approval, denied action, and fake completion claims.

## Boundary

M62 evidence is not proof that a live runtime behaved safely. It is a
public-safe contract and conversion layer for future tool-capable benchmarks.
Live runtime adapters remain future, opt-in work and must continue to emit
public-safe summaries before evidence can enter committed fixtures.
