# Milestone 7 - Text-Only Saved Output Collector

Date: 2026-05-23

Status: Complete / tag-ready

Milestone 7 adds the first concrete non-gated saved-output workflow for future adapters. It introduces a target registry, a local raw text-output collector, a review converter that emits normalized adapter-output JSONL, tests for the workflow, and quality-gate validation for the registry.

M7 still does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, file mutation, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M7.1 Target registry for mock profiles and future adapter labels.
- M7.2 Trace/profile schema loosening for registered future labels.
- M7.3 Text-only local raw-output collector.
- M7.4 Reviewed raw-output to normalized adapter-output converter.
- M7.5 Workflow tests for collection, review, and validation.
- M7.6 Quality-gate target registry validation and compile coverage.

## Key Artifacts

Target registry:

- `targets/target_registry.json`
- `schemas/target_registry.schema.json`
- `src/target_registry.py`
- `tests/test_target_registry.py`

Text-only workflow:

- `src/collect_text_only_outputs.py`
- `src/review_text_only_outputs.py`
- `tests/test_text_only_output_workflow.py`
- `docs/wiki/concepts/text_only_saved_output_workflow.md`

Updated contracts:

- `schemas/trace.schema.json`
- `schemas/saved_transcript.schema.json`
- `.gitignore`
- `scripts/check_all.py`

## What The Repo Can Now Do

- Keep deterministic mock profiles in the quality gate while registering future adapter labels.
- Accept registered adapter candidate labels in saved-output and adapter-output paths.
- Collect already-provided text into local raw JSONL.
- Force raw outputs through a review state before normalization.
- Convert approved public-safe raw records into normalized adapter-output JSONL.
- Validate reviewed output with the existing adapter-output validator.

## What Remains Intentionally Blocked

- Calling providers.
- Running local models.
- Running CLI agents.
- Executing tools.
- Browser, email, messaging, purchase, file mutation, shell, or external actions.
- Credentials and secrets.
- Raw output commits.
- Automatic promotion of reviewed candidates into committed fixtures.
- Real adapter execution inside `scripts/check_all.py`.

## Quality Gate

From the repository root:

```bash
python3 scripts/check_all.py
```

The gate validates the target registry and tests the text-only workflow using temporary files. It does not run live collection.

## Recommended Next Milestone

Milestone 8 should make reviewed candidate promotion explicit:

1. Promotion command from `.reviewed.jsonl` to a named committed fixture.
2. Fixture manifest update helper for promoted reviewed outputs.
3. First-class adapter provenance fields in scored traces.
4. Human adjudication notes for scorer false positives and false negatives.
5. Optional previous-vs-current scored trace comparison for arbitrary files.

Keep live tool execution blocked until reviewed text-only output promotion is stable.

## Tag Readiness

After the closeout commit and a clean quality gate, the repository is ready for:

`v0.7.0-text-only-saved-output-collector`
