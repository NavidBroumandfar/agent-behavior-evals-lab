# Milestone 65 - Production-Policy Scenario Packs

Date: 2026-06-21

Status: Complete / public-safe scenario review-ready

Milestone 65 adds schema-backed production-policy scenario packs for
production-like prompts without touching production systems. The committed pack
uses synthetic public-safe metadata and saved transcripts to exercise database
changes, deployments, credentials, payments, external messaging, and customer
data boundaries.

M65 does not add production accounts, production system access, provider calls,
local model calls, browser/email actions, messaging, purchases, shell execution,
filesystem mutation as a system under test, network collection, credentials,
private customer data, private runtime logs, gated LLM review, or live execution
inside `scripts/dev.py check` or `scripts/check_all.py`.

## Completed Slices

- M65.1 Added `schemas/production_policy_scenario_pack.schema.json`.
- M65.2 Added `schemas/production_policy_scenario_check.schema.json`.
- M65.3 Added `traces/external/production_policy_scenario_pack.example.json`.
- M65.4 Added `src/production_policy_scenarios.py` to validate the pack and emit public-safe derivatives.
- M65.5 Added generated saved transcripts at `traces/external/production_policy_scenario_transcripts.example.jsonl`.
- M65.6 Added generated scenario checks at `traces/external/production_policy_scenario_checks.example.jsonl`.
- M65.7 Replayed the generated transcripts into `traces/scored/production_policy_scenario_eval.jsonl`.
- M65.8 Added `reports/comparisons/production_policy_scenario_report.md`.
- M65.9 Added public-safe adjudications at `traces/external/production_policy_scenario_adjudications.example.jsonl`.
- M65.10 Wired fixture, replay, adjudication, manifest, schema coverage, report manifest, release-note, and compile coverage into the deterministic gate.

## Key Artifacts

Adapter-style scenario evidence:

- `traces/external/production_policy_scenario_pack.example.json`
- `traces/external/production_policy_scenario_transcripts.example.jsonl`
- `traces/external/production_policy_scenario_checks.example.jsonl`
- `traces/scored/production_policy_scenario_eval.jsonl`
- `reports/comparisons/production_policy_scenario_report.md`
- `traces/external/production_policy_scenario_adjudications.example.jsonl`
- `schemas/production_policy_scenario_pack.schema.json`
- `schemas/production_policy_scenario_check.schema.json`
- `src/production_policy_scenarios.py`
- `tests/test_production_policy_scenarios.py`

Documentation:

- `docs/wiki/concepts/production_policy_scenario_packs.md`
- `docs/wiki/reference/schema_validation_coverage.md`
- `docs/live_benchmark_roadmap.md`
- `docs/roadmap.md`

## Scenario Outcome

- Scenario families: 6
- Normalized transcript records: 6
- Scenario check records: 6
- Scored trace records: 6
- Replay pass count: 6
- Reviewer adjudications: 6
- Production system access in quality gate: false
- External actions in quality gate: false
- Scenario evidence is production proof: false

The fixture is synthetic and public-safe. It proves the scenario-pack evidence
path and deterministic reporting contract, not production compliance.

## Evidence Boundary

M65 can show whether selected assistant text handles production-like prompts
with approval gates, scope/risk disclosure, no execution, and no completion
claims. It cannot prove live production behavior, production policy compliance,
account safety, customer-data handling in real systems, or leaderboard quality.

## Quality Gate

From the repository root:

```bash
python3 scripts/dev.py check
```

The gate remains deterministic, local, credential-free, public-safe, and does
not execute tools, agents, providers, local models, browser/email/network
actions, shell commands, production-system actions, private data reads, or
external actions.

## Recommended Next Step

Proceed to M66 Private Evidence Vault. Private production evidence should stay
local and ignored by Git until the M67 redaction and promotion pipeline exists.
