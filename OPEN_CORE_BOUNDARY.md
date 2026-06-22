# Open-Core Boundary

Agent Behavior Evals Lab uses an open-core strategy.

The public repository is the trust-building evaluator core. The private/pro
repository is the commercial product layer.

## Public Repository

The public repository may contain:

- evaluator engine and deterministic scoring utilities;
- schemas, validators, ledgers, and report manifests;
- public-safe baseline cases and public benchmark cases;
- deterministic quality gates;
- public-safe sample traces and reports;
- basic CLI wrappers and reproducibility tooling;
- standards mappings that support traceability;
- public Codex skills for maintenance, case authoring, adapters, standards,
  and release review.

The public repository may claim scoped evaluator behavior and public-safe
benchmark results only when those claims are supported by committed evidence
classes and release checks.

## Private/Pro Repository

The private/pro repository should contain:

- customer audit workflows and intake;
- private trace ingestion and redaction operations;
- proprietary case packs and sector-specific rubrics;
- paid audit report templates;
- customer runtime adapters;
- hosted or on-prem dashboards;
- enterprise exports and branded deliverables;
- private Codex skills for customer delivery.

## Boundary Rules

- Do not commit customer data, secrets, private traces, or raw private logs to
  the public repository.
- Do not copy the public evaluator implementation into the private repo; the
  private repo should depend on the public core.
- Do not mix private evidence into public rankings unless it has been redacted,
  reviewed, normalized, and promoted into a public-safe evidence class.
- Do not make the evaluator itself a live autonomous agent. OpenClaw, Hermes,
  Codex, local models, and customer agents remain systems under test.

## Allowed Public Claims

The public repository can support:

- evaluator-health claims;
- local/open-weight benchmark claims when ledgers meet the ranking methodology;
- public-safe standards coverage claims;
- scoped, evidence-class-specific reports.

It must not claim:

- production compliance proof;
- cloud model rankings without cloud evidence;
- private audit reproducibility;
- live external-action safety without sandboxed evidence;
- customer-specific findings.
