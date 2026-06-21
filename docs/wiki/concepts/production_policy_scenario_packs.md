# Production-Policy Scenario Packs

Production-policy scenario packs are the M65 public-safe layer for evaluating
production-like prompts without production-system access. They represent
scenario evidence only, not production proof.

The committed M65 pack covers six scenario families:

- database changes
- deployments
- credentials
- payments
- external messaging
- customer data

Each scenario records synthetic production-state metadata, expected approval or
refusal controls, a selected assistant response, and public-safe safety
assertions. `src/production_policy_scenarios.py` validates the pack and emits:

- saved transcript records for deterministic replay;
- scenario-check records for reader-facing policy evidence;
- no raw production logs, credentials, private data, real customer data, or
  external actions.

## Artifacts

- Scenario pack: `traces/external/production_policy_scenario_pack.example.json`
- Pack schema: `schemas/production_policy_scenario_pack.schema.json`
- Check schema: `schemas/production_policy_scenario_check.schema.json`
- Fixture generator: `src/production_policy_scenarios.py`
- Normalized transcripts: `traces/external/production_policy_scenario_transcripts.example.jsonl`
- Scenario checks: `traces/external/production_policy_scenario_checks.example.jsonl`
- Scored trace: `traces/scored/production_policy_scenario_eval.jsonl`
- Report: `reports/comparisons/production_policy_scenario_report.md`
- Adjudications: `traces/external/production_policy_scenario_adjudications.example.jsonl`
- Tests: `tests/test_production_policy_scenarios.py`

## Runtime Boundary

M65 does not run production systems. The deterministic gate validates local
schemas, synthetic metadata, saved transcript replay, scenario checks, and
public-safe adjudications only. It does not call providers, run local models,
execute agents, use credentials, access production databases or deployments,
send messages, process payments, expose customer data, or perform external
actions.

## Interpretation

Scenario packs can support scoped statements such as: "On this public-safe
synthetic scenario pack, the selected assistant turns requested approval and
disclosed production-like risk." They must not be used to claim production
compliance, production safety, private audit results, or public benchmark
rankings.
