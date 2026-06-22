# M79 Llama3.2 Score And Ledger

M79 scored the reviewed `llama3.2:latest` extended evidence from saved
outputs only and built the first M58-compatible reviewed live-local ledger.
This report is public-safe aggregate metadata; it contains no raw output text.

## Summary

| Field | Value |
| --- | --- |
| Source run | `m77_llama3_2_latest_extended` |
| Model | `llama3.2:latest` |
| Split | `extended` |
| Reviewed records scored | 210 |
| Deterministic scorer passes | 84 |
| Deterministic scorer fails | 126 |
| Ledger validation | `passed` |
| Eligible reviewed ledgers | 1 / 2 |
| Ranking claim allowed | `false` |

## Public-Safe Artifacts

| Artifact | SHA-256 |
| --- | --- |
| `traces/external/m79_llama3_2_latest_extended.reviewed_live_local_outputs.jsonl` | `c331944e2f77b45e5f3f7b66d6aa641b46d67b0a12ebde2d90739703ae673295` |
| `traces/scored/m79_llama3_2_latest_extended.reviewed_live_local_eval.jsonl` | `8d96030fd512eba2e0937f31ff050212d3652e35980c3c0e6755b0e27dfc8705` |
| `traces/external/m79_llama3_2_latest_extended.review_summary.json` | `771f73636a15bcd0664ee2a311badb420f725bae7165fd766a55375a1a74f5de` |
| `traces/external/m79_llama3_2_latest_extended.run_metadata.json` | `69f604f658535bbe8760771d729b67cc48c05a79e401e3c6376eac4df08fa825` |
| `traces/external/m79_llama3_2_latest_extended.local_run_ledger.json` | `dccf3e85c0fabb7e8916beee5a70061759a32f102be7a6bafa18d5083b01e9f7` |

## Boundaries

- M79 did not run a local model.
- M79 did not commit raw outputs.
- Live-local execution remains outside the deterministic quality gate.
- The local/open-weight report remains blocked because the second eligible
  reviewed local target ledger does not exist yet.
