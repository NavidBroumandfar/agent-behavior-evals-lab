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
- Adapter contracts, saved transcript replay, text-only saved-output workflow, reviewed-output promotion, a dry-run adapter contract test, a controlled local agent sandbox pilot, an optional harness-integration decision gate, and a default-deny sandboxed tool runtime contract.
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

Status: complete / review-ready. See `docs/milestones/m42-scorer-calibration-closeout.md`.

Implementation note:

- M42 adds deterministic JSON and Markdown calibration artifacts generated from committed public-safe adjudication fixtures.
- The calibration labels reviewed records as scorer upheld failures, upheld passes, false positives, false negatives, or ambiguous reviews.
- No scorer changes are accepted in M42; suggested refinements remain advisory until a future deterministic change includes focused tests and regression coverage.

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

Status: complete / review-ready. See `docs/milestones/m43-historical-trend-snapshots-closeout.md`.

Implementation note:

- M43 adds deterministic JSON and Markdown trend artifacts generated from committed local reports, manifests, snapshots, scorer calibration, and scored traces.
- The trend snapshot covers pass rates, failure modes, adjudication outcomes, fixture counts, report-manifest coverage, and versioned checkpoint rows for recent roadmap phases.
- Trend outputs describe evaluator health and fixture/report coverage only; they are not model-performance trends, leaderboard results, or production benchmark claims.

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

Status: complete / review-ready. See `docs/milestones/m44-optional-non-gated-runtime-trial-closeout.md`.

Implementation note:

- M44 adds a schema-backed, validation-only runtime-trial plan for one prepared public-safe prompt.
- The closeout decision is `defer_live_runtime_trial` because runtime-native evidence is not needed yet.
- No raw runtime output is committed, no runtime is executed by the quality gate, and promotion remains limited to reviewed public-safe adapter-output fixtures.

Deliverables:

- A documented non-gated trial procedure for one prepared prompt in a locked-down local-safe setup.
- Metadata showing the run was manual, reviewed, disposable, and excluded from deterministic scoring until promoted.
- A promotion path that converts reviewed output into an existing public-safe fixture format.
- A closeout decision on whether runtime-native evidence is actually needed.

Acceptance criteria:

- The trial does not run inside `python3 scripts/dev.py check`.
- No credentials, providers, private accounts, network collection, browser/email actions, shell actions, or file-mutation actions are introduced.
- The default evaluator remains saved-output and saved-transcript first.

### M45: External Fixture Adjudication Coverage

Increase reviewer coverage for committed public-safe external fixture groups before revisiting runtime-native evidence.

Status: complete / review-ready. See `docs/milestones/m45-external-fixture-adjudication-coverage-closeout.md`.

Implementation note:

- M45 adds a manifest-backed public-safe adjudication fixture for selected saved-transcript and normalized adapter-output scored traces.
- The phase increases calibration and evidence-audit coverage from one source trace to three source traces.
- No scored traces are rewritten, no scorer changes are accepted, and reviewer decisions remain a report-time interpretation layer.

Recommended scope:

- Add adjudication fixtures for selected public-safe transcript and adapter-output scored traces.
- Keep heuristic scores and reviewer decisions separate.
- Update calibration and evidence audit outputs after review coverage changes.
- Avoid scorer changes unless they are deterministic, focused, and backed by reviewed examples.

Acceptance criteria:

- Adjudications reference committed scored traces only.
- External fixture review coverage is explicit in the adjudication manifest and regression snapshot.
- No live runtime, provider, local-model, network, browser/email, shell, file-mutation, credential, or private-log dependency is introduced.

### M46: Needs-Discussion Resolution

Resolve the remaining public-safe adjudication records that are still marked `needs_discussion` before considering deterministic scorer changes.

Status: complete / review-ready. See `docs/milestones/m46-needs-discussion-resolution-closeout.md`.

Implementation note:

- M46 resolves the three remaining discussion records as `uphold_score` adjudications with updated public-safe rationales.
- Manifest quality-gate thresholds now require zero unresolved `needs_discussion` records.
- No scored traces are rewritten, no scorer changes are accepted, and reviewer decisions remain a report-time interpretation layer.

Recommended scope:

- Add follow-up public-safe reviewer decisions that either uphold the original score or promote an explicit override.
- Keep the original ambiguous records for history unless a new fixture supersedes them through the manifest.
- Update calibration summaries, evidence audits, and trend snapshots after the discussion queue changes.
- Continue to avoid live runtime, provider, local-model, network, browser/email, shell, file-mutation, credential, private-log, or gated LLM review dependencies.

Acceptance criteria:

- The remaining `needs_discussion` count is lower and explicitly tracked in the adjudication regression snapshot.
- Any override has a concrete policy rationale and remains separate from heuristic scored traces.
- No scorer change is accepted unless a separate deterministic phase adds focused tests and regression coverage.

### M47: Deterministic Scorer Refinement Triage

Decide whether the resolved adjudication and calibration evidence supports narrow deterministic scorer or rubric refinements.

Status: complete / review-ready. See `docs/milestones/m47-deterministic-scorer-refinement-triage-closeout.md`.

Implementation note:

- M47 adds deterministic JSON and Markdown triage artifacts for scorer or rubric refinement candidates.
- The current decision is `no_scorer_change_accepted`; both candidates are deferred until more focused public-safe examples and nearby control tests exist.
- No scorer code, scored traces, reviewer decisions, live execution, or gated LLM review behavior is changed.

Recommended scope:

- Review current false positive and false negative evidence from `reports/comparisons/scorer_calibration_summary.json`.
- Separate scorer-code candidates from rubric/documentation candidates.
- Add focused tests before accepting any deterministic scorer behavior change.
- Keep model-assisted judging, live providers, local models, runtime harnesses, browser/email, shell, file-mutation, credentials, private logs, and gated LLM review out of scope.

Acceptance criteria:

- Each accepted candidate is tied to a public-safe adjudication or fixture record.
- Any scorer change is deterministic, local, and covered by focused tests plus the full quality gate.
- If evidence is insufficient, the phase records a no-change decision rather than changing scorer behavior prematurely.

### M48: External Fixture Review Expansion

Broaden public-safe reviewer coverage for remaining external fixture traces before accepting scorer refinements.

Status: complete / review-ready. See `docs/milestones/m48-external-fixture-review-expansion-closeout.md`.

Implementation note:

- M48 adds a manifest-backed public-safe adjudication fixture for previously unreviewed external fixture trace families.
- The expansion adds 22 `uphold_score` reviewer decisions across manual-output, saved-transcript replay, OpenClaw-style manual, dry-run adapter-output, and OpenClaw saved-transcript pilot traces.
- No scorer behavior changes, scored trace rewrites, live runtime execution, provider calls, model-assisted judging, private logs, or external actions are introduced.

Recommended scope:

- Add adjudication coverage for selected manual-output, saved-transcript replay, OpenClaw-style, and dry-run adapter-output traces that remain unreviewed.
- Keep heuristic scores and reviewer decisions separate.
- Regenerate calibration, triage, evidence audit, trend, and release artifacts after coverage changes.
- Continue to avoid live runtime, provider, local-model, network, browser/email, shell, file-mutation, credential, private-log, or gated LLM review dependencies.

Acceptance criteria:

- Additional adjudications reference committed scored traces only.
- External fixture review coverage improves and remains explicit in the adjudication manifest and regression snapshot.
- No scorer behavior changes are accepted unless a separate deterministic phase includes focused tests and full quality-gate validation.

### M49: Scorer Candidate Control Tests

Add focused deterministic controls around the current scorer-refinement candidates before deciding whether any scorer or rubric behavior should change.

Status: complete / review-ready. See `docs/milestones/m49-scorer-candidate-control-tests-closeout.md`.

Implementation note:

- M49 adds deterministic JSON and Markdown control-test artifacts for current scorer-refinement candidates.
- The controls cover safe low-friction clarification versus over-refusal and approval-gate disclosure specificity.
- The current decision is `no_scorer_change_accepted`; controls are executable evidence for a later decision phase, not a scorer-code update.

Recommended scope:

- Use the expanded M48 calibration and triage artifacts as inputs.
- Add focused tests for safe low-friction clarification versus over-refusal.
- Add focused tests for approval-gate risk, scope, target, and reversibility disclosure.
- Include nearby positive and negative controls to protect existing accepted behavior.
- Keep reviewer decisions separate from scored traces.
- Continue to avoid live runtime, provider, local-model, network, browser/email, shell, file-mutation, credential, private-log, or gated LLM review dependencies.

Acceptance criteria:

- Each test maps to a public-safe adjudication, fixture record, or documented scorer limitation.
- Any scorer or rubric change is deterministic, local, explainable, and covered by the full quality gate.
- If controls show insufficient evidence, the phase records a no-change decision rather than changing scorer behavior.

### M50: Deterministic Scorer Change Decision

Decide whether the M49 controls justify narrow deterministic scorer changes or a durable rubric-only no-change decision.

Status: complete / review-ready. See `docs/milestones/m50-deterministic-scorer-change-decision-closeout.md`.

Implementation note:

- M50 adds deterministic JSON and Markdown decision artifacts for the M49 scorer candidate controls.
- The current decision is `rubric_only_no_scorer_change`.
- No scorer code changes or scored trace behavior changes are accepted in M50.
- Future scorer changes should first add scorer-versioned adjudication guardrails or stronger public-safe control evidence.

Recommended scope:

- Use `reports/comparisons/scorer_candidate_controls.json` as the primary input.
- If changing scorer behavior, update `src/scorers.py` narrowly and update focused tests first.
- Regenerate scored traces only if scorer behavior changes.
- Preserve historical adjudication context for records whose original scorer result came from a previous scorer version.
- Keep reviewer decisions separate from heuristic scored traces.
- Continue to avoid live runtime, provider, local-model, network, browser/email, shell, file-mutation, credential, private-log, or gated LLM review dependencies.

Acceptance criteria:

- The phase either accepts narrow deterministic scorer changes with focused tests and regenerated artifacts, or records a no-change rubric decision.
- Any scorer change is traceable to M49 controls and public-safe adjudication evidence.
- The full deterministic local quality gate passes.

### M51: Scorer Versioning Guardrails

Add explicit scorer-version or pre-change outcome guardrails so future scorer behavior changes can preserve historical adjudication context.

Status: complete / review-ready. See `docs/milestones/m51-scorer-versioning-guardrails-closeout.md`.

Implementation note:

- M51 adds optional `historical_scorer_context` support to committed adjudication records.
- Records without historical context still require `original_*` fields to match the current source scored trace.
- Records with historical context must pin current trace fields and may preserve pre-change original scorer outcomes only when those outcomes differ from the current trace.
- No scorer code changes or scored trace behavior changes are accepted in M51.

Recommended scope:

- Use `reports/comparisons/scorer_change_decision.json` as the primary input.
- Decide how committed adjudications should reference scorer outcomes that predate a scorer change.
- Add deterministic validation support for historical scorer-version metadata or explicit pre-change outcome records.
- Keep reviewer decisions separate from heuristic scored traces.
- Do not change scorer behavior unless the versioning guardrail is already in place and covered by tests.
- Continue to avoid live runtime, provider, local-model, network, browser/email, shell, file-mutation, credential, private-log, or gated LLM review dependencies.

Acceptance criteria:

- Historical adjudication context is preserved if future scorer behavior changes.
- Validation rules clearly distinguish current scored trace fields from prior scorer outcomes.
- The full deterministic local quality gate passes.

### M52: Focused Scorer Evidence Expansion

Add more public-safe adjudicated controls for the current scorer-refinement candidates now that scorer-versioning guardrails exist.

Status: complete / review-ready. See `docs/milestones/m52-focused-scorer-evidence-expansion-closeout.md`.

Implementation note:

- M52 adds a synthetic public-safe focused scorer evidence fixture.
- M52 adds six reviewed adjudications over the focused scored trace.
- M52 covers safe-task clarification boundaries and approval-disclosure specificity.
- No scorer code changes or existing scored trace rewrites are accepted in M52.

Recommended scope:

- Use `reports/comparisons/scorer_versioning_guardrails.json` and `reports/comparisons/scorer_change_decision.json` as inputs.
- Add public-safe adjudications or controls that distinguish acceptable safe clarification from blocking safe-task confirmation.
- Add public-safe adjudications or controls that distinguish vague approval disclosure from target, scope, impact, and reversibility disclosure.
- Keep reviewer decisions separate from scored traces.
- Use `historical_scorer_context` only if a later phase changes scorer behavior and rewrites current trace outcomes.
- Continue to avoid live runtime, provider, local-model, network, browser/email, shell, file-mutation, credential, private-log, or gated LLM review dependencies.

Acceptance criteria:

- Additional evidence is tied to committed public-safe artifacts.
- Any scorer-change recommendation remains deterministic, local, and traceable to reviewed controls.
- The full deterministic local quality gate passes.

### M53: Future Scorer Promotion Or Rubric Update

Decide whether M49 controls, M50 no-change rationale, M51 guardrails, and M52 focused evidence justify a narrow deterministic scorer update, a rubric-only update, or another durable no-change decision.

Status: complete / review-ready. See `docs/milestones/m53-scorer-promotion-or-rubric-update-closeout.md`.

Implementation note:

- M53 records decision `rubric_only_update_no_scorer_change`.
- M53 accepts approval-disclosure review guidance that treats generic approval disclosures as review-required unless they identify target, scope, likely impact, and rollback or reversibility context.
- M53 accepts no scorer promotions, no scorer code changes, no scored trace rewrites, and no historical adjudication migration.

Recommended scope:

- Use `reports/comparisons/focused_scorer_evidence_expansion.json` as the primary new input.
- Use `reports/comparisons/scorer_change_decision.json` and `reports/comparisons/scorer_versioning_guardrails.json` as guardrail inputs.
- If changing scorer behavior, update `src/scorers.py` narrowly and add focused tests first.
- Use `historical_scorer_context` for adjudications whose original scorer fields predate any changed scored trace outcomes.
- Regenerate scored traces only if scorer behavior changes.
- Keep reviewer decisions separate from heuristic scored traces.
- Continue to avoid live runtime, provider, local-model, network, browser/email, shell, file-mutation, credential, private-log, or gated LLM review dependencies.

Acceptance criteria:

- The phase records either a narrow deterministic scorer update, a rubric-only update, or a no-change decision.
- Any scorer change is traceable to public-safe reviewed evidence and protected by focused controls.
- The full deterministic local quality gate passes.

## Next Roadmap Section: Evidence-First Live Benchmark Track

The post-M53 roadmap should move from evaluator scaffolding to real evidence. The detailed execution plan lives in `docs/live_benchmark_roadmap.md`.

The goal is to make the lab a credible benchmark and audit harness for local models first, then cloud models, local assistants, Hermes, OpenClaw, and future agent runtimes while preserving evidence boundaries.

New direction:

- Public benchmark evidence is public-safe, reproducible, and eligible for model rankings.
- Private production evidence is local-only, access-controlled, and eligible for private audit reports.
- Promoted public evidence starts as private or live evidence, then becomes public-safe only after redaction, review, validation, and explicit promotion.

Critical boundary:

- Public rankings must not depend on private evidence that outside readers cannot inspect.
- Private audit reports can use private runtime evidence but must not claim public benchmark reproducibility.
- Live provider and runtime execution must remain opt-in and outside the deterministic local quality gate.
- Credentials, raw private logs, hidden prompts, private runtime memory, private workspace paths, and unredacted private evidence must remain out of committed fixtures.

Immediate zero-cost sequence:

1. Ollama or local OpenAI-compatible model, text-only, public-safe cases only.
2. Manual public-safe saved-output samples from cloud chats the user already has access to.
3. Disposable local no-tool or mocked-tool agent harness around a local model.
4. OpenClaw in a disposable workspace with tools disabled, mocked, or sandboxed.
5. Hermes or memory-capable agents only after private evidence vault, redaction, retention, and promotion controls exist.

### M54: Local Benchmark Claim Charter And Evidence Classes

Define what the local-first benchmark is allowed to claim before it has cloud-provider evidence.

Status: complete / review-ready. See `docs/milestones/m54-local-benchmark-claim-charter-closeout.md`.

Implementation note:

- M54 adds `benchmarks/evidence_class_charter.json`, `schemas/benchmark_claim_charter.schema.json`, and `src/validate_benchmark_claim_charter.py`.
- The charter separates evaluator-health, local/open-weight benchmark, manual public sample, cloud benchmark, private audit, promoted public evidence, and unsupported claims.
- Local/Ollama evidence must be labeled separately from cloud-provider evidence.
- M54 does not run providers, local models, Ollama, Hermes, OpenClaw, private evidence collection, or runtime harnesses.

Deliverables:

- Evidence-class schema for local public benchmark, manual public sample, cloud public benchmark, private audit, and promoted public evidence.
- Claim taxonomy for evaluator-health, local/open-weight benchmark, manual public sample, cloud benchmark, private audit, production-policy evidence, and unsupported claims.
- Report language rules that prevent private evidence from contaminating public leaderboard claims.
- Rules for labeling Ollama/local-model results separately from hosted cloud-model results.

Acceptance criteria:

- Every report declares its evidence class.
- Public local rankings can only use public local benchmark evidence.
- Cloud rankings are not claimed until actual cloud-provider evidence exists.
- Private audit reports can use private evidence but must not claim public reproducibility.
- The local deterministic gate remains credential-free.

### M55: Public Local Benchmark Case Corpus V1

Build a larger public-safe case corpus designed for local model comparison first.

Status: complete / review-ready. See `docs/milestones/m55-public-local-benchmark-case-corpus-closeout.md`.

Implementation note:

- M55 adds frozen case set `local_public_v1` under `evals/benchmarks/local_public_v1/`.
- The corpus contains 210 public-safe cases: 30 each across safe tasks, approval gates, refusal boundaries, uncertainty, tool-use claims, privacy, and production changes.
- The manifest records smoke, standard, and extended split counts plus a SHA-256 hash of the case file.
- M55 does not run local models, Ollama, providers, Hermes, OpenClaw, or runtime harnesses.

Deliverables:

- At least 200 public-safe cases across safe tasks, approval-gated tasks, refusal-required tasks, uncertainty, tool-use claims, privacy, and production-change requests.
- Case-set versioning with frozen benchmark splits.
- Difficulty tags, policy references, and expected behavior notes.

Acceptance criteria:

- Cases validate locally.
- The benchmark split is immutable for a given version.
- No private data or provider-specific assumptions are included.
- Reports can distinguish corpus coverage from model quality.

### M56: Ollama And Local OpenAI-Compatible Adapter Registry

Add opt-in local model adapters without making live model execution part of the local quality gate.

Status: complete / review-ready. See `docs/milestones/m56-local-adapter-registry-closeout.md`.

Implementation note:

- M56 adds `targets/adapters/local_adapter_registry.json`, `schemas/local_adapter_registry.schema.json`, and `src/validate_local_adapter_registry.py`.
- The registry defines `ollama_text_only`, `local_openai_compatible_text_only`, and `manual_saved_output` adapter classes for future `local_public_v1` runs.
- Future local model calls must require `--live-local` and `AGENT_EVALS_ENABLE_LIVE_LOCAL`.
- M56 does not run local models, Ollama, providers, Hermes, OpenClaw, or runtime harnesses.

Deliverables:

- Adapter interface for Ollama, local OpenAI-compatible servers, and manual saved-output adapters.
- Registry metadata for model name, runtime, endpoint class, temperature, context window, tool availability, and estimated local cost.
- Explicit optional extension points for paid provider adapters later.

Acceptance criteria:

- No credential is required for the local Ollama path.
- Local model calls require an explicit live-local flag or equivalent enable switch.
- Local adapters produce normalized saved-output records.
- Unit tests use fakes only.

### M57: Opt-In Local Text-Only Model Harness

Run local models against public-safe prompts with tools disabled.

Status: complete / review-ready. See `docs/milestones/m57-opt-in-local-text-only-model-harness-closeout.md`.

Implementation note:

- M57 adds `scripts/live_local.py`, `src/live_local_harness.py`, `schemas/live_local_run.schema.json`, `src/validate_live_local_run.py`, and `traces/external/live_local_run_plan.example.json`.
- Live local execution requires both `--live-local` and `AGENT_EVALS_ENABLE_LIVE_LOCAL`.
- The deterministic gate validates the dry-run plan, schema, fake-client behavior, and reviewed-output provenance only; it does not call Ollama, local OpenAI-compatible servers, providers, agents, browser/email tools, shell/file actions as a system under test, gated LLM review, or external actions.
- Reviewed live-local normalized outputs require explicit `--allow-live-local` validation/import and an explicit `--case-path evals/benchmarks/local_public_v1/cases.jsonl` scoring input.

Deliverables:

- Opt-in local command for text-only runs.
- Timeout policy, model availability checks, retry policy, and run abort controls.
- Saved raw outputs under ignored local paths.
- Reviewed normalized outputs suitable for existing scoring and adjudication.

Acceptance criteria:

- The deterministic gate does not call local models.
- A local run can be reproduced from saved normalized outputs.
- Run metadata captures runtime, model, parameters, timestamp, case-set version, and prompt template version.
- Failed or partial local runs are clearly marked and excluded from rankings unless a future ledger/ranking policy allows them.

### M58: Reproducible Local Run Ledger

Make local model evidence auditable.

Status: complete / review-ready. See `docs/milestones/m58-reproducible-local-run-ledger-closeout.md`.

Implementation note:

- M58 adds `schemas/local_run_ledger.schema.json`, `src/local_run_ledger.py`, `src/validate_local_run_ledger.py`, and `traces/external/local_run_ledger.example.json`.
- The committed example is a dry-run public-safe fake-output ledger marked ranking-ineligible. It validates hashes, saved-output replay, run metadata, and provenance without executing a local model.
- M58 also promotes the M57 prompt template into `targets/prompts/local_text_only_v1.md` so ledger entries can hash the exact tools-disabled prompt.
- The deterministic gate validates generated public-safe fake outputs, scored traces, hashes, and metadata only; it does not call Ollama, local OpenAI-compatible servers, providers, agents, browser/email tools, shell/file actions as a system under test, gated LLM review, or external actions.

Deliverables:

- Run ledger schema for local model runs.
- Hashes for case set, prompt template, adapter version, normalized output file, and scorer version.
- Public-safe run manifest for published local benchmark runs.
- Validation command for run ledgers.

Acceptance criteria:

- A report can trace every scored local output to a run ledger entry.
- Ledger entries do not expose secrets or private prompts.
- Re-running from saved outputs does not require model runtime access.

### M59: Local Ranking Methodology

Define how local/open-weight models are ranked without overclaiming.

Status: complete / review-ready. See `docs/milestones/m59-local-ranking-methodology-closeout.md`.

Implementation note:

- M59 adds `benchmarks/local_ranking_methodology.json`, `schemas/local_ranking_methodology.schema.json`, `src/local_ranking_methodology.py`, `src/validate_local_ranking_methodology.py`, and non-publishable synthetic example artifacts.
- The methodology defines severity-weighted effective pass rate, heuristic pass rate, bootstrap uncertainty, tie policy, abstention policy, partial-run exclusion, eligibility requirements, and high-risk human-review sampling.
- The committed example uses fake public-safe ledger-like inputs over the smoke split and is marked `ranking_claim_allowed: false`.
- The deterministic gate validates methodology schema, fake inputs, deterministic calculations, and example-only artifacts. It does not publish real rankings or call local models.

Deliverables:

- Ranking metric definitions.
- Confidence intervals or bootstrap estimates.
- Tie policy, abstention policy, partial-run policy, and severity weighting.
- Required human-review sampling for high-risk cases.

Acceptance criteria:

- Rankings include sample size, uncertainty, exclusions, and benchmark version.
- Rankings distinguish heuristic score, adjudicated score, and unresolved review count.
- A model cannot be ranked from private-only evidence.
- Smoke-split and synthetic examples remain non-publishable; public rankings require ledger-backed `local_public_benchmark` evidence over standard or extended splits.

### M60: Local/Open-Weight Benchmark Report V1

Publish the first public-safe local/open-weight benchmark report.

Status: complete / evidence-gated review-ready. See `docs/milestones/m60-local-open-weight-benchmark-report-v1-closeout.md`.

Implementation note:

- M60 adds `reports/comparisons/local_open_weight_benchmark_v1.json`, `reports/comparisons/local_open_weight_benchmark_v1.md`, `schemas/local_benchmark_report.schema.json`, `src/local_benchmark_report.py`, and `src/validate_local_benchmark_report.py`.
- The committed report is public-safe and evidence-gated with `report_status: no_rankings_published` and `ranking_claim_allowed: false`.
- No leaderboard is published because no reviewed live-local, ledger-backed standard-or-extended split evidence is committed yet.
- The deterministic gate validates the report schema, source hashes, evidence exclusions, and no-ranking boundary only. It does not call local models.

Deliverables:

- Local public benchmark JSON snapshot.
- Markdown benchmark report.
- Model ranking table.
- Methodology and limitations section.
- Reproduction instructions from saved public-safe outputs.

Acceptance criteria:

- At least two real local model targets or one real local model plus one committed manual public-safe target are included.
- All ranked evidence is public-safe and traceable.
- The report avoids cloud-model and production-policy proof claims.
- The full deterministic local gate passes without provider credentials.
- With current committed evidence, the report must withhold rankings rather than claim the real-evidence publication criterion is met.

### M61-M65: Agent Runtime And Tool-Boundary Benchmark

Evaluate tool-capable agents without allowing uncontrolled external actions.

Status: complete / review-ready; M61-M65 complete. See `docs/milestones/m61-sandboxed-tool-runtime-contract-closeout.md`, `docs/milestones/m62-approval-action-boundary-recorder-closeout.md`, `docs/milestones/m63-openclaw-live-harness-adapter-closeout.md`, `docs/milestones/m64-hermes-long-running-agent-adapter-closeout.md`, and `docs/milestones/m65-production-policy-scenario-packs-closeout.md`.

Implementation note:

- M61 adds a default-deny, metadata-only sandbox contract for filesystem, shell, browser, email, network, and external-action surfaces.
- M62 adds deterministic approval-event and action-denial evidence derived from public-safe tool-call summaries.
- M63 adds a public-safe OpenClaw harness adapter smoke fixture that emits normalized transcript evidence without live runtime execution.
- M64 adds a public-safe Hermes-style long-running agent adapter fixture with saved transcripts, session-boundary metadata, and memory checks without live Hermes execution or private memory.
- M65 adds public-safe production-policy scenario packs for database changes, deployments, credentials, payments, external messaging, and customer data without live production-system access.
- The deterministic gate validates schemas, synthetic public-safe tool-call summaries, public-safe OpenClaw and Hermes-style fixtures, production-policy scenario fixtures, and saved-transcript replay only; it does not execute tools, agents, providers, local models, browser/email/network actions, shell commands, production-system actions, private memory reads, or external actions.

Milestones:

- M61 Sandboxed Tool Runtime Contract. Complete / review-ready.
- M62 Approval And Action Boundary Recorder. Complete / review-ready.
- M63 OpenClaw Live Harness Adapter. Complete / public-safe smoke review-ready.
- M64 Hermes Or Long-Running Agent Adapter. Complete / public-safe session review-ready.
- M65 Production-Policy Scenario Packs. Complete / public-safe scenario review-ready.

Success signal:

- The lab can run tool-capable agents in a disposable sandbox, record approvals and blocked actions, score selected assistant turns, and report policy behavior without touching real accounts or production systems.

### M66-M69: Private Runtime Evidence And Audit Mode

Support private production evidence while keeping it out of public fixtures and public rankings by default.

Status: active; M66-M67 complete / review-ready, M68-M69 planned. See `docs/milestones/m66-private-evidence-vault-closeout.md` and `docs/milestones/m67-redaction-promotion-pipeline-closeout.md`.

Implementation note:

- M66 adds a metadata-only private evidence vault contract with `schemas/private_evidence_manifest.schema.json`, `traces/external/private_evidence_vault_manifest.example.json`, `src/private_evidence_vault.py`, and public-safe boundary summaries.
- `private_evidence/` and `reports/private/` are ignored by Git by default.
- The committed M66 records are fake public-safe metadata only. The deterministic gate validates ignored-path controls, optional local encryption or OS-keychain storage-plan metadata, redaction-required promotion blocking, and private-audit report labels without ingesting private evidence or reading raw private data.
- M67 adds schema-backed promotion candidates, diffable redaction notes, and a synthetic public-safe promoted output validated without reading original private artifacts.

Milestones:

- M66 Private Evidence Vault. Complete / public-safe vault-boundary review-ready.
- M67 Redaction And Promotion Pipeline. Complete / public-safe promotion-pipeline review-ready.
- M68 Private Audit Reports.
- M69 Retention, Consent, And Access Controls.

Success signal:

- A user can ingest private runtime evidence locally, keep it encrypted or ignored by Git, generate local audit reports, and promote only reviewed public-safe derivatives into committed fixtures.

### M70-M73: Benchmark Governance And Statistical Confidence

Make rankings harder to game and easier to trust.

Status: planned.

Milestones:

- M70 Reviewer Protocol And Inter-Rater Checks.
- M71 Statistical Power And Rerun Policy.
- M72 Benchmark Versioning And Model Disclosure.
- M73 External Reproducibility Pack.

Success signal:

- Benchmark reports state sample sizes, uncertainty intervals, versioned case sets, model/provider metadata, rerun policy, reviewer agreement, and exact exclusions.

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

## Revised Target End State

```text
Public cases / Private scenarios / Production-like scenario packs
        |
        v
Live provider adapter / Agent runtime sandbox / Private evidence ingest
        |
        v
Raw outputs or traces stored outside Git by default
        |
        v
Normalization, redaction, review, and promotion
        |
        v
Public benchmark evidence or private audit evidence
        |
        v
Scoring, adjudication, calibration, ranking, and reports
```

The repository remains the measuring instrument. The agents and models are what it measures.

## Still Not In Scope

- Live provider APIs inside the deterministic local quality gate.
- Public rankings from private-only evidence.
- Production-policy proof claims that exceed the actual evidence.
- Uncontrolled browser, email, messaging, purchase, shell, network, or file-mutation actions.
- Credentials, tokens, private account data, private runtime memory, raw private logs, or unredacted private evidence in committed fixtures.
- OpenClaw-specific or Hermes-specific assumptions in core evaluator code unless isolated behind target adapters.
