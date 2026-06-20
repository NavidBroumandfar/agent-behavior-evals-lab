# Milestone 33 - First Real Text-Only Adapter

Date: 2026-06-20

Status: Complete / review-ready

Milestone 33 adds the first controlled text-only adapter path for real target outputs that have already been captured and reviewed as final text.

M33 does not add provider SDKs, live provider calls, local model execution, CLI agent execution, credentials, network collection inside the deterministic gate, browser/email actions, messaging, purchases, file mutation, autonomous actions, or live adapter execution inside `python3 scripts/check_all.py`.

## Completed Slices

- M33.1 Added `src/text_only_adapter.py`, a standard-library controlled adapter that converts reviewer-approved final text into normalized adapter-output JSONL.
- M33.2 Required approved input records to declare public-safe provenance with no live execution, external actions, private data, or credentials.
- M33.3 Validated adapter records against run metadata, known eval cases, registered adapter-output profiles, duplicate case/profile keys, and `.reviewed.jsonl` output naming.
- M33.4 Verified that generated reviewed adapter outputs validate with `src/validate_adapter_outputs.py` and score through `src/import_adapter_outputs.py`.
- M33.5 Added tests for the valid adapter path, unsafe provenance rejection, future-only live provenance rejection, and quality-gate exclusion.
- M33.6 Updated text-only workflow docs, adapter design notes, roadmap, and wiki index.

## Key Artifacts

Code and tests:

- `src/text_only_adapter.py`
- `tests/test_text_only_adapter.py`
- `scripts/check_all.py`

Docs:

- `docs/wiki/concepts/text_only_saved_output_workflow.md`
- `targets/adapters/real_model_adapter_design.md`
- `docs/roadmap.md`
- `docs/wiki/index.md`

## Adapter Boundary

The M33 adapter consumes final text that was produced outside the deterministic quality gate and already reviewed as `approved_public_safe`.

It writes normalized adapter-output JSONL only when:

- The run metadata validates.
- The case IDs match the metadata case selection.
- The target profile matches the metadata target and is adapter-output eligible.
- The input provenance is public-safe.
- The output path ends with `.reviewed.jsonl`.

The adapter does not collect live target output, call providers, run local models, execute agents, mutate files outside its requested output path, or perform external actions.

## Quality-Gate Boundary

The deterministic quality gate compiles `src/text_only_adapter.py` and runs unit tests with temporary files. It does not run the adapter against real targets, import local reviewed candidates into committed traces, or depend on network access, credentials, provider availability, local model availability, or private runtime state.

Reviewed adapter candidates remain ignored by git until a maintainer deliberately promotes a public-safe fixture and updates the fixture manifest.

## Reports And Snapshots

M33 does not change committed scored trace counts or baseline/adjudication aggregates. No report or regression snapshot regeneration is required beyond the normal deterministic gate outputs.

## What Remains Intentionally Blocked

- Live hosted model adapters.
- Local model runtime adapters.
- CLI agent or OpenClaw execution.
- Browser, email, messaging, purchase, form submission, settings changes, file mutation, or other external actions.
- Credentials, private prompts, raw private logs, private workspace paths, and provider account metadata in committed fixtures.
- Adding live adapter execution to `scripts/check_all.py`.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic and local.

## Recommended Next Milestone

Milestone 34 should expand saved transcript replay so real sessions can carry selected-turn IDs, tool-call summaries, approval metadata, denied-action metadata, and public-safe source details without importing private runtime logs.
