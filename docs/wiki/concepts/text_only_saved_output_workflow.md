# Text-Only Saved Output Workflow

The M7 text-only saved output workflow is the first implementation step toward real adapter experiments. It still does not call providers, run local models, execute agents, use credentials, or perform external actions.

## Workflow

1. Register the target label in `targets/target_registry.json`.
2. Plan the run with adapter run metadata.
3. Collect already-provided final assistant text into local raw JSONL with `src/collect_text_only_outputs.py`.
4. Human-review the local raw output and mark approved public-safe records.
5. Convert approved records to normalized adapter-output JSONL with `src/review_text_only_outputs.py`.
6. Validate/import/score the reviewed output with the existing adapter-output path when it is ready to become an explicit fixture.

## Local Raw Records

Raw records are local-only and must use filenames ending in `.local.jsonl`. The collector writes `review_status: pending_review` and `provenance.public_safe: false` by default. This forces a review step before anything can become normalized adapter output.

Raw records are ignored by git through `.gitignore`.

## Reviewed Candidates

The review converter only accepts records marked `approved_public_safe` with public-safe provenance. It writes normalized adapter-output records ending in `.reviewed.jsonl`.

Reviewed candidates are also ignored by git until a maintainer deliberately promotes them into committed fixtures and updates the fixture manifest.

## Why This Is Not Live Execution

The workflow handles saved text. It does not know how that text was produced. That means it can support future hosted model, local model, or agent outputs without coupling the evaluator to runtime execution.

The deterministic quality gate validates the workflow code and target registry, but it does not run live collection.
