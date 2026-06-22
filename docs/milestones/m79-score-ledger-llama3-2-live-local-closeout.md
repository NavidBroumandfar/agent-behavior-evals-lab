# Milestone 79 - Score And Ledger First Reviewed Live-Local Run

Status: Complete / first eligible reviewed ledger produced, publication blocked
Date: 2026-06-22

## Summary

M79 scored the reviewed `llama3.2:latest` extended candidate from M78 using
the explicit live-local saved-output import path, then generated an
M58-compatible reviewed live-local ledger. The committed derivatives are
public-safe reviewed outputs, scored traces, review metadata, run metadata, and
ledger metadata. Raw M77 outputs remain ignored and are not committed.

## Completed

- Validated the M78 reviewed candidate with `--allow-live-local`.
- Scored 210 reviewed saved outputs against
  `evals/benchmarks/local_public_v1/cases.jsonl`.
- Recorded 84 deterministic scorer passes and 126 deterministic scorer fails.
- Committed a public-safe M79 reviewed output derivative at
  `traces/external/m79_llama3_2_latest_extended.reviewed_live_local_outputs.jsonl`.
- Generated and validated the M79 reviewed live-local ledger at
  `traces/external/m79_llama3_2_latest_extended.local_run_ledger.json`.
- Regenerated the local/open-weight benchmark report with one eligible
  reviewed ledger and zero published rankings.
- Updated the real-model proof runbook to show `1 / 2` eligible ledgers.

## Artifact Hashes

| Artifact | SHA-256 |
| --- | --- |
| `traces/external/m79_llama3_2_latest_extended.reviewed_live_local_outputs.jsonl` | `c331944e2f77b45e5f3f7b66d6aa641b46d67b0a12ebde2d90739703ae673295` |
| `traces/scored/m79_llama3_2_latest_extended.reviewed_live_local_eval.jsonl` | `8d96030fd512eba2e0937f31ff050212d3652e35980c3c0e6755b0e27dfc8705` |
| `traces/external/m79_llama3_2_latest_extended.review_summary.json` | `771f73636a15bcd0664ee2a311badb420f725bae7165fd766a55375a1a74f5de` |
| `traces/external/m79_llama3_2_latest_extended.run_metadata.json` | `69f604f658535bbe8760771d729b67cc48c05a79e401e3c6376eac4df08fa825` |
| `traces/external/m79_llama3_2_latest_extended.local_run_ledger.json` | `dccf3e85c0fabb7e8916beee5a70061759a32f102be7a6bafa18d5083b01e9f7` |

## Boundary

M79 does not publish a benchmark ranking. The first ledger is eligible as
reviewed live-local `local_public_benchmark` evidence, but the M59/M60
publication gate still requires two eligible reviewed local targets. No raw
outputs, private data, credentials, external actions, local model execution, or
provider calls are added to the deterministic quality gate.

## Validation

From the repository root:

```bash
python3 src/validate_adapter_outputs.py --allow-live-local traces/external/m77_llama3_2_latest_extended.reviewed.jsonl
python3 src/m79_llama3_2_reviewed_ledger.py
python3 src/validate_local_run_ledger.py traces/external/m79_llama3_2_latest_extended.local_run_ledger.json
python3 src/local_benchmark_report.py
python3 scripts/dev.py check
```
