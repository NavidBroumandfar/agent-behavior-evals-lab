# Milestone 83 - Two-Model Report Unlock

Status: Complete / local-open-weight ranking published
Date: 2026-06-22

## Summary

M83 regenerated the local/open-weight benchmark report from two eligible
reviewed live-local extended ledgers: `llama3.2:latest` from M79 and
`mistral:latest` from M82. The report now satisfies the two-ledger publication
gate and sets `ranking_claim_allowed: true`.

## Published Ranking

| Rank | Model | Weighted effective | 95% CI | Sample | Split |
| ---: | --- | ---: | --- | ---: | --- |
| 1 | `llama3.2:latest` | 0.3484 | 0.2860-0.4158 | 210 | `extended` |
| 2 | `mistral:latest` | 0.1065 | 0.0708-0.1425 | 210 | `extended` |

The dry-run fake ledger remains excluded. The report still does not claim
production safety, hosted-provider ranking, cloud-model ranking,
private-audit proof, or third-party reproducibility.

## Artifact Hashes

| Artifact | SHA-256 |
| --- | --- |
| `reports/comparisons/local_open_weight_benchmark_v1.json` | `ae9d2e7a20ad4e9b25db9760847e1d54b6ac89f88002e2cd9abca9e409f48596` |
| `reports/comparisons/local_open_weight_benchmark_v1.md` | `36b5e401e5ac301d92e827bce5c9f02ff29acb824bbb1405ea42a868df5deb36` |
| `reports/comparisons/real_model_proof_runbook.json` | `3b1ea83bd5b03648465a080047bb7ea96056d12dd568a27789dad2568d40e640` |
| `reports/comparisons/real_model_proof_runbook.md` | `70cff5fb1e55456121bc66fcc086e8b83bf5edfe217692d4fde05680229f88a0` |

## Boundary

M83 publishes only the local/open-weight benchmark ranking allowed by the M59
methodology and the M70-M82 review/ledger gates. Raw outputs remain ignored and
local-only, live-local execution remains outside the deterministic quality
gate, and `gemma4:latest`, `qwen3.5:2b-q4_K_M`, and `gemma4:31b-cloud` remain
excluded from the current publication claim.

## Validation

From the repository root:

```bash
python3 src/local_benchmark_report.py
python3 src/validate_local_benchmark_report.py
python3 src/real_model_proof_runbook.py
python3 scripts/dev.py check
```
