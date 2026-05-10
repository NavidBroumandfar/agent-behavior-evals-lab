# Normalized Adapter Outputs

Normalized adapter outputs are saved target-side records that contain the final assistant or model text to evaluate. They sit between future adapters and the evaluator: an adapter or importer produces public-safe JSONL records, and a later evaluator step can map those records to cases and score `output_text`.

M4.1 makes this contract executable for saved fixtures only. It adds `schemas/adapter_output.schema.json`, `src/validate_adapter_outputs.py`, and `traces/external/adapter_outputs.example.jsonl`. The validator checks shape and provenance, but it does not import, score, call providers, run local models, execute OpenClaw, or perform external actions.

## Not Scored Traces

Adapter outputs are not scored traces. A normalized adapter-output record has target-side fields such as `record_id`, `case_id`, `target_profile`, `source_type`, `adapter_name`, `created_at`, `output_text`, `provenance`, and optional `metadata`.

A scored trace is evaluator-side output written after scoring. It includes fields such as `run_id`, `category`, `user_prompt`, `expected_behavior`, `passed`, `score`, `failure_modes`, `policy_refs`, and `rationale`. The adapter-output fixture must remain separate from `traces/scored/*.jsonl` so collection and scoring can be reviewed independently.

## Relationship To Existing Artifacts

Eval cases in `evals/cases/*.jsonl` define prompts, expected behavior, policy references, severity, and scoring notes. They do not contain target responses.

Manual outputs in `traces/external/manual_outputs.example.jsonl` are the M3 minimal saved-output format used directly by `src/evaluate_manual_outputs.py`. Normalized adapter outputs are the provider-agnostic target-side format that future importers can consume before scoring.

Saved transcript replay in `traces/external/saved_transcripts.example.jsonl` stores ordered turns and a selected assistant turn index. A normalized adapter output stores the selected final `output_text` directly and can carry public-safe transcript details in `metadata`.

Scored traces in `traces/scored/*.jsonl` are generated evaluator artifacts. They are not adapter inputs and should not be edited to represent raw target output.

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

## Preparing M4.2

M4.1 stops at validation. It proves that normalized adapter-output JSONL records can be checked deterministically before any importer or scorer work happens.

M4.2 can build a fixture importer on top of this contract: load validated records, verify `case_id` and `target_profile` against the local evaluator, convert `output_text` to the scorer response shape, and write scored traces without making the scorer provider-aware.

Run the validator from the repository root:

```bash
python3 src/validate_adapter_outputs.py traces/external/adapter_outputs.example.jsonl
```
