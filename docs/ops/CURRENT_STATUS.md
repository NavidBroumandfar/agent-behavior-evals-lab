# Current Status

- Last updated: 2026-07-08
- Status: active
- GitHub repo: `https://github.com/NavidBroumandfar/agent-behavior-evals-lab.git`

## Current Objective

Maintain and position a local-first safety audit harness for AI agents before production.

## Current Phase Or Milestone

Published: GitHub Marketplace listing (Agent Behavior Safety Gate), corpus
2.1.0 (90 cases), AGB pattern registry 1.0/1.1 (50 patterns), sandbox fleet
evidence (8 agent configurations, reviewed), calibration study, public
leaderboard and demo repository.

## Recent Progress

- Mock-tool sandbox ("temptation lab") with structural, action-based scoring.
- Real-agent fleet evidence: raw tool loop, LangGraph, OpenAI Agents SDK,
  CrewAI configurations over local models.
- Marketplace listing live; badge output and `make reproduce` available.

## Current Blocker

Adoption evidence: external repositories using the gate in CI.

## Next Action

Publish launch write-ups; corpus expansion batches toward ~500 cases; rerun
fleet over the full 2.1.0 corpus.

## Guardrails

- Keep public examples generic and safe.
- Do not add private customer scenarios, proprietary packs, or paid workflow details.
- Keep this repo aligned with `agent-evals-pro` without duplicating private material.

## Review Note

Weekly review should check whether active work is increasing public clarity or adding internal complexity.
