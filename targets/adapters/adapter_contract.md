# Adapter Contract

Agent Behavior Evals Lab is the evaluator. Adapters are target-side producers of saved outputs. Their job is to normalize outputs from a system under test so the evaluator can score them without knowing how the output was collected.

M3.4 is contract-only. It does not add real model adapters, credentials, SDKs, network code, browser/email actions, OpenClaw execution, autonomous agents, or private runtime integration.

## Evaluator Responsibilities

The evaluator owns the stable scoring pipeline:

- Load eval cases from `evals/cases/*.jsonl`.
- Apply `src/scorers.py` to normalized target outputs.
- Validate scored traces against `schemas/trace.schema.json`.
- Write scored JSONL through `src/trace_writer.py`.
- Generate deterministic Markdown reports.
- Enforce deterministic quality-gate behavior through `scripts/check_all.py`.

Evaluator logic should not branch on provider, model family, agent runtime, or adapter implementation. If two adapters produce the same normalized output record, the scorer should treat them the same way.

## Adapter Responsibilities

An adapter must provide public-safe target outputs with enough metadata to audit what was scored:

- Provide a supported `target_profile`.
- Map each output to an existing `case_id`.
- Provide the final assistant/model output text to score.
- Provide optional public-safe source metadata such as `source_label`, `adapter_name`, and `transcript_id`.
- Avoid claiming tool execution unless the captured output and trace evidence support that claim.
- Avoid private data leakage in prompts, outputs, metadata, traces, and reports.
- Preserve deterministic ordering and stable identifiers for replayable artifacts.

Adapters may collect or generate outputs in future milestones, but the deterministic quality gate should only score saved outputs.

## Normalized Output Record

Every future adapter should normalize target output to this minimum shape before scoring:

```json
{
  "case_id": "SAFE-001",
  "target_profile": "generic_assistant",
  "output_text": "Assistant text to score.",
  "source_type": "manual_output",
  "source_label": "public-safe-label",
  "adapter_name": "manual_jsonl",
  "transcript_id": "optional-public-id",
  "metadata": {
    "public_safe_only": "optional values"
  }
}
```

Required fields are `case_id`, `target_profile`, `output_text`, `source_type`, `source_label`, and `adapter_name`. `transcript_id` and `metadata` are optional. Metadata must be public-safe, deterministic, and free of secrets, private workspace paths, raw tool logs, browser/email data, or credentials.

The current scored trace schema does not store every normalized adapter field directly. Until that schema is expanded, adapter metadata can be carried in `mock_behavior_notes` or in the input fixture that generated the trace.

## Current Adapter-Like Input Modes

The repository already has adapter-like producers without live execution:

- Deterministic mock model client: `src/model_clients.py` produces controlled baseline outputs.
- Manual output JSONL: `traces/external/manual_outputs.example.jsonl` is scored by `src/evaluate_manual_outputs.py`.
- Sanitized OpenClaw-style manual samples: `traces/external/openclaw_manual_samples.example.jsonl` uses the same manual evaluator.
- Saved transcript replay: `traces/external/saved_transcripts.example.jsonl` is scored by `src/replay_saved_transcripts.py`.

These modes prove the evaluator boundary: target outputs can vary, but scoring and reporting stay stable.

## Future Adapter Categories

Future adapter categories may include:

- Hosted model adapter.
- Local model adapter.
- Controlled CLI agent adapter.
- Controlled OpenClaw CLI adapter.
- Saved external transcript importer.

These are design categories, not active implementations. Any future adapter that performs external actions must be gated in a later milestone and must not become part of the deterministic quality gate.

## Traceability

Adapter outputs become scored traces through a stable flow:

1. Adapter produces or imports public-safe normalized output records.
2. Evaluator verifies `case_id` and `target_profile`.
3. Evaluator passes `output_text` plus case data to the scorer.
4. Evaluator writes scored traces and reports.

The scorer should not know which adapter produced the output. Reports should expose enough source metadata for audit without exposing private data.

## Non-Goals For M3.4

- No live execution.
- No provider credentials.
- No browser, email, purchase, messaging, file-system action, or external side effect.
- No private runtime integration.
- No autonomous agents.
- No background jobs.
- No paid-provider logic or SDK dependencies.
