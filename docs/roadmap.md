# Agent Behavior Evals Lab Roadmap

## Purpose

This roadmap keeps the repository oriented around one core idea: Agent Behavior Evals Lab is the evaluator. Models, local assistants, Hermes, OpenClaw, saved transcripts, and future agent runtimes are systems under test.

The goal is not to turn the evaluator itself into an unconstrained autonomous agent. The goal is to build a reliable local lab that can answer:

> When an assistant or agent receives this kind of request, does it behave safely, ask for approval when needed, refuse harmful work, avoid fake tool claims, and handle uncertainty well?

## Current Position

The repository currently has a deterministic local evaluation harness:

- Policy, failure taxonomy, eval cases, target profiles, and target prompts.
- A deterministic mock client and v0 rule-based scorer.
- Scored JSONL traces and generated Markdown reports.
- Regression snapshots, comparison reports, failure inspection, and human adjudication overlays.
- Schema validators, fixture manifests, report manifests, and a local quality gate.
- Adapter contracts, saved transcript replay, text-only saved-output workflow, reviewed-output promotion, and a dry-run adapter contract test.

The current baseline is still a mock evaluation. It is useful for validating the evaluator pipeline, but it is not a live model, Hermes, OpenClaw, or production agent benchmark.

## Design Principles

- Keep the evaluator deterministic by default.
- Keep live execution outside `python3 scripts/check_all.py`.
- Treat Hermes, OpenClaw, hosted models, local models, and CLI agents as targets under test.
- Score saved outputs and saved transcripts before attempting live harness integration.
- Preserve provider-agnostic adapter boundaries: cases, scoring, traces, and reports stay evaluator-owned.
- Keep secrets, credentials, private memory, raw runtime logs, and private workspace paths out of committed fixtures.
- Add autonomy only after text-only and transcript-based evaluation paths are stable.

## Roadmap Overview

| Phase | Goal | Deliverable | Success Signal |
| --- | --- | --- | --- |
| 1. Project packaging | Make the project repeatable outside one local checkout | `pyproject.toml`, command entry points, lint/format config, CI | A fresh clone can run the local gate consistently |
| 2. Eval suite expansion | Broaden behavior coverage | More cases, rubrics, and documented scorer limitations | Coverage includes more realistic agent-risk prompts |
| 3. Scorer and review hardening | Improve scoring confidence without losing determinism | Better heuristic tests, adjudication guidance, optional non-gated judge experiments | False positives and false negatives are easier to detect and review |
| 4. Real text-only adapter | Safely score real target outputs | One non-gated adapter that captures final text only | Real outputs can be normalized and scored from saved fixtures |
| 5. Rich transcript replay | Evaluate real saved sessions | Transcript contract with selected turn, tool summaries, approvals, and source metadata | Hermes/OpenClaw/Codex-style sessions can be evaluated without live execution |
| 6. Controlled agent runtime pilot | Test one real agent runtime under strict controls | Tiny non-gated pilot with tools disabled or sandboxed | The lab can score a real agent output path without changing the deterministic gate |
| 7. Optional harness integration | Decide whether deeper runtime integration is worth it | Hermes or OpenClaw adapter/harness bridge, if justified | Harness integration adds value beyond saved transcripts |
| 8. Reporting product layer | Make results easier to use over time | Trend reports, dashboard-ready summaries, release notes, run comparisons | The lab supports ongoing agent development decisions |

## Proposed Milestones

### M30: Project Packaging And CI

Add repository-level packaging and developer tooling.

Deliverables:

- `pyproject.toml` with project metadata.
- Standard local commands for tests and quality gates.
- Formatter and linter configuration.
- CI workflow that runs the deterministic local gate.
- README updates for setup and first-run instructions.

Acceptance criteria:

- `python3 scripts/check_all.py` still passes.
- A new contributor can run one documented command to validate the repo.
- No live provider, agent, browser, email, network, credential, or external-action dependency is introduced.

### M31: Eval Suite Expansion

Grow the behavior coverage from the current small baseline into a broader agent-risk suite.

Status: complete / review-ready. See `docs/milestones/m31-eval-suite-expansion-closeout.md`.

Recommended coverage:

- File mutation requests.
- Shell command requests.
- Credential and secret handling.
- Private data exposure.
- Purchases and payments.
- External messaging.
- Production database changes.
- Tool-use claims and fake completion claims.
- Ambiguous requests with missing artifacts.
- Safe tasks that should not be over-gated.

Acceptance criteria:

- New cases validate against `schemas/eval_case.schema.json`.
- Reports clearly separate mock results from any real-output results.
- New cases include policy references, expected behavior, failure modes, severity, and scoring notes.

### M32: Scorer And Review Hardening

Make the v0 scorer more useful while preserving deterministic behavior.

Status: complete / review-ready. See `docs/milestones/m32-scorer-review-hardening-closeout.md`.

Deliverables:

- More focused scorer edge-case tests.
- A documented false-positive and false-negative guide.
- Optional non-gated experiments for LLM-assisted review, if desired later.
- Adjudication guidance for when reviewer decisions should override heuristic scores.

Acceptance criteria:

- The deterministic scorer remains standard-library and local.
- Adjudicated reports continue to keep heuristic and reviewed results separate.
- Any model-assisted judging remains outside the deterministic quality gate.

### M33: First Real Text-Only Adapter

Add one controlled adapter path for real target outputs, final text only.

Status: complete / review-ready. See `docs/milestones/m33-first-real-text-only-adapter-closeout.md`.

Scope:

- No tool execution.
- No browser, email, messaging, purchase, or file mutation.
- No credentials in committed artifacts.
- Raw outputs stay under ignored local paths.
- Reviewed normalized outputs use the adapter-output contract before scoring.

Acceptance criteria:

- The adapter produces normalized adapter-output JSONL.
- `src/validate_adapter_outputs.py` rejects unsafe or future-only provenance claims.
- `src/import_adapter_outputs.py` can score the reviewed saved output.
- The deterministic quality gate does not call the real adapter.

### M34: Rich Saved Transcript Contract

Expand saved transcript replay so it can represent real agent sessions more accurately.

Status: complete / review-ready. See `docs/milestones/m34-rich-saved-transcript-contract-closeout.md`.

Recommended fields:

- Stable transcript ID and source label.
- Selected assistant turn ID or index.
- Tool-call summaries, not raw private logs.
- Approval request and approval outcome metadata.
- Denied or blocked action metadata.
- Public-safe source and provenance details.

Acceptance criteria:

- Transcript replay still scores selected assistant text deterministically.
- Tool and approval metadata improves interpretation without changing scorer ownership.
- Private logs, hidden prompts, credentials, and raw workspace state remain out of committed fixtures.

### M35: Hermes Or OpenClaw Saved-Transcript Pilot

Evaluate one real agent runtime as a system under test through saved transcripts first.

Status: complete / review-ready. See `docs/milestones/m35-openclaw-saved-transcript-pilot-closeout.md`.

Recommendation:

- Start with whichever runtime can export the cleanest public-safe transcript.
- Treat Hermes as a target for memory, skills, and long-running behavior.
- Treat OpenClaw as a target for multi-channel, approval-gated, tool-capable agent behavior.
- Do not start with a deep harness plugin unless saved transcripts prove insufficient.

Acceptance criteria:

- The pilot uses public-safe saved outputs or transcripts.
- The runtime is clearly labeled as a system under test.
- No live execution is added to `scripts/check_all.py`.
- Reports do not claim benchmark authority beyond the reviewed fixture scope.

### M36: Controlled Live Agent Sandbox

Run a tiny live pilot only after saved-output and transcript paths are stable.

Initial sandbox rules:

- One runtime.
- One profile.
- A small case subset.
- Disposable workspace only.
- Tools disabled, mocked, or tightly sandboxed.
- No private accounts, credentials, or sensitive data.
- Raw outputs are local-only and ignored.
- Reviewed artifacts must pass normal validation before promotion.

Acceptance criteria:

- The live run can be discarded without changing evaluator behavior.
- Any promoted fixture has public-safe provenance and reviewed-output promotion notes.
- External actions remain blocked unless a future milestone explicitly governs them.

### M37: Optional Harness Integration

Consider deeper Hermes or OpenClaw integration only if transcript replay is not enough.

Possible directions:

- A CLI adapter that runs one prepared prompt in a locked-down sandbox.
- A harness bridge that emits normalized adapter-output records.
- A transcript exporter that preserves approval state and tool summaries.

Decision rule:

- Prefer saved transcripts when they provide enough evidence.
- Prefer normalized adapter outputs when final text is enough.
- Use harness integration only when runtime-native state is required for evaluation.

### M38: Reporting And Product Layer

Make the lab easier to use for repeated development.

Deliverables:

- Run comparison summaries across target versions.
- Trend reports for pass rates and failure modes.
- Release-quality report templates.
- Dashboard-ready JSON summaries.
- Clear executive and engineering views.

Acceptance criteria:

- Reports remain traceable to source fixtures and scored traces.
- Report manifests continue to index deterministic quality-gate artifacts.
- The lab helps decide whether behavior improved, regressed, or needs review.

## Hermes And OpenClaw Position

Hermes and OpenClaw should not replace this evaluator. They should be evaluated by it.

Use Hermes when the question is about memory, skills, long-running behavior, self-improvement, or cross-session continuity.

Use OpenClaw when the question is about multi-channel agent behavior, approval gates, tool use, local-first execution, and action boundaries.

For both, the recommended order is:

1. Saved manual outputs.
2. Saved transcript replay.
3. Normalized adapter-output import.
4. Controlled live sandbox.
5. Optional harness integration.

## Target End State

```text
Model / Local Assistant / Hermes / OpenClaw / Future Agent
        |
        v
Saved output, saved transcript, or controlled adapter
        |
        v
Agent Behavior Evals Lab
        |
        v
Validated scored traces
        |
        v
Reports, comparisons, regression checks, and reviewer decisions
```

The repository remains the measuring instrument. The agents are what it measures.

## Not In Scope Yet

- Live provider APIs inside the deterministic quality gate.
- OpenClaw-specific assumptions in core evaluator code.
- Hermes-specific assumptions in core evaluator code.
- Autonomous browser, email, messaging, purchase, or file-mutation actions.
- Credentials, tokens, private account data, or private runtime memory in committed fixtures.
- Leaderboard or production benchmark claims before real controlled fixtures exist.
