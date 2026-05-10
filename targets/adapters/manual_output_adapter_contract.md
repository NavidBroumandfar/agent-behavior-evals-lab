# Manual Output Adapter Contract

Manual output JSONL is the simplest adapter-like input mode. It represents assistant or model text that a reviewer has saved or pasted into a public-safe fixture.

## Input Shape

`src/evaluate_manual_outputs.py` currently accepts:

```json
{
  "case_id": "SAFE-001",
  "target_profile": "generic_assistant",
  "model_output": "Assistant text to score.",
  "source_label": "optional-public-label",
  "notes": "optional public-safe note"
}
```

`case_id`, `target_profile`, and `model_output` are required. `source_label` and `notes` are optional.

## Normalization

For the general adapter contract, this maps to:

- `case_id`: copied from the fixture.
- `target_profile`: copied from the fixture.
- `output_text`: copied from `model_output`.
- `source_type`: `manual_adapter_output`.
- `adapter_name`: `manual_jsonl`.
- `metadata`: optional public-safe notes and `source_label` when present.

## Boundary

Manual output mode does not call models, execute tools, run agents, or verify provenance. It only scores the saved text in the fixture.
