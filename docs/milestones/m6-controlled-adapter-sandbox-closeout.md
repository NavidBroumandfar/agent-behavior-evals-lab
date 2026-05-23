# Milestone 6 - Controlled Adapter Sandbox & Non-Gated Live Output Preparation

Date: 2026-05-23

Status: Complete / tag-ready

Milestone 6 turns the M5 recommendation into an executable preparation layer for future real adapter experiments. It does not add live execution. It adds a controlled sandbox policy, a public-safe adapter run metadata contract, metadata validation, tests, and quality-gate wiring so future live-output collection can be planned without weakening deterministic evaluator boundaries.

## Completed Slices

- M6.1 Controlled adapter sandbox policy.
- M6.2 Non-gated local output policy.
- M6.3 Provider/local/CLI adapter risk matrix.
- M6.4 Adapter run metadata schema and example.
- M6.5 Adapter run metadata validator and tests.
- M6.6 Quality-gate integration for metadata validation only.

## Key Artifacts

Policy and docs:

- `targets/adapters/controlled_adapter_sandbox.md`
- `docs/wiki/concepts/controlled_adapter_sandbox.md`

Metadata contract:

- `schemas/adapter_run_metadata.schema.json`
- `traces/external/adapter_run_metadata.example.json`
- `src/validate_adapter_run_metadata.py`
- `tests/test_adapter_run_metadata_validation.py`

Quality gate:

- `scripts/check_all.py`

## What The Repo Can Now Do

- Describe a future adapter experiment without executing it.
- Validate committed public-safe adapter run metadata.
- Enforce that raw outputs stay local-only.
- Enforce that live runs stay outside the deterministic quality gate.
- Require sanitization and review before normalized outputs can become fixtures.
- Give future adapter work a concrete approval checklist and risk matrix.

## What Remains Intentionally Blocked

- Live provider calls.
- Local model execution inside the quality gate.
- CLI agent execution inside the quality gate.
- Browser, email, messaging, purchase, file mutation, shell, or external actions.
- Credentials, secrets, private prompts, private logs, and private runtime data in committed artifacts.
- Real adapter execution inside `scripts/check_all.py`.
- Benchmark claims from planned metadata or saved examples.

## Quality Gate

From the repository root:

```bash
python3 scripts/check_all.py
```

The gate validates adapter run metadata as a public-safe planning artifact. It does not run the adapter described by that metadata.

## Portfolio Interpretation

M6 makes the project more credible as an agent-evaluation lab because it separates three different things that are easy to blur:

- Planning a live-output experiment.
- Collecting raw outputs locally.
- Publishing reviewed deterministic fixtures for scoring.

The repo is now ready for a first text-only, no-tool, non-gated real adapter experiment. It is not ready for autonomous tool execution or external actions.

## Recommended Next Milestone

Milestone 7 should implement one text-only saved-output collector outside the quality gate.

Suggested scope:

1. Target registry for real model or adapter labels.
2. Local raw output collector that writes `traces/raw/*.local.jsonl`.
3. Review command that converts approved raw records into normalized adapter-output JSONL.
4. Trace schema expansion for adapter metadata fields.
5. Human adjudication notes for scorer false positives and false negatives.

Keep tool execution and external actions blocked until the text-only path is stable.

## Tag Readiness

After the closeout commit and a clean quality gate, the repository is ready for:

`v0.6.0-controlled-adapter-sandbox`
