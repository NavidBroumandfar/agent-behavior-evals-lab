# Milestone 30 - Project Packaging And CI

Date: 2026-06-20

Status: Complete / review-ready

Milestone 30 adds the first repository-level packaging and continuous-integration layer for Agent Behavior Evals Lab.

M30 does not add live provider calls, local model execution, CLI agent execution, credentials, network collection, browser/email actions, autonomous actions, or real adapter execution inside the deterministic quality gate.

## Completed Slices

- M30.1 Added `pyproject.toml` with project metadata, Python version support, dev tooling extras, and Ruff configuration.
- M30.2 Added `scripts/dev.py` as a small local command wrapper for `test`, `check`, and `lint`.
- M30.3 Added `.github/workflows/local-quality-gate.yml` so CI runs Ruff and the deterministic local quality gate.
- M30.4 Added tests that verify project tooling, the developer wrapper, and CI wiring remain present.
- M30.5 Updated README setup instructions for local tests, the full gate, and optional lint tooling.
- M30.6 Updated the local `py_compile` gate to include the developer command wrapper.

## Key Artifacts

Code and config:

- `pyproject.toml`
- `scripts/dev.py`
- `.github/workflows/local-quality-gate.yml`
- `tests/test_project_tooling.py`
- `scripts/check_all.py`

Docs:

- `README.md`
- `docs/roadmap.md`
- `docs/wiki/index.md`

## What The Repo Can Now Do

- Declare project metadata and supported Python version in a standard file.
- Install optional development tooling with `python3 -m pip install ".[dev]"`.
- Run unit tests through `python3 scripts/dev.py test`.
- Run the full deterministic local gate through `python3 scripts/dev.py check`.
- Run Ruff through `python3 scripts/dev.py lint` when dev tooling is installed.
- Run lint and the deterministic gate in GitHub Actions.

## What Remains Intentionally Blocked

- Live model calls.
- Live Hermes or OpenClaw execution.
- Provider SDKs or credentials.
- Network collection.
- Browser, email, messaging, purchase, or file-mutation actions.
- Treating CI or lint results as real model benchmark evidence.

## Quality Gate

From the repository root:

```bash
python3 scripts/check_all.py
```

The gate remains deterministic and local.

## Recommended Next Milestone

Milestone 31 should expand eval case coverage around realistic agent-risk prompts, especially file mutation, shell commands, credential handling, private data exposure, purchases, external messaging, production data changes, fake completion claims, and safe tasks that should not be over-gated.
