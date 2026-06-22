# Product Positioning

## Positioning

Agent Behavior Evals Lab is a local-first safety audit harness for AI agents
before production.

It helps teams answer:

> Can this assistant or agent be trusted around tools, files, customer data,
> approvals, and production workflows?

## Core Product Idea

The lab is the evaluator. OpenClaw, Hermes, Codex, local models, hosted models,
and customer agents are systems under test.

The evaluator should remain deterministic, inspectable, and claim-bounded by
default. Live model runs, private evidence, and tool-capable agent execution
belong in explicit opt-in workflows that write reviewed, reproducible evidence.

## Target Users

- AI teams preparing agents for internal or external deployment.
- Security and governance teams reviewing tool-capable assistants.
- Engineering teams comparing agent behavior across versions.
- Consultants or agencies delivering agent readiness audits.

## Differentiation

This project is not another generic LLM eval runner. It focuses on:

- approval gates before consequential action;
- refusal and safe redirection;
- uncertainty handling;
- fake tool-use and fake completion claims;
- private/public evidence separation;
- reproducible local ledgers and claim boundaries.

## Commercial Path

The public repository should build trust through a useful open-source core. The
commercial layer should monetize:

- private customer audits;
- proprietary case packs;
- private runtime adapters;
- professional report exports;
- hosted or on-prem dashboards;
- sector-specific readiness workflows.

## Claim Boundary

Reports should describe scoped evidence, confidence, limitations, and residual
risk. They should not claim mathematical proof of safety, production compliance,
or broad model quality unless the required evidence class supports that claim.
