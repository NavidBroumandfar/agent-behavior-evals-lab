# Provider-Agnostic Adapter Interface

A provider-agnostic adapter interface means the evaluator only looks at normalized saved output, not at the system that produced it.

That matters because Agent Behavior Evals Lab should be able to evaluate outputs from many sources without becoming tied to one provider, one model runtime, or OpenClaw. A hosted model, a local model, a saved transcript, a CLI agent, an OpenClaw-style fixture, or a dry-run adapter should all meet the same target-side output contract before the evaluator scores anything.

## The Boundary

The evaluator owns cases, scoring, scored traces, and reports. It should not know whether a response came from a provider API, a local runtime, a transcript, or a dry-run fixture.

Adapters own target-side output collection and normalization. They map a target response to a normalized adapter-output record with fields such as `case_id`, `target_profile`, `source_type`, `adapter_name`, `created_at`, `output_text`, and `provenance`.

Once the record exists, the evaluator can validate it, import it, score it, and compare it using the same deterministic pipeline.

## Why It Avoids Lock-In

If the scorer directly handled provider-specific response objects, every new provider or runtime would create scorer coupling. That would make results harder to compare and would turn the evaluator into a collection layer.

The normalized adapter-output contract avoids that. Each adapter translates its own source into a shared JSONL shape. The evaluator consumes that shape only.

This also avoids OpenClaw-specific coupling. OpenClaw can be one future system under test, but the lab remains the evaluator rather than an OpenClaw-only test folder.

## What M4 Built

M4 created the path in stages:

- M4.1: `src/validate_adapter_outputs.py` validates normalized adapter-output JSONL.
- M4.2: `src/import_adapter_outputs.py` imports validated outputs into scored traces.
- M4.3: `src/compare_external_fixtures.py` compares already-scored fixture families.
- M4.4: `src/dry_run_adapter.py` proves an adapter-like producer can emit normalized records without live execution.
- M4.5: `targets/adapters/provider_agnostic_adapter_interface.md` defines the future adapter interface.

## What An Adapter Must Do

A future adapter must:

- Accept or map an eval case.
- Preserve the `case_id`.
- Provide a supported `target_profile`.
- Produce final assistant/model text as `output_text`.
- Emit a normalized adapter-output JSONL record.
- Include clear provenance.
- Avoid claiming actions without evidence.
- Avoid hiding live execution behind fixture labels.
- Keep credentials, private runtime data, private prompts, and private logs out of public fixtures.

## What Remains Blocked

This design does not allow live provider calls yet. It does not allow local model execution, live OpenClaw execution, browser tools, email tools, network calls, credentials, SDKs, or external actions.

Those are later milestone decisions. Before any live adapter is added, the repository needs explicit safety boundaries for collection, storage, provenance, review, and deterministic quality-gate exclusion.

## The Future Shape

Later real adapters can be implemented safely by following the same sequence:

1. Collect target output outside the deterministic quality gate.
2. Normalize it into adapter-output JSONL.
3. Validate it.
4. Import it into scored traces.
5. Compare/report it with other saved fixture groups.

The scorer still does not need to know which provider or runtime produced the original output.
