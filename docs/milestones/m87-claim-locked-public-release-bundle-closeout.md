# Milestone 87 - Claim-Locked Public Release Bundle

Status: Complete / public-safe release bundle published
Date: 2026-06-22

## Summary

M87 adds a claim-locked public release bundle for the current local/open-weight
benchmark release. The bundle turns the M83 report, M84 reproducibility packet,
M85 runtime-stability profile, and M86 claim-review checklist into one
public-safe release handoff.

This milestone does not collect new evidence, run a local model, inspect raw
outputs, submit hosted-provider jobs, read private evidence, use credentials,
or add live execution to the deterministic quality gate.

## Completed

- Added `schemas/public_release_bundle.schema.json`.
- Added `traces/external/public_release_bundle.example.json`.
- Added `src/public_release_bundle.py`.
- Added `tests/test_public_release_bundle.py`.
- Wired public release bundle validation into `scripts/check_all.py`.
- Added wiki, roadmap, and schema-coverage documentation.

## Approved Release Wording

The bundle allows this scoped release summary:

> The committed report may be described as a public-safe local/open-weight ranking for llama3.2:latest and mistral:latest over the local_public_v1 extended split, backed by two reviewed local Ollama ledgers.

The required qualifier is:

> This is not a cloud-model ranking, hosted-provider comparison, production-safety proof, private-audit proof, or third-party output-regeneration claim.

## Ranked Rows

| Rank | Model | Runtime | Weighted effective | 95% CI | Sample |
| ---: | --- | --- | ---: | --- | ---: |
| 1 | `llama3.2:latest` | `ollama` | 0.3484 | 0.2860-0.4158 | 210 |
| 2 | `mistral:latest` | `ollama` | 0.1065 | 0.0708-0.1425 | 210 |

## Boundary

M87 does not make `gemma4:latest`, `gemma4:31b-cloud`, or
`qwen3.5:2b-q4_K_M` ranking-eligible. It does not publish raw outputs and does
not compare the local ranking to hosted providers.

## Validation

From the repository root:

```bash
python3 src/public_release_bundle.py
python3 scripts/dev.py check
```
