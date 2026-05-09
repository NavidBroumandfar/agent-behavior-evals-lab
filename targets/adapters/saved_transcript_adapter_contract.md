# Saved Transcript Adapter Contract

Saved transcript replay is an adapter-like input mode for scoring one selected assistant turn from each static transcript record.

## Input Shape

`src/replay_saved_transcripts.py` currently accepts:

```json
{
  "transcript_id": "TRANSCRIPT-SAFE-001",
  "case_id": "SAFE-001",
  "target_profile": "generic_assistant",
  "turns": [
    {
      "role": "user",
      "content": "User prompt."
    },
    {
      "role": "assistant",
      "content": "Assistant text to score."
    }
  ],
  "assistant_turn_index": 1,
  "source_label": "optional-public-label",
  "notes": "optional public-safe note"
}
```

`transcript_id`, `case_id`, `target_profile`, `turns`, and `assistant_turn_index` are required. The selected turn must exist and must have role `assistant`.

## Normalization

For the general adapter contract, this maps to:

- `case_id`: copied from the transcript record.
- `target_profile`: copied from the transcript record.
- `output_text`: copied from `turns[assistant_turn_index].content`.
- `source_type`: `saved_transcript`.
- `source_label`: copied when present.
- `adapter_name`: `saved_transcript_replay`.
- `transcript_id`: copied from the transcript record.
- `metadata`: optional public-safe replay details, such as `assistant_turn_index`.

## Boundary

Saved transcript replay does not rerun the original system, execute transcript actions, inspect private logs, or infer hidden state. It only scores the selected saved assistant turn.
