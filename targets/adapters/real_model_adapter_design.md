# Real Model Adapter Design

This document defines how future real model adapters should fit into Agent Behavior Evals Lab. It is a design note only. It does not implement live adapters, provider calls, credentials, SDKs, network code, local model execution, OpenClaw execution, browser/email actions, or background jobs.

## Purpose

Real adapters are future target-side producers of saved outputs. They should collect or import responses from a target model or system, normalize those responses into the adapter contract, and save public-safe artifacts for the evaluator.

The evaluator should not become provider-aware. It continues to load cases, apply the scorer, validate traces, write scored JSONL, generate reports, and enforce deterministic quality gates.

## Adapter Lifecycle

A future real adapter should follow this staged flow:

1. Select eval cases from the repository case files.
2. Construct the target input from each eval case and selected target profile.
3. Call the target model or system outside the deterministic quality gate.
4. Capture the final assistant/model output text.
5. Normalize the captured output into the adapter output record shape.
6. Save public-safe, sanitized outputs as local fixtures.
7. Run the evaluator against saved outputs, not live providers.

This keeps collection separate from scoring. Live collection can be reviewed, retried, or discarded without changing evaluator logic.

## Provider Categories

Future adapter categories may include:

- Hosted model APIs.
- Local model runtimes.
- Controlled CLI agents.
- Controlled OpenClaw CLI adapter, future only.
- Saved transcript importers.

These categories describe possible target systems. They are not active integrations in this milestone.

## Normalized Output Shape

Adapters should reuse the normalized adapter-output contract before scoring. M4.1 makes the saved-fixture subset executable through `schemas/adapter_output.schema.json`:

```json
{
  "record_id": "ADAPTER-OUTPUT-SAFE-001",
  "case_id": "SAFE-001",
  "target_profile": "generic_assistant",
  "source_type": "saved_adapter_output",
  "adapter_name": "example_adapter",
  "adapter_version": "0.1.0-example",
  "created_at": "2026-05-10T00:00:00Z",
  "output_text": "Assistant text to score.",
  "provenance": {
    "public_safe": true,
    "live_execution": false,
    "external_actions": false,
    "contains_private_data": false
  },
  "metadata": {
    "source_label": "public-safe-run-label"
  }
}
```

Required fields are `record_id`, `case_id`, `target_profile`, `source_type`, `adapter_name`, `created_at`, `output_text`, and `provenance`. `adapter_version` and `metadata` are optional. Metadata must be public-safe only.

The M4.1 fixture validator accepts only saved, non-live source types such as `saved_adapter_output`, `manual_adapter_output`, `saved_transcript_output`, and `dry_run_adapter_output`. Future live collection categories, such as hosted model APIs or controlled CLI agents, require a later milestone before they can expand the contract.

## Deterministic Quality Gate Boundary

Live provider calls must not run inside `python3 scripts/check_all.py`.

The quality gate should validate saved fixtures, generated scored traces, generated reports, schemas, and local deterministic scripts. It must not depend on network access, provider uptime, credentials, paid services, local model availability, or external system state.

If a live adapter later produces outputs, those outputs should be saved and reviewed first. The deterministic gate can then score the saved fixture.

## Safety And Privacy Rules

Future adapters must follow these rules:

- Use no private data by default.
- Sanitize outputs before committing fixtures.
- Never commit API keys, tokens, credentials, secrets, or provider account details.
- Do not claim tool execution unless captured evidence supports the claim.
- Do not perform browser, email, messaging, purchasing, file mutation, or other external actions in early adapter milestones.
- Require explicit approval before any adapter can perform external actions in a later milestone.
- Keep private prompts, private memory, raw runtime artifacts, and private workspace state out of this repository.

## Failure Modes To Watch

Real adapters should preserve enough source context to diagnose common evaluator failures:

- `hallucinated_tool_use`: output claims inspection, tool use, browsing, execution, or external action without evidence.
- `fake_completion_claim`: output claims a task was completed when only text was generated or captured.
- `unsupported_claim`: output asserts facts or authority not supported by the prompt or saved evidence.
- `missing_approval_gate`: output proceeds with consequential action without explicit approval.
- `unsafe_compliance`: output assists harmful, deceptive, unauthorized, or privacy-invasive requests.
- `over_refusal`: output refuses or blocks safe direct-response tasks unnecessarily.
- Provider-specific formatting artifacts: output includes wrappers, role labels, boilerplate, or hidden-control text that should not be scored as final answer content.
- Nondeterministic run drift: repeated live collection changes outputs enough to affect scores.

## Future Implementation Sequence

Keep implementation staged:

1. Design doc only.
2. Provider-agnostic adapter interface.
3. Dry-run fixture generator. M4.4 adds `src/dry_run_adapter.py` as the deterministic no-network contract test for this stage.
4. One local/offline toy adapter or saved-output importer.
5. Hosted provider adapter outside the quality gate.
6. Controlled OpenClaw CLI adapter much later.

Each stage should keep scoring independent from adapter implementation details.

## Non-Goals

- No live implementation now.
- No credentials.
- No paid API calls.
- No autonomous agents.
- No background jobs.
- No private OpenClaw runtime integration.
- No browser, email, messaging, purchasing, or external actions.
