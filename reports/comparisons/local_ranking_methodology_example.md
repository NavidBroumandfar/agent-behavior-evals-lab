# Local Ranking Methodology Example

This M59 artifact demonstrates deterministic ranking calculations with synthetic public-safe inputs only.
It is not a local model leaderboard and does not support model-quality claims.

## Summary

| Field | Value |
| --- | --- |
| Snapshot ID | `m59_local_ranking_methodology_example` |
| Snapshot kind | `methodology_example_only` |
| Publication status | `example_only_not_publishable` |
| Ranking claim allowed | `false` |
| Case set | `local_public_v1` `1.0.0` |
| Split | `smoke` |

## Example Results

| Example rank | Model | Weighted effective | Weighted heuristic | 95% CI | Sample | Unresolved review | Abstentions | Eligible |
| ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| 1 | `fake-local-model-alpha` | 0.8925 | 0.8925 | 0.7400-1.0000 | 21 | 0 | 0 | false |
| 2 | `fake-local-model-beta` | 0.3656 | 0.4086 | 0.1443-0.6042 | 21 | 0 | 1 | false |

## Exclusions

- `fake-local-model-alpha`: Synthetic methodology example; not real model evidence; Benchmark split is not publishable for local rankings; Sample size is below the publication minimum.
- `fake-local-model-beta`: Synthetic methodology example; not real model evidence; Benchmark split is not publishable for local rankings; Sample size is below the publication minimum.

## Boundaries

- This artifact demonstrates ranking calculations only.
- The inputs are synthetic and do not represent local model quality.
- M59 does not publish a leaderboard or support production-policy proof claims.
- Real local rankings require M58 ledger-backed public-safe local_public_benchmark evidence.
