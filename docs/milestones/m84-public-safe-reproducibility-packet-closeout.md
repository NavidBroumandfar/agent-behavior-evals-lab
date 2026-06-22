# Milestone 84 - Public-Safe Reproducibility Packet

Status: Complete / public-safe packet published
Date: 2026-06-22

## Summary

M84 adds a public-safe reproducibility packet for the M83 local/open-weight
ranking. The packet records the exact committed artifacts, hashes, target
identifiers, harness/scorer/adapter versions, command templates, validation
commands, source inventory, and claim boundaries needed to audit the published
ranking without committing raw outputs or rerunning a local model.

This packet supports deterministic replay and verification from committed
public-safe derivatives. It does not claim that a third party can regenerate
the same model outputs from model tags alone, because Ollama tags are mutable
labels unless an operator separately captures local model digests and runtime
state.

## Published Ranking Context

| Field | Value |
| --- | --- |
| Report | `reports/comparisons/local_open_weight_benchmark_v1.json` |
| Report status | `published_local_ranking` |
| Ranking claim allowed | `true` |
| Evidence class | `local_public_benchmark` |
| Case set | `local_public_v1` `1.0.0` |
| Split | `extended` |
| Cases per ranked target | 210 |
| Eligible reviewed ledgers | 2 / 2 |
| Primary metric | `severity_weighted_effective_pass_rate` |
| Methodology | `local_ranking_methodology_v1` `1.0.0` |

| Rank | Model identifier | Runtime | Weighted effective | 95% CI | Sample |
| ---: | --- | --- | ---: | --- | ---: |
| 1 | `llama3.2:latest` | `ollama` | 0.3484 | 0.2860-0.4158 | 210 |
| 2 | `mistral:latest` | `ollama` | 0.1065 | 0.0708-0.1425 | 210 |

## Version Pins

| Component | Identifier | Version or label | Artifact | SHA-256 |
| --- | --- | --- | --- | --- |
| Harness | `live_local_text_only_harness` | `0.1.0` | `src/live_local_harness.py` | `c4794f57e3f32396a8e72e8a5fdf46907d83042b90d12f64b42e0e683d712321` |
| Adapter | `ollama_text_only` | `0.1.0` | `targets/adapters/local_adapter_registry.json` | `02e58dc1270edcf0e72fed649e12a23051ac5e22e154e4295555f0378443328c` |
| Prompt template | `local_text_only_v1` | `0.1.0` | `targets/prompts/local_text_only_v1.md` | `3bd2dd3d13d6de9d1732fbc96629d9c09fee30352df077f20f07524342d193d2` |
| Scorer | `deterministic_v0_rule_based_scorer` | `v0-rule-based-heuristic` | `src/scorers.py` | `1dec7cb2520edc346132bb93e64e543f1dc24a6b8349da00c70a3789932753ca` |
| Methodology | `local_ranking_methodology_v1` | `1.0.0` | `benchmarks/local_ranking_methodology.json` | `dabc58593abc1f616c9bb9c8f9e72be6455cdfcada473fa9bc213746781a7263` |
| Ledger schema | `local_run_ledger` | current schema | `schemas/local_run_ledger.schema.json` | `0e81f7c7814a65313f55353deaedc1c55c2a0a35b117a7d4f6656088dd05d152` |
| Report schema | `local_benchmark_report` | current schema | `schemas/local_benchmark_report.schema.json` | `357b01db46b7882cdeaf2fe67f21306e4195f74e1428271d284b12634e294408` |
| Review summary schema | `live_local_review_summary` | current schema | `schemas/live_local_review_summary.schema.json` | `c9653397e940e3e80e17bdddf49eb4c897b73059184a451e39177ffa2b496602` |

## Source Artifact Inventory

These are the committed public-safe source artifacts for the published M83
claim. They are sufficient to verify the committed ranking and replay scoring
from saved public-safe derivatives. They are not raw model outputs.

### Benchmark And Claim Inputs

| Artifact | Role | SHA-256 |
| --- | --- | --- |
| `benchmarks/evidence_class_charter.json` | Evidence-class and claim-boundary rules | `842f43f638175af94b4d23ae4e25dabed525e66b199c01cc49d3db575bcc78cd` |
| `benchmarks/local_ranking_methodology.json` | Ranking metric, eligibility, CI, and exclusion policy | `dabc58593abc1f616c9bb9c8f9e72be6455cdfcada473fa9bc213746781a7263` |
| `evals/benchmarks/local_public_v1/manifest.json` | Frozen case-set manifest | `9dc94414a2fc926a86a8705e540323c524886c3d2c7499f4f4d64c1bfadb8c88` |
| `evals/benchmarks/local_public_v1/cases.jsonl` | Frozen public-safe case corpus | `366ca2f65991f9fbecffa15104e11b1b0f5c1e3f236eee947e00ed209f5891bb` |
| `targets/adapters/local_adapter_registry.json` | Local adapter declarations | `02e58dc1270edcf0e72fed649e12a23051ac5e22e154e4295555f0378443328c` |
| `targets/prompts/local_text_only_v1.md` | Text-only system prompt template | `3bd2dd3d13d6de9d1732fbc96629d9c09fee30352df077f20f07524342d193d2` |

### Replay, Scoring, And Report Code

| Artifact | Role | SHA-256 |
| --- | --- | --- |
| `src/import_adapter_outputs.py` | Saved-output import into scored traces | `2e9a4f5b8e9c89c5894f6dc0bc81390ce4db5f9188279db8f73d46c18a2f909a` |
| `src/validate_adapter_outputs.py` | Normalized adapter-output validation | `2207b58eb6c2b862225d671aa493ed0b88f163c999a31e7adebe7176f4b77e8f` |
| `src/validate_local_run_ledger.py` | Ledger validation and saved-output replay checks | `3c793238aac5f872c9820425cd7d80bf8512367464e50d02c683ebfdb71f3708` |
| `src/local_benchmark_report.py` | Local/open-weight report generation | `40de0e7cd6399e8671a90bf88e096f3619396f8aca30f8319280383dcb8c6aaf` |
| `src/real_model_proof_runbook.py` | CLI/report runbook generation | `7f60b7e62e1649c06b475625e2d1544a31b7359382173aa0df136f121676a1fe` |
| `src/scorers.py` | Deterministic v0 scorer artifact | `1dec7cb2520edc346132bb93e64e543f1dc24a6b8349da00c70a3789932753ca` |

### Published Report Artifacts

| Artifact | Role | SHA-256 |
| --- | --- | --- |
| `reports/comparisons/local_open_weight_benchmark_v1.json` | Machine-readable published local ranking | `ae9d2e7a20ad4e9b25db9760847e1d54b6ac89f88002e2cd9abca9e409f48596` |
| `reports/comparisons/local_open_weight_benchmark_v1.md` | Reader-facing published local ranking | `36b5e401e5ac301d92e827bce5c9f02ff29acb824bbb1405ea42a868df5deb36` |
| `reports/comparisons/real_model_proof_runbook.json` | Machine-readable runbook state | `3b1ea83bd5b03648465a080047bb7ea96056d12dd568a27789dad2568d40e640` |
| `reports/comparisons/real_model_proof_runbook.md` | Reader-facing runbook state | `70cff5fb1e55456121bc66fcc086e8b83bf5edfe217692d4fde05680229f88a0` |

### Ranked Ledger Artifacts

| Artifact | Role | SHA-256 |
| --- | --- | --- |
| `traces/external/m79_llama3_2_latest_extended.local_run_ledger.json` | Ranked `llama3.2:latest` ledger | `dccf3e85c0fabb7e8916beee5a70061759a32f102be7a6bafa18d5083b01e9f7` |
| `traces/external/m79_llama3_2_latest_extended.reviewed_live_local_outputs.jsonl` | Public-safe reviewed derivative for `llama3.2:latest` | `c331944e2f77b45e5f3f7b66d6aa641b46d67b0a12ebde2d90739703ae673295` |
| `traces/scored/m79_llama3_2_latest_extended.reviewed_live_local_eval.jsonl` | Scored trace for `llama3.2:latest` | `8d96030fd512eba2e0937f31ff050212d3652e35980c3c0e6755b0e27dfc8705` |
| `traces/external/m79_llama3_2_latest_extended.review_summary.json` | Review summary for `llama3.2:latest` | `771f73636a15bcd0664ee2a311badb420f725bae7165fd766a55375a1a74f5de` |
| `traces/external/m79_llama3_2_latest_extended.run_metadata.json` | Reviewed run metadata for `llama3.2:latest` | `69f604f658535bbe8760771d729b67cc48c05a79e401e3c6376eac4df08fa825` |
| `traces/external/m82_mistral_latest_extended.local_run_ledger.json` | Ranked `mistral:latest` ledger | `0576c56cb33553909f9278cddcc351bfa77ed892269a2b813fbfbf9cc89ca764` |
| `traces/external/m82_mistral_latest_extended.reviewed_live_local_outputs.jsonl` | Public-safe reviewed derivative for `mistral:latest` | `9513fff6022ce7d6e0f1a593f96de4f61d42dec74b3a5529741edb8cacb507f9` |
| `traces/scored/m82_mistral_latest_extended.reviewed_live_local_eval.jsonl` | Scored trace for `mistral:latest` | `19b90201feb8f9e3e9a25f979ac9b7e68df3b802194df9b8a6559975d7202504` |
| `traces/external/m82_mistral_latest_extended.review_summary.json` | Review summary for `mistral:latest` | `a35328f835e52dd1927775abf34d2f2611b02faa6b320d5cf8c2d5a2bfb1b277` |
| `traces/external/m82_mistral_latest_extended.run_metadata.json` | Reviewed run metadata for `mistral:latest` | `1abd7fa03df93e91436cdbde3ed818fb43caa7a89e0ea3d4fd7b4bbea14e8cb0` |

## Model Identifiers

| Model identifier | Runtime | Run ID | Ledger entry | Rank eligible |
| --- | --- | --- | --- | --- |
| `llama3.2:latest` | `ollama` | `m77_llama3_2_latest_extended` | `m79_llama3_2_latest_extended_reviewed_live_local_entry` | true |
| `mistral:latest` | `ollama` | `m81_mistral_latest_extended` | `m82_mistral_latest_extended_reviewed_live_local_entry` | true |

These identifiers are the model tags recorded by the local Ollama run metadata
and ledgers. M84 does not add model content digests, local hardware profile,
Ollama binary version, OS scheduler state, or thermal/resource profile. Those
belong to the later runtime-stability metadata path.

## Command Templates

M84 did not run a local model. The following templates document how future
operators would collect new local evidence. They require explicit opt-in and
must stay outside `python3 scripts/dev.py check`.

```bash
python3 scripts/live_local.py \
  --model <ollama-model-tag> \
  --adapter ollama_text_only \
  --split extended \
  --plan-only \
  --run-id <run-id> \
  --output traces/raw/<run-id>.local.jsonl \
  --metadata-output traces/raw/<run-id>.run_metadata.local.json \
  --plan-output traces/raw/<run-id>.plan.local.json
```

```bash
AGENT_EVALS_ENABLE_LIVE_LOCAL=1 python3 scripts/live_local.py \
  --model <ollama-model-tag> \
  --adapter ollama_text_only \
  --split extended \
  --live-local \
  --max-failures 210 \
  --run-id <run-id> \
  --output traces/raw/<run-id>.local.jsonl \
  --metadata-output traces/raw/<run-id>.run_metadata.local.json
```

Post-run review, normalization, scoring, and ledger construction must use
public-safe reviewed derivatives only. Raw outputs must remain under ignored
local paths and must not be committed.

## Validation Commands

These commands verify the committed public-safe packet and ranking without
live-local model execution:

```bash
python3 src/validate_adapter_outputs.py --allow-live-local traces/external/m79_llama3_2_latest_extended.reviewed_live_local_outputs.jsonl
python3 src/validate_adapter_outputs.py --allow-live-local traces/external/m82_mistral_latest_extended.reviewed_live_local_outputs.jsonl
python3 src/validate_local_run_ledger.py traces/external/m79_llama3_2_latest_extended.local_run_ledger.json
python3 src/validate_local_run_ledger.py traces/external/m82_mistral_latest_extended.local_run_ledger.json
python3 src/validate_local_benchmark_report.py
python3 src/real_model_proof_runbook.py
python3 scripts/dev.py check
```

To verify recorded artifact hashes from a clean checkout:

```bash
shasum -a 256 \
  benchmarks/evidence_class_charter.json \
  benchmarks/local_ranking_methodology.json \
  evals/benchmarks/local_public_v1/manifest.json \
  evals/benchmarks/local_public_v1/cases.jsonl \
  targets/adapters/local_adapter_registry.json \
  targets/prompts/local_text_only_v1.md \
  src/live_local_harness.py \
  src/scorers.py \
  reports/comparisons/local_open_weight_benchmark_v1.json \
  reports/comparisons/real_model_proof_runbook.json \
  traces/external/m79_llama3_2_latest_extended.local_run_ledger.json \
  traces/external/m82_mistral_latest_extended.local_run_ledger.json
```

## Raw And Local-Only Exclusions

The packet deliberately excludes raw local output hashes and raw local output
inventory from the public reproducibility surface. The public claim starts from
reviewed, committed derivatives and ledgers.

Excluded local-only classes:

- `traces/raw/*.local.jsonl`
- `traces/raw/*.local.json`
- `traces/raw/*.plan.local.json`
- `reports/private/`
- `private_evidence/`

Verification command:

```bash
git check-ignore -v traces/raw/m81_mistral_latest_extended.local.jsonl reports/private/m68_private_audit_report.local.json private_evidence/example.local.jsonl
```

## Claim Boundaries

Allowed claim:

- A public-safe local/open-weight ranking for two reviewed local Ollama model
  tags over `local_public_v1` extended split, using the M59 methodology and
  committed M58-compatible ledgers.

Disallowed claims:

- No cloud-model ranking.
- No production-safety proof.
- No hosted-provider comparison.
- No private-audit proof.
- No third-party model-output regeneration claim.
- No claim that Ollama tags alone pin immutable model weights.
- No claim from raw, private, smoke-only, synthetic, partial, unresolved-review,
  or cloud-labelled evidence.

Explicit target boundaries:

- `gemma4:latest` remains deferred pending resource-stability metadata.
- `qwen3.5:2b-q4_K_M` remains smoke/control only.
- `gemma4:31b-cloud` remains excluded from local/open-weight claims.

## Validation

From the repository root:

```bash
python3 scripts/dev.py check
```

M84 is documentation-only and public-safe. It does not execute a local model,
read raw local outputs, call hosted providers, use credentials, enable tools,
perform external actions, or add live-local execution to the deterministic
quality gate.
