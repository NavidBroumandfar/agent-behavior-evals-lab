# Adapter Output Provenance

Adapter-output provenance records why a saved target-side output is allowed into the deterministic evaluator pipeline.

The original `provenance` booleans answer the hard safety questions: whether a record is public-safe, whether live execution happened, whether external actions happened, and whether private data is present. M5.2 keeps those booleans required and unchanged.

`provenance_details` adds a small optional object for clearer public-safe context. It does not replace the booleans. Default committed fixture validation remains non-live; M57 adds an explicit reviewed live-local opt-in path for local text-only model outputs.

## Why More Than Booleans

The booleans are intentionally strict, but they do not explain where a fixture came from. A saved transcript, a reviewer-prepared normalized output, a dry-run contract fixture, and a sanitized external sample can all be public-safe and non-live while still needing different review expectations.

The detail object gives future readers enough information to understand the record without tying the scorer to a provider, model runtime, CLI agent, or OpenClaw.

## Detail Fields

`source_origin` describes fixture origin: synthetic fixture, manual saved output, saved transcript, dry-run contract, sanitized external sample, future controlled adapter output, or reviewed live-local model output.

`execution_mode` describes how the record entered the fixture path: no live execution, saved output only, dry-run only, reviewed live-local text-only output, or a future live mode that is documented but blocked from current gated fixtures.

`data_classification` describes public suitability: public synthetic, public sanitized, public-safe fixture, or a future blocked private/sensitive classification.

`action_evidence` describes what evidence supports action claims: none required, not applicable, output text only, trace/transcript reference, or future external-action evidence required later.

`notes` is optional public-safe text for deterministic context.

## Current Gate

Committed adapter-output fixtures must remain deterministic and public-safe. The validator rejects these future-only values in current gated fixture validation:

- `data_classification=private_or_sensitive_blocked`
- `execution_mode=future_live_execution_not_in_quality_gate`

Current deterministic fixtures should use safe values such as `no_live_execution`, `saved_output_only`, `dry_run_only`, `public_synthetic`, `public_sanitized`, and `public_safe_fixture`.

Reviewed M57 live-local outputs must be validated with `--allow-live-local`. They must use `source_origin=live_local_model`, `execution_mode=live_local_text_only`, `data_classification=public_safe_fixture`, `action_evidence=output_text_only`, and source metadata proving tools, credentials, external actions, and quality-gate execution were disabled.

## Future Protection

This structure gives hosted provider, local model, CLI agent, and OpenClaw-related adapter work a place to declare origin, execution mode, evidence limits, and data classification before scoring. That helps prevent live output, private data, or action claims from being hidden behind generic fixture labels.

Future collection can produce reviewed saved artifacts, but those artifacts still have to pass the public-safe validator before entering scored traces. Live-local artifacts require the M57 opt-in validator/import flags and remain outside the deterministic gate by default.

## Still Not Live Execution

M5.2 does not add provider APIs, provider SDKs, local model execution, live OpenClaw execution, browser/email tools, external actions, credentials, network calls, private runtime integration, real adapters, or scoring changes.

`provenance_details` is metadata on saved JSONL records. The evaluator still scores only `output_text` after validation and import.
