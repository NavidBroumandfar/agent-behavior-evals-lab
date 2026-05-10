# Milestone 4 — Adapter Readiness & External Fixture Hardening

Date: 2026-05-10

Status: Complete / tag-ready

Milestone 4 made the adapter boundary executable without adding live adapters. The repository can now validate normalized adapter-output records, import saved outputs into scored traces, compare controlled external fixture families, exercise a deterministic dry-run adapter contract path, and describe the provider-agnostic adapter interface future real adapters must satisfy.

M4 intentionally keeps target execution separate from evaluator logic. It strengthens the public, deterministic evaluator surface without claiming that live providers, local models, OpenClaw, browser/email tools, or external actions have been executed.

## Completed Slices

- M4.1 Normalized Adapter Output Schema Validation
- M4.2 Adapter-output Fixture Importer
- M4.3 External Fixture Comparison Report
- M4.4 Adapter Dry-Run Contract Test
- M4.5 Provider-Agnostic Adapter Interface Design

## Key Artifacts

Schema and validation:

- `schemas/adapter_output.schema.json`
- `src/validate_adapter_outputs.py`

Adapter-output import and dry-run contract path:

- `src/import_adapter_outputs.py`
- `src/dry_run_adapter.py`
- `traces/external/adapter_outputs.example.jsonl`
- `traces/external/dry_run_adapter_outputs.jsonl`
- `traces/scored/adapter_output_fixture_import.jsonl`
- `traces/scored/dry_run_adapter_output_import.jsonl`

External fixture comparison:

- `src/compare_external_fixtures.py`
- `reports/comparisons/external_fixture_comparison_report.md`
- `traces/scored/manual_output_eval.jsonl`
- `traces/scored/openclaw_manual_eval.jsonl`
- `traces/scored/saved_transcript_replay_eval.jsonl`

Documentation and adapter interface:

- `docs/wiki/concepts/normalized_adapter_outputs.md`
- `docs/wiki/concepts/external_fixture_comparison.md`
- `docs/wiki/concepts/adapter_dry_run_contract_test.md`
- `docs/wiki/concepts/provider_agnostic_adapter_interface.md`
- `targets/adapters/provider_agnostic_adapter_interface.md`
- `docs/milestones/m4-adapter-readiness-closeout.md`

Quality gate:

- `scripts/check_all.py`

## What The Repo Can Now Do

- Validate normalized adapter-output JSONL before scoring.
- Import saved adapter outputs into scored traces using existing eval cases and scorer logic.
- Compare controlled external fixture families in a deterministic Markdown report.
- Run a deterministic dry-run adapter contract path from normalized output generation through validation, import, and comparison.
- Describe a future provider-agnostic adapter interface that keeps collection target-side and scoring evaluator-side.

## What Remains Intentionally Blocked

- Live provider APIs.
- Provider SDKs.
- Local model execution.
- Live OpenClaw CLI execution.
- Browser, email, messaging, purchase, file mutation, or other external actions.
- Credentials, secrets, private account metadata, and private runtime integration.
- Autonomous external actions.
- Real adapter execution inside the deterministic quality gate.

These are blocked because M4 is about making the saved-output boundary reviewable and deterministic first. Live collection needs separate safety, provenance, storage, and quality-gate decisions before it belongs in this public repository.

## Quality Gate

From the repository root:

```bash
python3 scripts/check_all.py
```

The quality gate validates and regenerates deterministic artifacts, including unit tests, schema validation, adapter-output fixture validation/import, dry-run adapter generation/validation/import, mock eval generation, report generation, regression checking, failure inspection, manual output evaluation, OpenClaw-style manual fixture evaluation, saved transcript replay, external fixture comparison, trace count checks, and Python compile checks.

It should leave the repository clean. The gate does not call live providers, execute OpenClaw, run local models, use browser/email tools, perform external actions, use credentials, or reach private runtime state.

## Portfolio Interpretation

M4 matters for LLM and agent evaluation credibility because it avoids vague "adapter-ready" claims. The repository now has a concrete source-normalization path, explicit provenance expectations, deterministic validation, a stable adapter boundary, saved-output comparison across fixture families, and a no-network contract test that future adapters can target.

The milestone also keeps the claims honest. Public reports compare saved fixtures, not live systems. The dry-run adapter is clearly a contract test, not a model adapter. OpenClaw-style samples remain sanitized fictional fixtures, not evidence of live OpenClaw execution. That separation makes the evaluator easier to trust because it does not blur fixture review, collection, scoring, and benchmark interpretation.

## Limitations

- Saved fixtures are not statistical benchmarks.
- Pass rates are fixture-specific and reflect small public-safe examples.
- The dry-run adapter is a contract test, not a model adapter.
- The scorer remains heuristic and unchanged.
- Real adapters remain future work.
- External fixture comparison summarizes already-scored local traces; it does not collect or rank live systems.

## Recommended Next Milestone

Milestone 5 should not jump directly to live provider execution. A better next step is:

M5 — Adapter Interface Test Harness & Provenance Extensions

Possible slices:

1. Richer adapter-output provenance fields.
2. Adapter interface conformance tests.
3. Negative and invalid fixture tests.
4. Fixture manifest or index.
5. Optional non-gated live-output sandbox design document.

This keeps the project moving toward real adapters while preserving the deterministic public quality gate and avoiding premature provider-specific runtime work.

## Tag Readiness

After the closeout commit and a clean quality gate, the repository is ready for:

`v0.4.0-adapter-readiness`
