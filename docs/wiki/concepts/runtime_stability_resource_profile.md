# Runtime Stability And Resource Profile

M85 adds public-safe runtime stability metadata for live-local model runs. The
profile records operational stop criteria and model-specific resource status
without reading raw outputs, probing the local runtime, or executing a model.

Primary artifacts:

- `schemas/runtime_stability_profile.schema.json`
- `traces/external/runtime_stability_profile.example.json`
- `src/runtime_stability_profile.py`
- `tests/test_runtime_stability_profile.py`

## What The Profile Covers

The committed profile records:

- the local `ollama` runtime, `ollama_text_only` adapter, and
  `live_local_text_only_harness` controls,
- operator controls such as one-model-at-a-time execution, plan-only preflight,
  ignored raw outputs, review-before-scoring, and stop-on-instability,
- model-specific status for `llama3.2:latest`, `mistral:latest`,
  `qwen3.5:2b-q4_K_M`, `gemma4:latest`, and `gemma4:31b-cloud`,
- the M77 `gemma4:latest` swap-activity blocker,
- stop criteria for memory pressure, swap activity, thermal or power
  instability, model availability failures, and repeated timeouts.

## Current Target Status

`llama3.2:latest` and `mistral:latest` remain the only ranked local targets in
the current report. `qwen3.5:2b-q4_K_M` remains smoke/control only.
`gemma4:31b-cloud` remains excluded from local/open-weight claims.

`gemma4:latest` remains deferred. M85 documents why it stopped and what must
happen before any future retry, but it does not authorize a new live run and
does not make the model ranking-eligible.

## Boundary

The profile is metadata only. It treats failed, interrupted, partial, or
unstable runs as operational blockers, not benchmark evidence. The deterministic
quality gate validates the committed profile but does not call Ollama, check
local model availability, read raw local outputs, handle credentials, or perform
external actions.
