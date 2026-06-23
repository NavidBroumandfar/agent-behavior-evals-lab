# Architecture

Agent Behavior Evals Lab is the evaluator. Target systems are evaluated through
saved outputs, transcripts, adapters, or future sandboxed runtime bridges.

## Core Flow

```text
policy + cases + target metadata
        |
        v
target output fixture or deterministic mock response
        |
        v
schema validation -> scoring -> trace writing -> reports -> release checks
```

## Core Boundaries

- Cases, scoring, traces, reports, and quality gates are evaluator-owned.
- Model clients, OpenClaw, Hermes, Codex, local models, and customer agents are
  systems under test.
- Live execution stays opt-in and outside the deterministic gate.
- Private evidence stays local or in the private/pro workflow unless redacted
  and promoted into a public-safe fixture.

## Public Evidence Paths

- deterministic mock baseline;
- reviewed manual outputs;
- saved transcript replay;
- local/open-weight reviewed live-local ledgers;
- synthetic production-policy scenario fixtures;
- public-safe tool-boundary metadata.

## Out-Of-Repository Workflows

Customer-specific operations, private adapters, dashboards, and delivery
workflows should stay outside this public repository. They may consume public
core outputs, but they should not duplicate scoring logic or introduce private
evidence into public fixtures.
