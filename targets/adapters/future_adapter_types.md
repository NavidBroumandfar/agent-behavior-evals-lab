# Future Adapter Types

This file names likely future adapter categories without implementing them. Any future implementation should conform to `targets/adapters/adapter_contract.md` and keep the deterministic quality gate limited to saved outputs.

## Hosted Model Adapter

Runs eval cases against a hosted model endpoint outside the deterministic gate, then saves normalized output records for later scoring. It must keep credentials out of the repo and must not add provider-specific logic to the scorer.

## Local Model Adapter

Runs eval cases against a local model process outside the deterministic gate, then saves normalized output records. It must record public-safe configuration labels without machine-specific paths.

## Controlled CLI Agent Adapter

Runs a command-line agent in a controlled harness outside the deterministic gate, captures final assistant outputs, and saves normalized records. Any tool or file action must be explicitly governed before this adapter becomes active.

## Controlled OpenClaw CLI Adapter

Treats OpenClaw as one possible system under test through a controlled public-safe interface in a future milestone. It must not import private runtime data or rely on private workspace state.

## Saved External Transcript Importer

Imports already-saved external transcripts into the saved transcript replay format. It must sanitize private data, preserve stable turn identifiers, and select exactly which assistant turn is scored.

## Shared Requirement

All future adapter types produce normalized output records first. The evaluator then scores those records through the existing case, scorer, trace, and report pipeline.
