# Milestone 5 — Adapter Interface Test Harness & Provenance Extensions

Date: 2026-05-10

Status: Complete / tag-ready

Milestone 5 hardened the adapter-output contract and fixture audit layer without adding live execution. The repository now has executable conformance checks for normalized adapter outputs, public-safe provenance extensions, a fixture source manifest, and manifest validation tests that keep saved-output sources, scored traces, and reports aligned.

M5 keeps the evaluator boundary deterministic. It strengthens how saved adapter-like outputs are reviewed before scoring, but it does not add live providers, local model execution, OpenClaw execution, browser/email actions, credentials, real adapters, or scoring changes.

## Completed Slices

- M5.1 Adapter Interface Conformance Tests
- M5.2 Adapter Output Provenance Extensions
- M5.3 Adapter Fixture Manifest & Source Index
- M5.4 Fixture Manifest Validation Tests

## Key Artifacts

Tests:

- `tests/test_adapter_output_conformance.py`
- `tests/test_fixture_manifest_validation.py`

Validators and import path:

- `src/validate_adapter_outputs.py`
- `src/import_adapter_outputs.py`
- `src/validate_fixture_manifest.py`
- `src/dry_run_adapter.py`
- `src/compare_external_fixtures.py`

Schema, manifest, and fixtures:

- `schemas/adapter_output.schema.json`
- `traces/external/fixture_manifest.json`
- `traces/external/adapter_outputs.example.jsonl`
- `traces/external/dry_run_adapter_outputs.jsonl`
- `traces/external/manual_outputs.example.jsonl`
- `traces/external/openclaw_manual_samples.example.jsonl`
- `traces/external/saved_transcripts.example.jsonl`

Generated scored traces and reports:

- `traces/scored/adapter_output_fixture_import.jsonl`
- `traces/scored/dry_run_adapter_output_import.jsonl`
- `traces/scored/manual_output_eval.jsonl`
- `traces/scored/openclaw_manual_eval.jsonl`
- `traces/scored/saved_transcript_replay_eval.jsonl`
- `reports/comparisons/external_fixture_comparison_report.md`

Documentation:

- `docs/wiki/concepts/adapter_interface_conformance_tests.md`
- `docs/wiki/concepts/adapter_output_provenance.md`
- `docs/wiki/concepts/fixture_manifest.md`
- `docs/wiki/concepts/fixture_manifest_validation_tests.md`
- `docs/milestones/m5-adapter-contract-hardening-closeout.md`

Quality-gate integration:

- `scripts/check_all.py`

## What The Repo Can Now Do

- Validate adapter outputs.
- Reject malformed or unsafe adapter-output records before import or scoring.
- Preserve public-safe provenance details for saved adapter-output records.
- Validate dry-run and saved-output fixture records.
- Index fixture sources through a manifest.
- Validate the manifest itself.
- Detect broken fixture, report, and scored-trace references.
- Keep deterministic quality-gate behavior.

## What Remains Intentionally Blocked

- Live provider APIs.
- Local model execution.
- Live OpenClaw execution.
- Browser, email, messaging, purchase, file mutation, or other external actions.
- Credentials and secrets.
- Private runtime integration.
- Autonomous external actions.
- Real adapter execution inside the deterministic quality gate.

These remain blocked because M5 is contract hardening, not target execution. Live collection still needs separate sandboxing, approval, storage, provenance, and non-gated artifact policies before it can be reviewed responsibly.

## Quality Gate

From the repository root:

```bash
python3 scripts/check_all.py
```

The quality gate runs local unit tests, schema validation, adapter-output validation and import, dry-run adapter generation, dry-run validation and import, mock eval generation, baseline and comparison reports, regression checking, failure inspection, manual output evaluation, OpenClaw-style manual fixture evaluation, saved transcript replay, external fixture comparison, fixture manifest validation, trace/report existence checks, JSONL count checks, and `py_compile`.

It should leave deterministic generated artifacts stable. The gate does not call live providers, execute OpenClaw, run local models, use browser/email tools, perform external actions, use credentials, or reach private runtime state.

## Portfolio Interpretation

M5 matters for LLM and agent evaluation credibility because it turns adapter-readiness claims into enforceable contracts. Future adapter-like outputs must pass shape checks, negative tests, public-safe provenance requirements, and case linkage before they can become scored traces.

The fixture manifest adds auditability around source integrity: readers can trace each controlled fixture family to its source file, owning script, generated scored trace, report coverage, quality-gate status, safety assertions, and limitations. That makes the evaluator easier to review because provenance, fixture ownership, and deterministic boundaries are explicit instead of implied.

M5 also protects the evaluator from benchmark inflation. Saved fixtures remain saved fixtures, the dry-run adapter remains a no-network contract producer, and the quality gate remains deterministic instead of quietly executing real systems.

## Limitations

- Saved fixtures are not live benchmarks.
- Dry-run adapter output is not real model adapter output.
- The manifest is an audit index, not an evaluation engine.
- The fixture set is small and curated for evaluator coverage.
- The scorer remains heuristic and unchanged.
- Real adapters remain future work.

## Recommended Next Milestone

The next milestone should not jump directly into live provider execution. A better next step is:

Milestone 6 — Controlled Adapter Sandbox Design & Non-Gated Live Output Preparation

Possible slices:

1. Live-output sandbox design document.
2. Non-gated output directory policy.
3. Provider, local, and CLI adapter risk matrix.
4. Adapter run metadata draft.
5. Manual approval checklist for the first real adapter experiment.

This keeps live-output preparation outside the deterministic quality gate while making the first real adapter experiment reviewable before any public benchmark claim exists.

## Tag Readiness

After the closeout commit and a clean quality gate, the repository is ready for:

`v0.5.0-adapter-contract-hardening`
