# Evidence-First Live Benchmark Roadmap

Date: 2026-06-21

Status: Active evidence-first roadmap; M54-M67 complete / review-ready

This roadmap changes the lab from a deterministic evaluator scaffold into an evidence-producing benchmark program. The goal is to support live cloud-model runs, agent-runtime runs, model rankings, production-policy evidence, and private runtime evidence without confusing those categories or weakening credibility.

The current repository is a working measuring instrument. The next roadmap is about collecting enough real, reviewed, reproducible evidence for the measurements to matter.

## North Star

Agent Behavior Evals Lab should become a credible benchmark and audit harness for agent behavior under safety, approval, refusal, uncertainty, tool-use, and production-change policies.

It should support three evidence classes:

- Public benchmark evidence: public-safe cases, public-safe prompts, public provider/model outputs, reproducible run metadata, published aggregate rankings.
- Private production evidence: private runtime traces, private workspace context, private tool summaries, private reviewer notes, local-only audit reports.
- Promoted public evidence: private or live evidence that has been redacted, reviewed, normalized, and explicitly promoted into public-safe fixtures.

These classes must stay separate. A public leaderboard cannot depend on private evidence that other people cannot inspect. A private production audit can use private evidence, but it should not claim public benchmark reproducibility.

## Credibility Rules

- Do not claim mathematical proof of production policy compliance. Claim scoped evidence, confidence, residual risk, and known blind spots.
- Do not rank models until the benchmark has a frozen public case set, fixed run protocol, fixed scorer/adjudication process, and reproducible metadata.
- Do not mix private runtime evidence into public rankings unless it is redacted and promoted into public-safe fixtures.
- Do not run live providers in the deterministic local quality gate. Live runs must be opt-in, cost-bounded, logged, and replayable from saved outputs.
- Do not commit provider credentials, private logs, raw runtime memory, private workspace paths, or unredacted private evidence.
- Do not allow live tool actions in benchmark runs until a sandbox, approval recorder, and action-denial recorder are implemented.

## Zero-Cost Practical Sequence

The immediate path should prove the lab is functional without spending money or exposing personal agent data.

Order:

1. Local Ollama or OpenAI-compatible local model, text-only, public-safe cases only.
2. Manual saved-output samples from cloud chats the user already has access to, still public-safe and normalized before scoring.
3. Disposable local no-tool or mocked-tool agent harness around a local model.
4. OpenClaw in a disposable workspace with tools disabled, mocked, or sandboxed.
5. Hermes or memory-capable agents only after private evidence vault, redaction, retention, and promotion controls exist.

This sequence can produce real evidence without paid provider APIs. It should be labeled as a local/open-weight benchmark until paid or donated cloud-provider evidence is available.

## Execution Tracks

### Track A: Zero-Cost Local/Open-Weight Benchmark

This track proves the lab against real model outputs without cloud spend.

Milestones:

- M54: Local Benchmark Claim Charter And Evidence Classes
- M55: Public Local Benchmark Case Corpus V1
- M56: Ollama And Local OpenAI-Compatible Adapter Registry
- M57: Opt-In Local Text-Only Model Harness
- M58: Reproducible Local Run Ledger
- M59: Local Ranking Methodology
- M60: Local/Open-Weight Benchmark Report V1

Success signal: a maintainer can run a public-safe benchmark against local models, save normalized outputs, score and adjudicate them, and publish a transparent local/open-weight ranking with confidence intervals and limitations.

Cloud-model support remains a later extension of the same adapter and ledger architecture. It should not block the first proof.

### Track B: Agent Runtime And Tool-Boundary Benchmark

This track evaluates tool-capable agents without letting benchmark runs perform uncontrolled external actions.

Milestones:

- M61: Sandboxed Tool Runtime Contract
- M62: Approval And Action Boundary Recorder
- M63: OpenClaw Live Harness Adapter
- M64: Hermes Or Long-Running Agent Adapter
- M65: Production-Policy Scenario Packs

Success signal: the lab can run tool-capable agents in a disposable sandbox, record approvals and blocked actions, score selected assistant turns, and report policy behavior without touching real accounts or production systems.

### Track C: Private Runtime Evidence And Audit Mode

This track supports private production evidence while keeping it out of public fixtures and public rankings by default.

Milestones:

- M66: Private Evidence Vault
- M67: Redaction And Promotion Pipeline
- M68: Private Audit Reports
- M69: Retention, Consent, And Access Controls

Success signal: a user can ingest private runtime evidence locally, keep it encrypted or ignored by Git, generate local audit reports, and promote only reviewed public-safe derivatives into committed fixtures.

### Track D: Benchmark Governance And Statistical Confidence

This track makes rankings harder to game and easier to trust.

Milestones:

- M70: Reviewer Protocol And Inter-Rater Checks
- M71: Statistical Power And Rerun Policy
- M72: Benchmark Versioning And Model Disclosure
- M73: External Reproducibility Pack

Success signal: benchmark reports state sample sizes, uncertainty intervals, versioned case sets, model/provider metadata, rerun policy, reviewer agreement, and exact exclusions.

## Milestone Detail

### M54: Local Benchmark Claim Charter And Evidence Classes

Define what the local-first benchmark is allowed to claim before it has cloud-provider evidence.

Status: complete / review-ready. See `docs/milestones/m54-local-benchmark-claim-charter-closeout.md`.

Implementation note:

- M54 adds `benchmarks/evidence_class_charter.json`, `schemas/benchmark_claim_charter.schema.json`, and `src/validate_benchmark_claim_charter.py`.
- The charter defines seven evidence classes and machine-checked claim boundaries for public rankings, private audit evidence, local/open-weight results, cloud-provider results, manual samples, and unsupported claims.
- No live provider, local model, Ollama, Hermes, OpenClaw, private evidence, runtime harness, credential, network, or external action execution is introduced.

Deliverables:

- Evidence-class schema for local public benchmark, manual public sample, cloud public benchmark, private audit, and promoted public evidence.
- Claim taxonomy: evaluator-health, local/open-weight benchmark, manual public sample, cloud benchmark, private audit, production-policy evidence, and unsupported claims.
- Report language rules that prevent private evidence from contaminating public leaderboard claims.
- Rules for labeling Ollama/local-model results separately from hosted cloud-model results.
- Updated roadmap and wiki docs.

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

- M55 adds `evals/benchmarks/local_public_v1/cases.jsonl` and `evals/benchmarks/local_public_v1/manifest.json`.
- The frozen corpus has 210 public-safe cases, 30 per risk area, with deterministic smoke, standard, and extended splits.
- `src/validate_local_benchmark_corpus.py` checks schema, coverage, split membership, source paths, hash consistency, and public-safe assertions.
- No local model, Ollama, provider, runtime harness, private evidence, credential, network, or external action execution is introduced.

Deliverables:

- At least 200 public-safe cases across safe tasks, approval-gated tasks, refusal-required tasks, uncertainty, tool-use claims, privacy, and production-change requests.
- Case-set versioning with frozen benchmark splits.
- Difficulty tags, policy references, and expected behavior notes.
- Seeded sample selection for smoke, standard, and extended runs.

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
- The registry declares Ollama, local OpenAI-compatible, and manual saved-output adapter classes for future `local_public_v1` runs.
- Future live-local model calls require `--live-local` plus `AGENT_EVALS_ENABLE_LIVE_LOCAL`.
- No local model, Ollama, provider, runtime harness, private evidence, credential, network, or external action execution is introduced.

Deliverables:

- Adapter interface for Ollama, local OpenAI-compatible servers, and manual saved-output adapters.
- Registry metadata for model name, runtime, endpoint class, temperature, context window, tool availability, and estimated local cost.
- Dry-run and validation mode that never calls a local model.
- Explicit optional extension points for paid provider adapters later.

Acceptance criteria:

- No credential is required for the local Ollama path.
- Local model calls require an explicit `--live-local` or equivalent flag.
- Local adapters produce normalized saved-output records.
- Unit tests use fakes only.

### M57: Opt-In Local Text-Only Model Harness

Run local models against public-safe prompts with tools disabled.

Status: complete / review-ready. See `docs/milestones/m57-opt-in-local-text-only-model-harness-closeout.md`.

Implementation note:

- M57 adds `scripts/live_local.py`, `src/live_local_harness.py`, `schemas/live_local_run.schema.json`, `src/validate_live_local_run.py`, and `traces/external/live_local_run_plan.example.json`.
- The harness supports Ollama and local OpenAI-compatible text-only endpoints declared in the M56 registry.
- Live execution is opt-in only and requires `--live-local` plus `AGENT_EVALS_ENABLE_LIVE_LOCAL`.
- The deterministic quality gate validates the dry-run plan, schema, fake-client tests, and reviewed-output provenance path only. It does not call local models or put live execution into `scripts/dev.py check`.

Deliverables:

- `scripts/live_local.py` or equivalent command for local text-only runs.
- Timeout policy, model availability checks, retry policy, and run abort controls.
- Saved raw outputs under ignored local paths.
- Reviewed normalized outputs suitable for existing scoring and adjudication.

Acceptance criteria:

- The deterministic gate does not call local models.
- A local run can be reproduced from its saved normalized outputs.
- Run metadata captures runtime, model, parameters, timestamp, case-set version, and prompt template version.
- Failed or partial local runs are clearly marked and excluded from rankings unless policy allows them.

### M58: Reproducible Local Run Ledger

Make local model evidence auditable.

Status: complete / review-ready. See `docs/milestones/m58-reproducible-local-run-ledger-closeout.md`.

Implementation note:

- M58 adds `schemas/local_run_ledger.schema.json`, `src/local_run_ledger.py`, `src/validate_local_run_ledger.py`, and `traces/external/local_run_ledger.example.json`.
- The ledger pins SHA-256 hashes for the `local_public_v1` case file and manifest, M56 registry, selected adapter version, M57 prompt template, normalized output file, scored trace file, deterministic scorer artifact, and public-safe run metadata.
- The committed example uses fake public-safe dry-run outputs and is ranking-ineligible. It proves the audit path without local model execution.
- The deterministic gate regenerates and validates the public-safe example only. It does not call Ollama, local OpenAI-compatible servers, providers, agents, browser/email tools, shell/file actions as a system under test, gated LLM review, or external actions.

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

### M61: Sandboxed Tool Runtime Contract

Define a runtime harness for tool-capable agents.

Status: complete / review-ready. See `docs/milestones/m61-sandboxed-tool-runtime-contract-closeout.md`.

Implementation note:

- M61 adds `schemas/tool_sandbox_contract.schema.json`, `schemas/tool_call_summary.schema.json`, `traces/external/tool_sandbox_contract.example.json`, `traces/external/tool_call_summaries.example.jsonl`, and `src/validate_tool_sandbox_contract.py`.
- The contract is default-deny and metadata-only across filesystem, shell, browser, email, network, and external-action surfaces.
- The committed tool-call summaries are synthetic public-safe examples that record blocked actions and an approval request without executing tools or exposing raw private logs.
- The deterministic gate validates schema, examples, and safety semantics only. It does not launch agents, execute tools, call local models or providers, use browser/email/network tools, mutate files as a system under test, or perform external actions.

Deliverables:

- Tool sandbox contract for filesystem, shell, browser, email, network, and external actions.
- Default-deny action policy.
- Disposable workspace setup.
- Tool-call summary schema.

Acceptance criteria:

- No real external action is possible in the default sandbox.
- The harness can record attempted actions, blocked actions, and approval requests.
- Tool summaries can be scored without raw private logs.

### M62: Approval And Action Boundary Recorder

Record whether an agent asks before consequential actions.

Status: complete / review-ready. See `docs/milestones/m62-approval-action-boundary-recorder-closeout.md`.

Implementation note:

- M62 adds `schemas/approval_event.schema.json`, `schemas/action_denial.schema.json`, `traces/external/action_boundary_tool_summaries.example.jsonl`, generated public-safe `traces/external/approval_events.example.jsonl` and `traces/external/action_denials.example.jsonl`, and `src/action_boundary_recorder.py`.
- The converter turns M61-compatible public-safe tool-call summaries into approval-event and action-denial records covering missing approval, vague approval, denied action, and fake completion claims.
- The deterministic gate validates and regenerates only synthetic public-safe evidence. It does not launch agents, execute tools, call local models or providers, use browser/email/network tools, mutate files as a system under test, or perform external actions.

Deliverables:

- Approval-event schema.
- Action-denial schema.
- Runtime transcript-to-evidence converter.
- Tests for missing approval, vague approval, denied action, and fake completion claims.

Acceptance criteria:

- Reports can distinguish "asked for approval", "received approval", "attempted action", and "claimed completion".
- No real action is needed to evaluate approval behavior.

### M63: OpenClaw Live Harness Adapter

Evaluate OpenClaw as a system under test through the sandbox contract.

Status: complete / public-safe smoke review-ready. See `docs/milestones/m63-openclaw-live-harness-adapter-closeout.md`.

Implementation note:

- M63 adds `schemas/openclaw_harness_adapter.schema.json`, `traces/external/openclaw_harness_adapter_plan.example.json`, and `src/openclaw_harness_adapter.py`.
- The adapter emits a public-safe smoke saved-transcript fixture and M61-compatible tool summary, then scores the transcript through the existing saved-transcript replay path.
- The deterministic gate validates the adapter plan, generates public-safe smoke artifacts, and replays the saved transcript. It does not launch OpenClaw, execute tools, call local models or providers, use browser/email/network tools, mutate files as a system under test, or perform external actions.

Deliverables:

- OpenClaw adapter that emits normalized transcript evidence.
- Public-safe smoke run.
- Local-only raw runtime output handling.
- Promotion path into public-safe fixtures.

Acceptance criteria:

- OpenClaw runs are opt-in and outside the deterministic gate.
- Tool actions are disabled, mocked, or sandboxed.
- Reports label OpenClaw as a target, not as the evaluator.

### M64: Hermes Or Long-Running Agent Adapter

Evaluate memory and cross-session behavior.

Status: complete / public-safe session review-ready. See `docs/milestones/m64-hermes-long-running-agent-adapter-closeout.md`.

Implementation note:

- M64 adds `schemas/long_running_agent_adapter.schema.json`, `schemas/session_boundary_metadata.schema.json`, `schemas/memory_persistence_check.schema.json`, `traces/external/long_running_agent_adapter_plan.example.json`, and `src/long_running_agent_adapter.py`.
- The adapter emits public-safe saved transcripts, session-boundary metadata, memory disclosure and persistence checks, a scored trace, and a reader-facing report for a Hermes-style long-running agent target.
- The deterministic gate validates generated public-safe derivatives only. It does not launch Hermes, read private memory, execute tools, call local models or providers, use browser/email/network tools, mutate files as a system under test, or perform external actions.

Deliverables:

- Adapter for a long-running or memory-capable agent target.
- Session-boundary metadata.
- Memory disclosure and persistence checks.
- Public-safe saved transcripts.

Acceptance criteria:

- Private memory is never committed.
- Public-safe derivatives can show whether the agent correctly handles continuity and uncertainty.

### M65: Production-Policy Scenario Packs

Represent production-risk policies without touching production systems.

Status: complete / public-safe scenario review-ready. See `docs/milestones/m65-production-policy-scenario-packs-closeout.md`.

Implementation note:

- M65 adds `schemas/production_policy_scenario_pack.schema.json`, `schemas/production_policy_scenario_check.schema.json`, `traces/external/production_policy_scenario_pack.example.json`, and `src/production_policy_scenarios.py`.
- The pack covers database changes, deployments, credentials, payments, external messaging, and customer data with synthetic public-safe production-state metadata.
- The deterministic gate validates generated public-safe derivatives, replays saved transcripts, and validates public-safe adjudications only. It does not access production systems, credentials, private customer data, browser/email/network tools, providers, local models, or external actions.

Deliverables:

- Scenario packs for database changes, deployments, credentials, payments, external messaging, and customer data.
- Mocked or synthetic production-state metadata.
- Expected approval and refusal behavior for each scenario.

Acceptance criteria:

- No real production accounts or systems are used.
- The lab can produce scoped evidence about policy behavior under production-like prompts.
- Reports state that this is scenario evidence, not production proof.

### M66: Private Evidence Vault

Define local private evidence ingestion boundaries.

Status: complete / public-safe vault-boundary review-ready. See `docs/milestones/m66-private-evidence-vault-closeout.md`.

Implementation note:

- M66 adds `schemas/private_evidence_manifest.schema.json`, `traces/external/private_evidence_vault_manifest.example.json`, `src/private_evidence_vault.py`, and public-safe boundary summaries at `reports/comparisons/private_evidence_vault_summary.json` and `reports/comparisons/private_evidence_vault_summary.md`.
- The committed manifest uses fake public-safe metadata only. It defines ignored local storage roots, optional local encryption or OS-keychain storage-plan metadata, redaction-required promotion blocking, and private-audit report labels.
- `private_evidence/` and `reports/private/` are ignored by Git by default.
- The deterministic gate validates schema, fake metadata, ignored-path controls, promotion blocking, and report labels only. It does not ingest private evidence, read raw private data, handle credentials or encryption keys, execute agents, call providers, use browser/email/network tools, or perform external actions.

Deliverables:

- Ignored private evidence directory.
- Optional local encryption or OS-keychain backed storage.
- Private evidence manifest schema.
- Private run validation that never writes private data to committed fixtures.

Acceptance criteria:

- Private evidence is excluded from Git by default.
- Commands refuse to promote private records without explicit redaction metadata.
- Reports generated from private evidence are marked private audit reports.

### M67: Redaction And Promotion Pipeline

Turn selected private evidence into public-safe fixtures.

Status: complete / public-safe promotion-pipeline review-ready. See `docs/milestones/m67-redaction-promotion-pipeline-closeout.md`.

Implementation note:

- M67 adds `schemas/promotion_candidate.schema.json`, `schemas/redaction_note.schema.json`, `traces/external/redaction_promotion_candidates.example.json`, `traces/external/redaction_notes.example.jsonl`, `traces/external/promoted_private_evidence_outputs.example.jsonl`, and `src/redaction_promotion_pipeline.py`.
- The committed example uses fake M66 private-vault metadata and a synthetic public-safe promoted derivative only.
- Promotion requires redaction notes, reviewer signoff, public-safety assertions, and a public-safe adapter-output derivative.
- The deterministic gate validates public-safe derivatives only. It does not ingest private evidence, read raw private artifacts, handle credentials, run agents, call providers, or perform external actions.

Deliverables:

- Redaction checklist.
- Promotion candidate schema.
- Diffable redaction notes.
- Validator for public-safe promoted outputs.

Acceptance criteria:

- Promotion requires reviewer sign-off.
- The original private artifact remains local-only.
- The promoted public fixture contains no secrets, account data, private paths, hidden prompts, or raw runtime logs.

### M68: Private Audit Reports

Generate reports from private evidence without publishing it.

Status: complete / public-safe private-report-boundary review-ready. See `docs/milestones/m68-private-audit-reports-closeout.md`.

Implementation note:

- M68 adds `schemas/private_audit_report.schema.json`, `traces/external/private_audit_report_metadata.example.json`, and `src/private_audit_report.py`.
- The committed example uses fake M66 private-vault metadata only.
- Local private audit JSON and Markdown default to ignored `reports/private/*.local.*` paths and are labeled `private_audit_report`.
- Committed summaries remain aggregate-only and public-safe under `reports/comparisons/`.

Deliverables:

- Local-only private audit JSON and Markdown.
- Private-vs-public evidence separation in report metadata.
- Optional aggregate-only export.

Acceptance criteria:

- Private audit reports are ignored by Git unless explicitly exported.
- Reports can support internal decisions without becoming public leaderboard evidence.
- The deterministic gate does not read raw private evidence, handle credentials, run live systems, perform external actions, or run gated LLM review.

### M69: Retention, Consent, And Access Controls

Make private evidence handling operationally safe.

Status: complete / public-safe retention-access-boundary review-ready. See `docs/milestones/m69-retention-consent-access-controls-closeout.md`.

Implementation note:

- M69 adds `schemas/retention_consent_access.schema.json`, `traces/external/retention_consent_access_metadata.example.json`, and `src/retention_consent_access.py`.
- The committed example links to the M66 private evidence vault and M68 private audit report metadata using fake public-safe metadata only.
- Public summaries at `reports/comparisons/retention_consent_access_summary.json` and `reports/comparisons/retention_consent_access_summary.md` report aggregate retention class, consent/authorization status, access boundary, deletion/export boundary, and fake evidence-age signals.
- The deterministic gate validates deletion/export boundaries as metadata only; it does not execute deletion, export private artifacts, ingest private evidence, or read raw private logs.

Deliverables:

- Retention policy.
- Consent and authorization checklist.
- Access-control notes for local private stores.
- Deletion and export boundaries.

Acceptance criteria:

- Private evidence deletion is bounded to ignored local private roots and is not executed by the deterministic gate.
- Reports identify fake evidence age, retention class, and access boundary using aggregate public-safe metadata only.

### M70-M76: Real Model Proof Roadmap

Move from dry-run evaluator health toward the next controlled, opt-in local
model proof point.

Status: complete / proof-path infrastructure ready. See
`docs/milestones/m70-m76-real-model-proof-roadmap-closeout.md`.

Deliverables:

- `schemas/live_local_review_summary.schema.json`,
  `traces/external/live_local_review_summary.example.json`, and
  `src/live_local_review_summary.py` for reviewer protocol, deterministic
  sampling, unresolved-review blockers, and inter-rater reporting.
- Reviewed live-local ledger validation that requires review summaries to match
  normalized output record IDs, scored-trace pass results, and severity.
- Real metric aggregation in `src/local_benchmark_report.py` for reviewed
  scored traces: severity-weighted effective pass rate, heuristic pass rate,
  deterministic bootstrap CI, review counts, unresolved review count,
  abstention count, exclusions, and ledger entry ID.
- `schemas/hosted_provider_batch.schema.json` and
  `src/hosted_provider_batch.py` for a later hosted OpenAI Batch path as a
  separate metadata-only evidence class.
- `schemas/real_model_proof_runbook.schema.json` and
  `src/real_model_proof_runbook.py` for the CLI/report operator surface.

Acceptance criteria:

- The current committed gate remains deterministic and non-live.
- No ranking publishes from smoke-only, dry-run, partial, unresolved-review,
  raw-output, private, cloud-labelled, or hosted-provider evidence.
- After M80, the first real local proof requires reviewed extended
  `local_public_v1` ledgers for `llama3.2:latest` and the selected second
  target, `mistral:latest`; `gemma4:latest` is deferred after the M77 swapout
  blocker.
- Hosted provider evidence is separate from local/open-weight rankings until a
  future methodology explicitly allows comparison.

### M77-M86: Live-Local Publication Path

Turn the M77 technical proof into publishable local/open-weight evidence only
through explicit review, ledger, second-target, reproducibility, and claim gates.

Status: complete / M86 claim-review gate published after the M83
local-open-weight ranking, M84 reproducibility packet, and M85 runtime
stability metadata.

Milestone sequence:

- M77 executes a laptop-safe live-local technical proof and records public-safe
  blockers without publishing rankings.
- M78 reviews and normalizes the 210 `llama3.2:latest` M77 raw records.
  Status: complete as a local ignored reviewed candidate; no scored trace or
  ledger is committed yet.
- M79 scores the reviewed `llama3.2:latest` evidence and builds the first
  reviewed live-local ledger.
  Status at M79 closeout: complete with one eligible reviewed ledger; no
  ranking was published until the second ledger arrived.
- M80 documents the second local target decision after the M77
  `gemma4:latest` swapout blocker.
  Status: complete; `mistral:latest` is selected for the current publication
  path, and `gemma4:latest` remains deferred after the M85 stability profile
  until a separate explicit retry decision exists.
- M81 executes the selected second target over the extended split if the
  operator safety profile allows it.
  Status: complete; `mistral:latest` produced 210 / 210 extended raw records
  under ignored local-only paths after explicit live-local opt-in.
- M82 reviews, scores, and ledgers the second target.
  Status: complete; `mistral:latest` has a validated reviewed live-local
  ledger with 210 reviewed records.
- M83 regenerates the local/open-weight benchmark report and publishes rankings
  only if two eligible reviewed live-local ledgers pass.
  Status: complete; `ranking_claim_allowed` is `true` for the local/open-weight
  report with `llama3.2:latest` and `mistral:latest`.
- M84 adds a public-safe reproducibility packet with hashes, model identifiers,
  harness/scorer/adapter versions, command templates, validation commands,
  source artifact inventory, and claim boundaries but no raw outputs.
  Status: complete; see
  `docs/milestones/m84-public-safe-reproducibility-packet-closeout.md`.
- M85 adds runtime stability/resource metadata so heavier models have explicit
  stop criteria.
  Status: complete; see
  `docs/milestones/m85-runtime-stability-resource-profile-closeout.md`.
- M86 adds a claim-review and release checklist before any result is described
  as publishable, production-relevant, externally reproducible, or comparable to
  hosted-provider evidence.
  Status: complete; see
  `docs/milestones/m86-claim-review-release-checklist-closeout.md`.

Acceptance criteria:

- No raw outputs are committed.
- Reviewed candidates remain ignored until an explicit promotion or ledger
  artifact decision is made; M79 makes that decision only for the public-safe
  `llama3.2:latest` derivative artifacts needed by the first ledger.
- The deterministic gate remains non-live.
- A ranking is published only after two reviewed extended local targets satisfy
  review, scoring, ledger, sample-size, and safety gates.

## Revised End State

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

The lab becomes valuable when it can show enough real evidence to support scoped claims:

- Public benchmark claim: "On benchmark version X, model Y had these public-safe scored/adjudicated outcomes with these limitations."
- Private audit claim: "On private runtime evidence set Z, this agent showed these policy risks under this internal scenario set."
- Unsupported claim: "This proves the model is safe in production."

The roadmap should optimize for the first two and refuse the third.
