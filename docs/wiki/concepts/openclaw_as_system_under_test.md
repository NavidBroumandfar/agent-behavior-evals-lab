# OpenClaw As A System Under Test

Agent Behavior Evals Lab is the evaluator. OpenClaw is only one possible system under test.

## What M3.2 Adds

M3.2 adds a public-safe OpenClaw-style manual sample:

- Input fixture: `traces/external/openclaw_manual_samples.example.jsonl`
- Scored trace: `traces/scored/openclaw_manual_eval.jsonl`
- Report: `reports/comparisons/openclaw_manual_eval_report.md`

The sample records are fictional and sanitized. They are inspired by behavior principles such as approval gates, no fake completion claims, no fabricated tool use, safe stopping, uncertainty handling, and refusal boundaries.

## What It Does Not Do

This sample does not run OpenClaw, call APIs, use live adapters, browse, send email, import private artifacts, or read local project state.

The fixture is just local JSONL text. The evaluator loads those records, matches each `case_id` to an existing eval case, scores the provided `model_output`, and writes deterministic artifacts.

## Why This Matters

The sample demonstrates the adapter boundary before any real adapter exists. A future saved-transcript replay or controlled adapter can target the same scoring contract, but the quality gate stays deterministic and public-safe.

## Manual Command

From the repository root:

```bash
python3 src/evaluate_manual_outputs.py \
  --input traces/external/openclaw_manual_samples.example.jsonl \
  --output traces/scored/openclaw_manual_eval.jsonl \
  --report reports/comparisons/openclaw_manual_eval_report.md \
  --run-id openclaw_manual_eval_example \
  --report-title "Public OpenClaw-Style Manual Evaluation Report" \
  --report-context "This public-safe sample treats sanitized OpenClaw-inspired outputs as one system under test. The records are fictional examples based on behavior principles such as approval gates, safe stopping, uncertainty handling, refusal boundaries, no fabricated tool use, and no fake completion claims; no live execution or private runtime data is used."
```

The quality gate runs the same fixed report context so repeated runs do not change generated content.
