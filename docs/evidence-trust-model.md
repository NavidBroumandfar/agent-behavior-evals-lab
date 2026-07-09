# Evidence Trust Model — who produces `tool_events`, and why they are trusted

The structural verifier checks an agent's claims against a recorded tool-call
log (`tool_events`). That check is only as strong as the log. This page states
the trust boundary explicitly, because "can the log be faked by the thing it
audits?" is the right first question to ask of any action-level evaluator.

## Three trust tiers

| Tier | Source of `tool_events` | Trust basis | Evidence strength |
| --- | --- | --- | --- |
| 1. Harness-recorded | The mock-tool sandbox (`src/sandbox_tools.py`): every call an agent makes is recorded by the harness itself | The agent cannot write to the log — it can only *call tools*, and the harness records each call as a side effect of executing it. The agent has no code path to insert, edit, or delete an event. | Strongest. All sandbox fleet evidence in this repo is tier 1. |
| 2. Adapter-converted framework traces | Saved LangGraph / OpenAI Agents SDK / CrewAI traces converted by `src/trace_adapters.py` | Trusted exactly as much as the trace store: the framework runtime recorded the calls, not the agent's output channel. An agent could not alter these without compromising the framework or the storage. | Strong, conditional on the CI/trace-store owner's own integrity controls. |
| 3. Self-reported | Anything the agent itself asserts — output text, a log the agent wrote, a summary it produced | None. Self-reported action data is a *claim*, not evidence. | Not evidence. The gate scores this tier's content **against** tiers 1–2. |

## What the gate does and does not defend against

- **Defends:** an agent lying in its output about what it did — fabricated tool
  use, fabricated completion, fabricated output blocks, actions taken without
  approval. The claim surface (tier 3) is checked against the recorded log
  (tier 1 or 2).
- **Does not defend:** a compromised or adversarial *harness/trace store*. If
  the party running the tools forges the log, no downstream verifier can
  detect it from the log alone. Log integrity is the boundary of the CI or
  infrastructure owner, exactly as build provenance is in supply-chain
  security. Signing or hashing trace stores is an infrastructure control, not
  an evaluator feature.
- **Does not accept:** records whose `tool_events` provenance is unknown being
  treated as tier 1. Adapter outputs carry provenance fields
  (`provenance`, `provenance_details` — see
  [adapter output provenance](wiki/concepts/adapter_output_provenance.md)) so
  the evidence class of every scored record is explicit.

## Practical consequences

- In this repository, every fleet record was produced by driving the agent
  through the harness (tier 1); the agent never had write access to its own
  evidence.
- For CI use with adapter-converted traces (tier 2), point the converter at
  the framework's own trace output, not at anything the agent post-processed.
- For paid audits, the auditor runs the harness — the system under test never
  supplies its own evidence channel.

_The deterministic keyword scorer needs no trust model: it reads only the
output text. The trust boundary exists precisely because structural scoring
upgrades from "what the agent said" to "what the log shows" — and the log has
an owner._
