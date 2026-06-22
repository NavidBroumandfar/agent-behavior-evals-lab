---
name: agent-evals-case-author
description: Use when adding or reviewing Agent Behavior Evals Lab public benchmark cases, baseline cases, risk areas, policy refs, severities, and expected behaviors.
---

# Agent Evals Case Author

Use this workflow when authoring public cases.

## Case Requirements

Each public case needs:

- stable case ID;
- category;
- risk area when part of a benchmark corpus;
- user prompt;
- expected behavior;
- severity;
- policy references;
- expected failure modes;
- scoring notes;
- public-safe content only.

## Public-Safe Rule

Do not include real secrets, private data, customer logs, private workspace
paths, live credentials, or unredacted private evidence.

## Categories

Use existing category semantics:

- `safe_direct_response`
- `approval_gated`
- `refusal_required`
- `uncertainty_handling`

## Standards Mapping

When standards coverage is enabled, update the standards mapping so every new
public case maps to at least one standards row. The mapping supports scoped
case groups; do not duplicate large rows unless a case needs special coverage.

## Validation

Run the relevant case validator and then the full deterministic gate:

```bash
python3 scripts/dev.py check
```
