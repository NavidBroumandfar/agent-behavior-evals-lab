# Saved Transcript Replay

Saved transcript replay scores static assistant turns from public-safe transcript fixtures. It is a replay format, not a live model or agent run.

## Fixture Shape

Each JSONL record in `traces/external/saved_transcripts.example.jsonl` includes:

- `transcript_id`: stable fixture identifier.
- `case_id`: existing eval case to score against.
- `target_profile`: existing target profile label.
- `turns`: ordered transcript turns, each with `role` and `content`.
- `assistant_turn_index`: zero-based index of the assistant turn to score.
- `source_label` and `notes`: optional public-safe metadata.

The selected turn must exist and must have role `assistant`.

## Replay Flow

`src/replay_saved_transcripts.py` loads the transcript fixture, validates the shape, checks that each `case_id` and `target_profile` is known, extracts the selected assistant turn, scores it with `src/scorers.py`, writes scored traces, and generates a deterministic Markdown report.

M24 routes transcript record shape validation through `schemas/saved_transcript.schema.json` and `src/schema_validation_utils.py`. Replay-specific checks for duplicate transcript IDs, case/profile references, assistant-turn index bounds, and selected assistant role remain in `src/replay_saved_transcripts.py`.

The scored trace uses the same schema as the mock and manual-output paths. Transcript metadata is carried in `mock_behavior_notes` until a future trace schema adds dedicated replay fields.

## Boundaries

Replay does not call APIs, run OpenClaw, use live adapters, browse, send email, execute tools, or read private runtime data. The transcript fixture is fictional and public-safe.

## Outputs

- Input fixture: `traces/external/saved_transcripts.example.jsonl`
- Scored trace: `traces/scored/saved_transcript_replay_eval.jsonl`
- Report: `reports/comparisons/saved_transcript_replay_report.md`
- Optional schema document: `schemas/saved_transcript.schema.json`

## Next Step

Use this replay format to refine the future adapter contract: stable turn IDs, explicit selected assistant turns, source labels, approval state, and public-safe tool summaries can be added without changing the scorer boundary.
