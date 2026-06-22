---
name: agent-evals-standards-mapper
description: Use when mapping Agent Behavior Evals Lab cases or risk areas to OWASP LLM, OWASP Agentic, NIST AI RMF, or MITRE ATLAS standards coverage.
---

# Agent Evals Standards Mapper

Use this workflow to maintain standards coverage.

## Goal

Standards mappings support traceability. They are not compliance certification.

## Mapping Rules

- Map every public baseline and `local_public_v1` case to at least one standards
  row.
- Prefer grouped mappings by risk area or category when coverage is shared.
- Use case-specific mappings only for exceptions.
- Validate that every standard ID exists in a committed catalog.
- Keep report language claim-bounded: "coverage" does not mean "compliance."

## Standards

Current public catalogs:

- OWASP LLM Top 10
- OWASP Agentic risks
- NIST AI RMF
- MITRE ATLAS

## Validation

Run:

```bash
python3 src/standards_coverage.py
python3 scripts/dev.py check
```
