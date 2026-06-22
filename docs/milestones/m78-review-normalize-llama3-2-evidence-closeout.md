# Milestone 78 - Review And Normalize Llama3.2 M77 Evidence

Status: Complete / local ignored reviewed candidate produced, publication blocked
Date: 2026-06-22

## Summary

M78 reviewed the 210 ignored local raw records from the M77
`llama3.2:latest` extended run and produced a reviewed live-local normalized
candidate under an ignored local path. The committed artifacts are aggregate
public-safe metadata only. They do not include raw output text, normalized
output text, private data, credentials, scored live-local traces, or ledgers.

## Completed

- Reviewed all 210 M77 `llama3.2:latest` extended raw records.
- Approved 210 records as public-safe text-only evidence for local candidate
  normalization.
- Wrote the local ignored reviewed input at
  `traces/raw/m78_llama3_2_latest_extended.reviewed_input.local.jsonl`.
- Wrote the local ignored normalized candidate at
  `traces/external/m77_llama3_2_latest_extended.reviewed.jsonl`.
- Validated the normalized candidate with
  `python3 src/validate_adapter_outputs.py --allow-live-local
  traces/external/m77_llama3_2_latest_extended.reviewed.jsonl`.
- Recorded public-safe aggregate metadata in
  `reports/comparisons/m78_llama3_2_review_normalization.json` and
  `reports/comparisons/m78_llama3_2_review_normalization.md`.
- Updated the real-model proof runbook metadata so M79 is the next
  non-live scoring and ledger phase for the reviewed candidate.

## Local Artifact Hashes

| Artifact | SHA-256 |
| --- | --- |
| `traces/raw/m77_llama3_2_latest_extended.local.jsonl` | `1231c215cab8a17089e5f69186228964629824d409e15375de380e859085e8f4` |
| `traces/raw/m77_llama3_2_latest_extended.metadata.local.json` | `7c1afb934aee0dbf8b22dd1b684e04009112c52645f9d2651658c821a9e83887` |
| `traces/raw/m78_llama3_2_latest_extended.reviewed_input.local.jsonl` | `b185dbaf7d812fda37106b644563269f5bd45aa0c4af605bd582c0cd2004679a` |
| `traces/raw/m78_llama3_2_latest_extended.review_summary.local.json` | `c620c8df480c36eb2292ed806c39cb903d2afc4ecf7f3b448c17e28ecf21ba79` |
| `traces/external/m77_llama3_2_latest_extended.reviewed.jsonl` | `c331944e2f77b45e5f3f7b66d6aa641b46d67b0a12ebde2d90739703ae673295` |

## Boundary

M78 does not publish a benchmark ranking. It does not create or commit a scored
live-local trace, M58-compatible ledger, second-model ledger, or local/open-
weight report ranking. The deterministic quality gate remains non-live and does
not read raw local outputs.

Publication remains blocked until M79 scores and ledgers the reviewed
`llama3.2:latest` candidate, a stable second local target is reviewed, scored,
and ledgered, and the two-ledger publication gate passes.

## Validation

From the repository root:

```bash
python3 src/validate_adapter_outputs.py --allow-live-local traces/external/m77_llama3_2_latest_extended.reviewed.jsonl
python3 scripts/dev.py check
```
