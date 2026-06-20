# Text-Only Saved Output Workflow

The M7 text-only saved output workflow is the first implementation step toward real adapter experiments. It still does not call providers, run local models, execute agents, use credentials, or perform external actions.

## Workflow

1. Register the target label in `targets/target_registry.json`.
2. Plan the run with adapter run metadata.
3. Collect already-provided final assistant text into local raw JSONL with `src/collect_text_only_outputs.py`.
4. Human-review the local raw output and mark approved public-safe records.
5. Convert approved records to normalized adapter-output JSONL with `src/review_text_only_outputs.py`.
6. Validate/import/score the reviewed output with the existing adapter-output path when it is ready to become an explicit fixture.

## M33 Controlled Text-Only Adapter

M33 adds `src/text_only_adapter.py` for the first controlled text-only adapter path. It accepts final text that was produced outside the deterministic quality gate and already reviewed as `approved_public_safe`, then writes normalized adapter-output JSONL.

The adapter input is reviewer-approved final text, not raw private collection. Each input record must include:

- `case_id`
- `target_profile`
- `output_text`
- `review_status: approved_public_safe`
- public-safe provenance with `live_execution`, `external_actions`, `contains_private_data`, and `credentials_required` all false

The output must end with `.reviewed.jsonl`, validates through `src/validate_adapter_outputs.py`, and can be scored with `src/import_adapter_outputs.py`.

Example local flow:

```bash
python3 src/text_only_adapter.py \
  --metadata traces/external/adapter_run_metadata.example.json \
  --input traces/raw/example_reviewed_text.local.jsonl \
  --output traces/external/example_text_only_adapter.reviewed.jsonl

python3 src/import_adapter_outputs.py \
  traces/external/example_text_only_adapter.reviewed.jsonl \
  traces/scored/example_text_only_adapter.local.jsonl
```

The example paths use ignored local/reviewed filenames. A reviewed adapter output should only become a committed fixture after a deliberate promotion decision and manifest update.

## Local Raw Records

Raw records are local-only and must use filenames ending in `.local.jsonl`. The collector writes `review_status: pending_review` and `provenance.public_safe: false` by default. This forces a review step before anything can become normalized adapter output.

Raw records are ignored by git through `.gitignore`.

## Reviewed Candidates

The review converter only accepts records marked `approved_public_safe` with public-safe provenance. It writes normalized adapter-output records ending in `.reviewed.jsonl`.

Reviewed candidates are also ignored by git until a maintainer deliberately promotes them into committed fixtures and updates the fixture manifest.

## Why This Is Not Live Execution

The workflow handles saved text. It does not know how that text was produced. That means it can support future hosted model, local model, or agent outputs without coupling the evaluator to runtime execution.

The deterministic quality gate validates the workflow code and target registry, but it does not run live collection.

M33 keeps that boundary: `scripts/check_all.py` compiles `src/text_only_adapter.py` and tests the adapter with temporary files, but it does not execute real target collection or import local reviewed candidates into committed traces.
