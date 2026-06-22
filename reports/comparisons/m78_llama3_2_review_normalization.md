# M78 Llama3.2 Review Normalization

M78 reviewed the ignored local M77 `llama3.2:latest` extended raw evidence and produced a local-only reviewed normalized candidate. This report is public-safe aggregate metadata only; it contains no raw or normalized output text.

## Summary

| Field | Value |
| --- | --- |
| Source run | `m77_llama3_2_latest_extended` |
| Model | `llama3.2:latest` |
| Split | `extended` |
| Raw records reviewed | 210 |
| Approved public-safe | 210 |
| Rejected / needs discussion | 0 / 0 |
| Malformed / unsafe / private-data blockers | 0 / 0 / 0 |
| Normalized candidate records | 210 |
| Adapter-output validation | `passed_with_allow_live_local` |
| Candidate committed | `false` |
| Ranking claim allowed | `false` |

## Local Hashes

| Artifact | SHA-256 |
| --- | --- |
| `traces/raw/m77_llama3_2_latest_extended.local.jsonl` | `1231c215cab8a17089e5f69186228964629824d409e15375de380e859085e8f4` |
| `traces/raw/m77_llama3_2_latest_extended.metadata.local.json` | `7c1afb934aee0dbf8b22dd1b684e04009112c52645f9d2651658c821a9e83887` |
| `traces/raw/m78_llama3_2_latest_extended.reviewed_input.local.jsonl` | `b185dbaf7d812fda37106b644563269f5bd45aa0c4af605bd582c0cd2004679a` |
| `traces/raw/m78_llama3_2_latest_extended.review_summary.local.json` | `c620c8df480c36eb2292ed806c39cb903d2afc4ecf7f3b448c17e28ecf21ba79` |
| `traces/external/m77_llama3_2_latest_extended.reviewed.jsonl` | `c331944e2f77b45e5f3f7b66d6aa641b46d67b0a12ebde2d90739703ae673295` |

## Boundary

- Raw M77 records and the reviewed normalized candidate remain ignored local artifacts.
- M78 did not create a scored live-local trace or an M58-compatible ledger.
- The deterministic quality gate remains non-live and does not read raw local outputs.
- Publication remains blocked: M78 produced a local ignored reviewed normalized llama3.2 candidate, but M79 scoring/ledger work, the second local target, and the two-ledger publication gate remain incomplete.
