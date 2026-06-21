# Local/Open-Weight Benchmark Report V1

This report is public-safe and evidence-gated. It publishes no model rankings unless committed evidence satisfies the M59 methodology.

## Summary

| Field | Value |
| --- | --- |
| Generated at | `2026-06-21T00:00:00Z` |
| Report status | `no_rankings_published` |
| Ranking claim allowed | `false` |
| Case set | `local_public_v1` `1.0.0` |
| Publishable splits | `standard`, `extended` |
| Eligible real local targets | 0 |
| Excluded targets | 1 |

## Ranking Table

No ranking table is published because no committed real local model evidence satisfies M59.

## Excluded Evidence

- `m58_local_run_ledger_example` (`fake-local-model`): Evidence class is not local_public_benchmark; Run mode is not reviewed_live_local_run; Ledger marks entry ranking-ineligible: Dry-run fake public-safe example; not model evidence; Benchmark split is not publishable for local rankings; Sample size is below the publication minimum.

## Methodology

- Methodology: `local_ranking_methodology_v1` `1.0.0`.
- Primary metric: `severity_weighted_effective_pass_rate`.
- Public rankings require M58 ledger-backed `local_public_benchmark` evidence over the standard or extended split.

## Limitations

- No real local/open-weight model ranking is published unless at least two eligible real local targets are present.
- Dry-run, synthetic, smoke-split, private-only, and manual-public-sample evidence cannot support this public local ranking.
- The report does not claim cloud-model ranking, production-policy proof, private runtime behavior, or provider benchmark results.
- Live local execution remains opt-in only and outside the deterministic quality gate.

## Reproduction

- Run `python3 scripts/dev.py check` to regenerate and validate the public-safe report artifacts.
- For future real evidence, run the M57 harness manually with `--live-local` and `AGENT_EVALS_ENABLE_LIVE_LOCAL`, then review and normalize saved outputs.
- Validate reviewed live-local outputs with `--allow-live-local` and import them against `evals/benchmarks/local_public_v1/cases.jsonl`.
- Create an M58-compatible run ledger for the reviewed outputs, then rerun this report generator.
