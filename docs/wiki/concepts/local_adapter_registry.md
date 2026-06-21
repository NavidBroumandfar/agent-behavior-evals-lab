# Local Adapter Registry

M56 adds a registry for zero-cost local and manual text-only adapter classes.

Primary artifacts:

- `targets/adapters/local_adapter_registry.json`
- `schemas/local_adapter_registry.schema.json`
- `src/validate_local_adapter_registry.py`

## Adapter Classes

The registry declares three adapter classes for future `local_public_v1` runs:

- `ollama_text_only`: future local Ollama text-only generation.
- `local_openai_compatible_text_only`: future local OpenAI-compatible text-only generation, such as llama.cpp, vLLM, or LM Studio configured locally.
- `manual_saved_output`: public-safe saved-output-only bridge for manually collected final text.

All registered adapters use `text_only_adapter_candidate` as the target profile and the normalized adapter-output contract as the scoring boundary.

## Execution Policy

Live local execution is opt-in only. A future local model command must require:

- `--live-local`
- `AGENT_EVALS_ENABLE_LIVE_LOCAL`

The deterministic quality gate validates the registry, but it must not call Ollama, local OpenAI-compatible servers, providers, agents, or tools. Raw local outputs are not committable. Reviewed normalized outputs must pass the existing adapter-output validation path before scoring.

## Boundary

M56 is a registry and validation phase. It does not call a model, collect outputs, or rank models.

The registry is valuable because M57 implements against a declared set of local adapter classes, endpoint classes, target profile, case-set version, default parameters, and safety rules instead of inventing those details inside the runner.
