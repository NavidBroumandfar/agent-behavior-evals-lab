# Mock Vs Real Evaluations

Milestone 1 is a deterministic mock evaluation, not a real model benchmark.

## Mock Evaluation

The current baseline uses `src/model_clients.py` to generate controlled responses for three profiles:

- `generic_assistant`
- `openclaw_reference_agent`
- `strict_approval_agent`

Those profiles are simulated targets. The mock run exists to prove that case loading, scoring, trace writing, reporting, schema validation, and quality gates work together.

## Real Evaluation

A real evaluation would run cases against an actual model, saved transcript, or agent adapter. That adapter would need a clear contract, stable trace capture, reproducible configuration, and safety controls around any tool or system access.

The repository has a future adapter area at `targets/adapters/`, but no real model adapters are active yet.

## Interpreting The Baseline

`reports/baseline_report.md` shows deterministic mock results. The OpenClaw-inspired profile is not evidence that OpenClaw was executed. No live OpenClaw run happened in Milestone 1.

The baseline is useful as a pipeline fixture. It should not be cited as production model performance, leaderboard data, or proof of agent quality.
