# Evidence-First Live Benchmark Roadmap

Date: 2026-06-21

Status: Proposed post-M53 roadmap

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

## Execution Tracks

### Track A: Public Live Cloud Model Benchmark

This track makes the lab a public benchmark for cloud models and hosted assistants.

Milestones:

- M54: Benchmark Claim Charter And Evidence Classes
- M55: Public Benchmark Case Corpus V1
- M56: Live Provider Adapter Registry
- M57: Opt-In Live Text-Only Provider Harness
- M58: Reproducible Live Run Ledger
- M59: Public Ranking Methodology
- M60: Public Benchmark Report V1

Success signal: a maintainer can run a public-safe benchmark against configured cloud models, save normalized outputs, score and adjudicate them, and publish a transparent ranking with confidence intervals and limitations.

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

### M54: Benchmark Claim Charter And Evidence Classes

Define what the benchmark is allowed to claim.

Deliverables:

- Evidence-class schema for public benchmark, private audit, and promoted public evidence.
- Claim taxonomy: evaluator-health, public benchmark, private audit, production-policy evidence, and unsupported claims.
- Report language rules that prevent private evidence from contaminating public leaderboard claims.
- Updated roadmap and wiki docs.

Acceptance criteria:

- Every report declares its evidence class.
- Public rankings can only use public benchmark evidence.
- Private audit reports can use private evidence but must not claim public reproducibility.
- The local deterministic gate remains credential-free.

### M55: Public Benchmark Case Corpus V1

Build a larger public-safe case corpus designed for live model comparison.

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

### M56: Live Provider Adapter Registry

Add opt-in provider adapters without making providers part of the local quality gate.

Deliverables:

- Provider adapter interface for OpenAI-compatible APIs, Anthropic-compatible APIs, local OpenAI-compatible servers, and manual adapters.
- Registry metadata for model name, provider, endpoint class, temperature, tool availability, and cost estimate.
- Environment-variable based credential lookup.
- Dry-run and validation mode that never calls a provider.

Acceptance criteria:

- No credential is committed or printed.
- Live calls require an explicit `--live` flag and an enable environment variable.
- Provider adapters produce normalized saved-output records.
- Unit tests use fakes only.

### M57: Opt-In Live Text-Only Provider Harness

Run live cloud models against public-safe prompts with tools disabled.

Deliverables:

- `scripts/live.py` or equivalent command for live text-only runs.
- Cost ceilings, rate limits, retry policy, timeout policy, and run abort controls.
- Saved raw outputs under ignored local paths.
- Reviewed normalized outputs suitable for existing scoring and adjudication.

Acceptance criteria:

- The deterministic gate does not call providers.
- A live run can be reproduced from its saved normalized outputs.
- Run metadata captures provider, model, parameters, timestamp, case-set version, and prompt template version.
- Failed or partial live runs are clearly marked and excluded from rankings unless policy allows them.

### M58: Reproducible Live Run Ledger

Make live evidence auditable.

Deliverables:

- Run ledger schema for live provider runs.
- Hashes for case set, prompt template, adapter version, normalized output file, and scorer version.
- Public-safe run manifest for published benchmark runs.
- Validation command for run ledgers.

Acceptance criteria:

- A report can trace every scored live output to a run ledger entry.
- Ledger entries do not expose secrets or private prompts.
- Re-running from saved outputs does not require provider credentials.

### M59: Public Ranking Methodology

Define how models are ranked without overclaiming.

Deliverables:

- Ranking metric definitions.
- Confidence intervals or bootstrap estimates.
- Tie policy, abstention policy, partial-run policy, and severity weighting.
- Required human-review sampling for high-risk cases.

Acceptance criteria:

- Rankings include sample size, uncertainty, exclusions, and benchmark version.
- Rankings distinguish heuristic score, adjudicated score, and unresolved review count.
- A model cannot be ranked from private-only evidence.

### M60: Public Benchmark Report V1

Publish the first public-safe live cloud model benchmark report.

Deliverables:

- Live public benchmark JSON snapshot.
- Markdown benchmark report.
- Model ranking table.
- Methodology and limitations section.
- Reproduction instructions from saved public-safe outputs.

Acceptance criteria:

- At least two real provider/model targets are included.
- All ranked evidence is public-safe and traceable.
- The report avoids production-policy proof claims.
- The full deterministic local gate passes without provider credentials.

### M61: Sandboxed Tool Runtime Contract

Define a runtime harness for tool-capable agents.

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

Deliverables:

- Scenario packs for database changes, deployments, credentials, payments, external messaging, and customer data.
- Mocked or synthetic production-state metadata.
- Expected approval and refusal behavior for each scenario.

Acceptance criteria:

- No real production accounts or systems are used.
- The lab can produce scoped evidence about policy behavior under production-like prompts.
- Reports state that this is scenario evidence, not production proof.

### M66: Private Evidence Vault

Support local private evidence ingestion.

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

Deliverables:

- Local-only private audit JSON and Markdown.
- Private-vs-public evidence separation in report metadata.
- Optional aggregate-only export.

Acceptance criteria:

- Private audit reports are ignored by Git unless explicitly exported.
- Reports can support internal decisions without becoming public leaderboard evidence.

### M69: Retention, Consent, And Access Controls

Make private evidence handling operationally safe.

Deliverables:

- Retention policy.
- Consent and authorization checklist.
- Access-control notes for local private stores.
- Deletion and export commands.

Acceptance criteria:

- Private evidence can be deleted cleanly.
- Reports can identify evidence age, retention class, and access boundary.

### M70: Reviewer Protocol And Inter-Rater Checks

Make human review more credible.

Deliverables:

- Reviewer rubric v1.
- Double-review sampling policy.
- Inter-rater agreement report.
- Escalation path for unresolved cases.

Acceptance criteria:

- High-risk benchmark cases have reviewer sampling.
- Reports show unresolved and disagreement rates.

### M71: Statistical Power And Rerun Policy

Avoid unstable rankings.

Deliverables:

- Minimum sample-size policy.
- Bootstrap or interval estimates.
- Rerun cadence and provider-drift policy.
- Sensitivity report for severity weighting.

Acceptance criteria:

- Rankings are not published when sample size is too small.
- Reports show uncertainty and drift caveats.

### M72: Benchmark Versioning And Model Disclosure

Make public rankings reproducible.

Deliverables:

- Benchmark version identifiers.
- Model/provider disclosure schema.
- Prompt-template and adapter-version hashes.
- Public benchmark changelog.

Acceptance criteria:

- A leaderboard row states benchmark version, model identity, provider settings, run date, and exclusions.

### M73: External Reproducibility Pack

Allow outside users to inspect or reproduce public-safe results.

Deliverables:

- Public-safe benchmark bundle.
- Reproduction script from saved outputs.
- Report-generation instructions.
- Fixture and run-ledger validation instructions.

Acceptance criteria:

- A third party can regenerate public benchmark reports without provider credentials.
- Live reruns are optional and explicitly cost-bearing.

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
