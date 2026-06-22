---
name: agent-evals-release-reviewer
description: Use when reviewing Agent Behavior Evals Lab release claims, public benchmark reports, release bundles, rankings, or public-safe evidence boundaries.
---

# Agent Evals Release Reviewer

Use this workflow before publishing public reports or benchmark claims.

## Review Questions

- Does every report declare its evidence class?
- Are public rankings based only on eligible public benchmark evidence?
- Are manual samples and private evidence excluded unless explicitly promoted?
- Do reports state sample size, methodology, limitations, and exclusions?
- Are cloud rankings, production proof, and compliance proof avoided unless
  supported by the required evidence class?

## Public-Safe Check

Verify that no committed artifact contains secrets, credentials, private traces,
private memory, hidden prompts, private workspace paths, or customer data.

## Required Commands

```bash
python3 scripts/dev.py test
python3 scripts/dev.py check
```

Run release bundle and claim checklist validators when those artifacts change.
