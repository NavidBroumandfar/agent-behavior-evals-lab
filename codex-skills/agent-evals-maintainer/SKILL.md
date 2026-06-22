---
name: agent-evals-maintainer
description: Use when maintaining Agent Behavior Evals Lab, running local gates, updating generated artifacts, or checking that deterministic evaluator boundaries are preserved.
---

# Agent Evals Maintainer

Use this workflow for repository maintenance.

## Core Rule

The lab is the evaluator. Models, OpenClaw, Hermes, Codex, local runtimes, and
customer agents are systems under test.

Do not add live execution to the deterministic quality gate.

## Standard Checks

Run:

```bash
python3 scripts/dev.py test
python3 scripts/dev.py check
```

Run lint when dev tooling is installed:

```bash
python3 scripts/dev.py lint
```

If the system Python is externally managed, use a temporary virtual environment
instead of breaking the system package manager.

## Generated Artifacts

Generated traces, snapshots, ledgers, and reports may change when validators,
schemas, cases, reports, or scorer logic changes. Review these diffs before
committing.

Never silently accept generated changes that alter evidence claims, rankings,
or release boundaries.

## Safety Boundary

The deterministic gate must not call providers, local models, live agents,
browser/email tools, production systems, credentials, network collectors, or
private traces.
