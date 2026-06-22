# Milestone 85 - Runtime Stability And Resource Profile

Status: Complete / public-safe stability metadata published
Date: 2026-06-22

## Summary

M85 adds a public-safe runtime stability and resource profile for live-local
model runs. The profile records operator controls, model-specific resource
status, stop criteria, and the M77 `gemma4:latest` swap-activity blocker as
metadata. It does not run a local model, inspect raw local outputs, probe
Ollama, call providers, use credentials, or add live execution to the
deterministic quality gate.

## Completed

- Added `schemas/runtime_stability_profile.schema.json`.
- Added `traces/external/runtime_stability_profile.example.json`.
- Added `src/runtime_stability_profile.py`.
- Added `tests/test_runtime_stability_profile.py`.
- Wired runtime stability profile validation into `scripts/check_all.py`.
- Added wiki and schema-coverage documentation.

## Profiled Targets

| Model | Status | Publication use | Ranking eligible |
| --- | --- | --- | --- |
| `llama3.2:latest` | `completed_reviewed_extended` | current local/open-weight ranking | true |
| `mistral:latest` | `completed_reviewed_extended` | current local/open-weight ranking | true |
| `qwen3.5:2b-q4_K_M` | `smoke_control_only` | operator smoke only | false |
| `gemma4:latest` | `deferred_after_swap_activity` | deferred operational blocker | false |
| `gemma4:31b-cloud` | `excluded_from_local_claims` | cloud boundary exclusion | false |

## Stop Criteria

The profile records these public-safe stop criteria:

- Stop on memory pressure, swap activity, or sustained paging.
- Stop or defer on thermal, power, or other machine instability.
- Exclude incomplete runs when model availability or repeated timeout failures
  prevent a complete selected split.

Interrupted or partial runs are operational blockers, not benchmark evidence.
They cannot support ranking claims unless a later complete reviewed run is
validated and ledgered.

## Boundary

M85 does not re-admit `gemma4:latest` to the current ranking. It documents the
resource blocker and the criteria for any future operator decision. A future
retry still requires explicit live-local opt-in, ignored raw-output handling,
public-safe review, scoring, ledger validation, and a separate claim review.

No cloud claim, production-safety claim, hosted-provider comparison,
third-party reproducibility claim, private-audit proof, or claim from
smoke/control evidence is introduced.

## Validation

From the repository root:

```bash
python3 src/runtime_stability_profile.py
python3 scripts/dev.py check
```
