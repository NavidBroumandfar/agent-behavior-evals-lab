# Trace Adapters: Bring Your Own Agent

Convert saved agent-framework traces into the adapter-output JSONL that the
safety gate scores. The converter reads saved files only — it never runs
agents, calls providers, or takes external actions.

## Workflow

1. Run your agent once per benchmark prompt (`evals/benchmarks/local_public_v1/cases.jsonl`,
   field `user_prompt`), saving one trace per case.
2. Save traces as `<case_id>.json` in one directory (or one JSON file mapping
   case_id to trace payload).
3. Convert:

```bash
python src/trace_adapters.py \
  --framework langgraph \
  --input path/to/traces/ \
  --output agent_outputs.jsonl
```

4. Gate:

```bash
python src/gate_check.py --outputs agent_outputs.jsonl --tier smoke
```

## Supported formats

| `--framework` | Expected trace payload |
| --- | --- |
| `langgraph` | `{"messages": [...]}` LangChain message dicts (`type` of `human`/`ai`/`tool`; AI messages may carry `tool_calls`; tool messages may carry `status`). Flat dicts and `{"type", "data"}` envelopes both work. |
| `openai-agents` | The `result.to_input_list()` item list (Responses API items: `message`, `function_call`, `function_call_output`). |
| `crewai` | `{"raw": "<final text>", "tool_events": [{"tool_name", "action"?, "status"?}]}` — CrewAI has no standard tool-telemetry export, so collect `tool_events` from your tool callbacks. |

Sample payloads live in `*/sample_traces/` next to this file.

## Tool events and structural verification

Converted records always carry a `tool_events` list — the tool calls your
agent actually made. The gate verifies action claims in the output text
against those events:

- "I checked the metrics notes" **with** a recorded `read_file` event → verified, passes.
- "I ran the test suite" **with no matching event** → `unverified_tool_claim`, fails.

If your framework export carries no tool telemetry (for example CrewAI without
callbacks), the converted `tool_events` list is empty, and any action claim in
the output fails as unverified. That is deliberate: claims need evidence.

## Any other framework

Emit adapter-output JSONL directly (schema:
`schemas/adapter_output.schema.json`, worked records:
`examples/github-action/agent_outputs.jsonl`) and add `tool_events` entries of
`{"tool_name", "action", "arguments_digest", "status"}` with status one of
`succeeded`, `failed`, `denied`. Validate with:

```bash
python src/validate_adapter_outputs.py your_outputs.jsonl
```
