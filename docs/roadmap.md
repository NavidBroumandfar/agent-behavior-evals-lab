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
- Adapter contracts, saved transcript replay, text-only saved-output workflow, reviewed-output promotion, a dry-run adapter contract test, a controlled local agent sandbox pilot, and an optional harness-integration decision gate.
- Reporting product summaries and deterministic release-note artifacts.

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

Status: complete / review-ready. See `docs/milestones/m36-controlled-live-agent-sandbox-closeout.md`.

Implementation note:

- M36 uses a metadata-driven local no-tool sandbox runner, not a provider, local model, live OpenClaw/Hermes runtime, browser/email tool, network collector, shell executor, or external-action harness.
- The runner is manual and non-gated. The deterministic quality gate validates the committed metadata plan and compiles/tests local guardrails, but it does not run the sandbox command or commit raw outputs.

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

Status: complete / review-ready. See `docs/milestones/m37-optional-harness-integration-decision-closeout.md`.

Implementation note:

- M37 adds a local harness bridge plan schema, validator, example decision plan, and adapter contract.
- The current decision is `defer_harness_integration` because runtime-native state is not yet required. The deterministic quality gate validates the plan, but it does not run Hermes, OpenClaw, a CLI agent, a provider, a local model, shell commands, browser/email tools, network collection, or external actions.

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

Status: complete / review-ready. See `docs/milestones/m38-reporting-product-layer-closeout.md`.

Implementation note:

- M38 adds a deterministic dashboard-ready JSON summary and a Markdown executive/engineering report generated from already-scored traces, fixture manifests, adjudication snapshots, and the M37 harness decision plan.
- No live output collection, scorer changes, provider calls, model execution, harness execution, network access, private data, or external actions are introduced.

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

### M39: Release Notes Reporting

Turn the reporting product layer into release-ready handoff artifacts.

Status: complete / review-ready. See `docs/milestones/m39-release-notes-reporting-closeout.md`.

Implementation note:

- M39 adds deterministic release-note JSON and Markdown generated from the M38 product summary, report manifest, roadmap, and M35-M39 milestone closeouts.
- No live output collection, scorer changes, provider calls, model execution, harness execution, network access, private data, or external actions are introduced.

Deliverables:

- Release-ready JSON snapshot.
- Reader-facing release notes.
- Milestone rollup for recent roadmap phases.
- Report-manifest coverage for release artifacts.

Acceptance criteria:

- Release notes remain traceable to committed local artifacts.
- Report manifests index the new release artifacts.
- The release handoff preserves the evaluator boundary and avoids benchmark claims.

## Next Roadmap Section

The post-M39 work should shift from scaffold completeness to evidence quality. The lab now has local runners, schemas, validators, replay, adapter contracts, adjudication reporting, product summaries, and release notes. The next phases should make the evidence more representative before adding deeper live-agent integration.

Shared boundary for M40-M44:

- Keep the deterministic quality gate local and public-safe.
- Do not add live provider calls, credentials, private logs, browser/email actions, network collection, shell actions, file-mutation actions, or gated LLM review.
- Prefer saved transcripts, reviewed text-only outputs, and normalized local fixtures over runtime harness integration.
- Treat any optional runtime trial as non-gated, manually reviewed, and disposable unless a later phase explicitly promotes public-safe output.

### M40: Evidence Quality Audit

Audit the current fixtures, cases, scorers, adjudications, and reports to identify what the lab can and cannot currently prove.

Status: complete / review-ready. See `docs/milestones/m40-evidence-quality-audit-closeout.md`.

Implementation note:

- M40 adds deterministic JSON and Markdown audit artifacts generated from committed local cases, scored traces, fixture manifests, adjudication artifacts, report metadata, scorer documentation, and the roadmap.
- The audit separates missing fixture coverage, scorer weakness, and reporting weakness, with every gap tied to source paths.
- No new outputs are collected, no traces are rescored, no scorer behavior changes, no provider/runtime calls are added, and no benchmark claims are made.

Deliverables:

- A deterministic evidence inventory across eval cases, saved outputs, saved transcripts, adjudications, scored traces, and reports.
- A gap report that separates missing fixture coverage from scorer weakness and reporting weakness.
- Public-safe recommendations for the next fixture expansion.
- Quality-gate coverage for the audit artifact if it becomes a committed report.

Acceptance criteria:

- The audit is generated from committed local artifacts only.
- Gaps are tied to specific source files or fixture groups.
- The report does not make benchmark, leaderboard, or real-world model quality claims.

### M41: Public-Safe Transcript Expansion

Expand saved transcript coverage using realistic but sanitized local examples.

Status: complete / review-ready. See `docs/milestones/m41-public-safe-transcript-expansion-closeout.md`.

Implementation note:

- M41 adds a new synthetic public-safe saved transcript fixture family with 8 selected assistant turns.
- The expansion covers safe task-following, approval boundaries, refusal boundaries, and uncertainty handling with both passing and intentionally failing examples.
- No private run, raw runtime log, live provider, Hermes/OpenClaw runtime, browser/email action, shell action, file mutation, or credential-bearing artifact is promoted.

Deliverables:

- Additional saved transcript fixtures covering representative assistant behaviors.
- Manifest entries and schema validation for every new fixture.
- Replay coverage that exercises approval boundaries, refusal boundaries, and task-following behavior without external actions.
- Promotion notes for any fixture derived from a manually reviewed run.

Acceptance criteria:

- Fixtures contain no credentials, private account data, private logs, or runtime-sensitive information.
- Transcript replay remains deterministic and offline.
- New coverage improves the evidence gaps identified in M40.

### M42: Scorer Calibration From Adjudications

Use adjudication history to make scorer behavior easier to inspect and tune without adding gated LLM judgment.

Status: planned.

Deliverables:

- A local calibration summary comparing scorer outcomes against adjudication decisions.
- Clear labels for scorer false positives, false negatives, and ambiguous cases.
- Suggested scorer or rubric refinements that remain deterministic.
- Regression checks for any accepted scorer changes.

Acceptance criteria:

- Calibration uses committed adjudication fixtures only.
- Any scorer change is explainable, deterministic, and covered by tests.
- Human review remains advisory unless explicitly promoted through a local deterministic artifact.

### M43: Historical Trend Snapshots

Turn the reporting layer into a simple history of evaluator health over time.

Status: planned.

Deliverables:

- Versioned trend snapshots for pass rates, failure modes, adjudication outcomes, fixture counts, and report-manifest coverage.
- A Markdown trend report suitable for release review.
- Manifest coverage for committed trend artifacts.
- Deterministic regeneration checks when source behavior changes.

Acceptance criteria:

- Trends are derived from committed local reports and scored traces.
- Snapshot changes are intentional, reviewable, and tied to source artifacts.
- Reports distinguish evaluator-health trends from model-performance claims.

### M44: Optional Non-Gated Runtime Trial

Only after evidence quality improves, run a tightly scoped runtime trial that cannot affect the deterministic gate by default.

Status: planned / optional.

Deliverables:

- A documented non-gated trial procedure for one prepared prompt in a locked-down local-safe setup.
- Metadata showing the run was manual, reviewed, disposable, and excluded from deterministic scoring until promoted.
- A promotion path that converts reviewed output into an existing public-safe fixture format.
- A closeout decision on whether runtime-native evidence is actually needed.

Acceptance criteria:

- The trial does not run inside `python3 scripts/dev.py check`.
- No credentials, providers, private accounts, network collection, browser/email actions, shell actions, or file-mutation actions are introduced.
- The default evaluator remains saved-output and saved-transcript first.

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
