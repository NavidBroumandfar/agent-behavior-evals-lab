# Normalized Adapter Outputs

Normalized adapter outputs are saved target-side records that contain the final assistant or model text to evaluate. They sit between future adapters and the evaluator: an adapter or importer produces public-safe JSONL records, and a later evaluator step can map those records to cases and score `output_text`.

M4.1 makes this contract executable for saved fixtures only. It adds `schemas/adapter_output.schema.json`, `src/validate_adapter_outputs.py`, and `traces/external/adapter_outputs.example.jsonl`. The validator checks shape and provenance, but it does not import, score, call providers, run local models, execute OpenClaw, or perform external actions.

M4.2 adds `src/import_adapter_outputs.py`. The importer validates the same saved fixture first, loads existing eval cases, connects each `case_id` to evaluator expectations, scores `output_text` with the existing scorer, and writes deterministic scored traces to `traces/scored/adapter_output_fixture_import.jsonl`.

## Not Scored Traces

Adapter outputs are not scored traces. A normalized adapter-output record has target-side fields such as `record_id`, `case_id`, `target_profile`, `source_type`, `adapter_name`, `created_at`, `output_text`, `provenance`, and optional `metadata`.

A scored trace is evaluator-side output written after scoring. It includes fields such as `run_id`, `category`, `user_prompt`, `expected_behavior`, `passed`, `score`, `failure_modes`, `policy_refs`, and `rationale`. The adapter-output fixture must remain separate from `traces/scored/*.jsonl` so collection and scoring can be reviewed independently.

## Relationship To Existing Artifacts

Eval cases in `evals/cases/*.jsonl` define prompts, expected behavior, policy references, severity, and scoring notes. They do not contain target responses.

Manual outputs in `traces/external/manual_outputs.example.jsonl` are the M3 minimal saved-output format used directly by `src/evaluate_manual_outputs.py`. Normalized adapter outputs are the provider-agnostic target-side format that future importers can consume before scoring.

Saved transcript replay in `traces/external/saved_transcripts.example.jsonl` stores ordered turns and a selected assistant turn index. A normalized adapter output stores the selected final `output_text` directly and can carry public-safe transcript details in `metadata`.

Scored traces in `traces/scored/*.jsonl` are generated evaluator artifacts. They are not adapter inputs and should not be edited to represent raw target output. An adapter output becomes a scored trace only after import, case lookup, scoring, and trace-schema validation.

## Validation Vs Import

Validation answers: "Is this saved target-side record shaped correctly and public-safe enough for M4.1?" It checks required fields, string types, allowed `source_type`, fixed UTC timestamp shape, non-empty `output_text`, and provenance booleans. It writes nothing.

Import answers: "Can this validated saved output be evaluated against the existing cases?" It loads the same JSONL fixture, requires every `case_id` to exist in `evals/cases/*.jsonl`, requires `target_profile` to fit the current trace schema, converts `output_text` into the scorer response shape, and writes scored trace records.

`case_id` is the join key. It connects saved target output to the evaluator-owned prompt, category, expected behavior, policy references, severity, expected failure modes, and scoring notes. Without that case lookup, the output text is just saved text, not an evaluation result.

## Source Types

M4.1 allows these saved, public-safe source types:

- `saved_adapter_output`: a saved target output produced elsewhere and reviewed before entering the fixture.
- `manual_adapter_output`: a reviewer-prepared normalized record.
- `saved_transcript_output`: final assistant text selected from a static transcript.
- `dry_run_adapter_output`: output from a dry-run or fixture-only adapter path that did not execute a target system.

These values describe saved records, not provider families. They intentionally do not assume OpenAI, Anthropic, OpenClaw, local model runtimes, or any other target.

## Provenance Fields

Each record must include `provenance` with four booleans:

- `public_safe`: must be `true`; the record is suitable for the public repository.
- `live_execution`: must be `false` in M4.1; the fixture cannot be evidence from a live provider or agent run.
- `external_actions`: must be `false` in M4.1; the fixture cannot perform or depend on browser, email, messaging, purchase, file mutation, or other external side effects.
- `contains_private_data`: must be `false`; prompts, outputs, metadata, credentials, private paths, and runtime logs must not be included.

The validator enforces these values for M4.1 fixtures. Later milestones can introduce explicit gates if live collection or richer provenance becomes necessary, but that is outside this milestone.

## Importer Command

Run validation from the repository root:

```bash
python3 src/validate_adapter_outputs.py traces/external/adapter_outputs.example.jsonl
```

Run import from the repository root:

```bash
python3 src/import_adapter_outputs.py traces/external/adapter_outputs.example.jsonl
```

The import command writes `traces/scored/adapter_output_fixture_import.jsonl` with fixed `run_id` `m4_adapter_output_fixture_import` and fixed timestamp `2026-05-10T00:00:00Z`.

This still does not mean live model, provider, local model, or OpenClaw integration. The importer consumes saved public-safe records only. It does not create a real adapter, call APIs, run local models, execute OpenClaw, use browser/email/external tools, or read private runtime state.

## Preparing M4.3

M4.2 produces the first deterministic scored trace from normalized adapter-output fixtures. M4.3 can compare that scored fixture with other external fixture runs, reports, or summaries without changing the scorer and without making the evaluator provider-aware.
