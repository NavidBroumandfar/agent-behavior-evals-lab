# Public Repository Boundary

Agent Behavior Evals Lab is the public evaluator core. This repository should
build trust through inspectable tests, fixtures, schemas, reports, and release
checks.

## Public Repository Scope

This repository may contain:

- evaluator engine and deterministic scoring utilities;
- schemas, validators, ledgers, and report manifests;
- public-safe baseline cases and public benchmark cases;
- deterministic quality gates;
- public-safe sample traces and reports;
- basic CLI wrappers and reproducibility tooling;
- standards mappings that support traceability;
- public maintainer playbooks for cases, adapters, standards, and release
  review.

The repository may claim scoped evaluator behavior and public-safe benchmark
results only when those claims are supported by committed evidence classes and
release checks.

## Out Of Scope For This Repository

Keep these out of the public repository:

- buyer, sales, outreach, pricing, and pilot trackers;
- customer audit workflows, intake, and delivery templates;
- private trace ingestion and redaction operations;
- customer-specific findings, reports, and remediation plans;
- proprietary case packs and sector-specific rubrics;
- branded deliverables, dashboards, and enterprise exports;
- private delivery playbooks or customer-facing process notes.

## Boundary Rules

- Do not commit customer data, secrets, private traces, raw private logs, buyer
  lists, discovery notes, pricing notes, or customer-specific findings.
- Do not mix private evidence into public rankings unless it has been redacted,
  reviewed, normalized, and promoted into a public-safe evidence class.
- Do not make the evaluator itself a live autonomous agent. Agent runtimes,
  local models, hosted models, and CLI agents remain systems under test.

## Allowed Public Claims

This repository can support:

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
