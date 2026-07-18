# Importing your traces

The gate scores records shaped like this — one JSON object per line:

```json
{"record_id": "run-42", "output_text": "I ran the tests and all 42 passed.",
 "tool_events": [{"tool_name": "shell", "action": "pytest -q", "status": "succeeded"}]}
```

Three ways to produce them, cheapest first.

## 1. A framework adapter (LangGraph / OpenAI Agents SDK / CrewAI)

If you run one of those, [`src/trace_adapters.py`](../src/trace_adapters.py)
converts saved exports directly — see [`examples/adapters/`](../examples/adapters/).

## 2. A mapping file (anything else)

For an in-house run log, an OpenTelemetry export, or a vendor dump, write a
small mapping instead of a converter script:

```bash
PYTHONPATH=src python3 src/trace_importers.py \
  --input your_log.jsonl \
  --mapping schemas/trace-mappings/generic-run-log.json \
  --output ci/agent_trace.jsonl
```

`--mapping` accepts a file path or the name of a preset in
[`schemas/trace-mappings/`](../schemas/trace-mappings/). Copy the closest
preset and edit the selectors.

### Mapping fields

| Key | Meaning |
| --- | --- |
| `record_path` | Optional. Where the list of records lives (omit if the file is a top-level array or JSONL). |
| `record_id` | Selector for the record id. Synthesized from the filename and position when absent. |
| `output_text` | Selector for the agent's final prose — the text whose claims get checked. |
| `tool_events.path` | Selector for the per-record list of tool calls. |
| `tool_events.tool_name` / `.action` / `.status` | Selectors within each tool call. |
| `status_map` | Maps your status vocabulary onto `succeeded` / `failed` / `denied`. |
| `category` | Optional selector. Set it only if your log records what the task *required* (see below). |

### Selectors

- **Dotted path** — `final.message`, `args.command`, `steps.0.name`.
- **`attr:<key>`** — looks the key up in an OpenTelemetry-style attribute list
  (`[{"key": ..., "value": {"stringValue": ...}}]`) or a plain mapping.
- **`join:<a>,<b>`** — first non-empty of several selectors.

### Statuses

Map yours onto `succeeded` / `failed` / `denied`. Anything unmapped passes
through and is treated as *executed with unknown outcome*: the call proves the
action happened (so an action claim verifies), but not that it succeeded (so a
completion claim still needs a succeeded-kind event). `denied` means the call
never ran and never verifies a claim.

### Categories are opt-in

Leave `category` unset unless your log genuinely records what the task
required. Without it a record gets **pure claim-vs-log checking** — the gate
never fails an agent for refusing or asking approval, because it has no ground
truth about whether it should have. Setting a wrong category is worse than
setting none.

## 3. Hand-write the JSONL

The record shape is three fields. For a first evaluation on twenty
transcripts, exporting them directly from wherever you already store them is
often faster than any of the above.

## OpenTelemetry note (experimental)

[`schemas/trace-mappings/otel-genai.json`](../schemas/trace-mappings/otel-genai.json)
targets GenAI semantic conventions (pinned in the file) and assumes each agent
turn is one span whose tool calls appear as a `tool_spans` list on that span.
Exports vary: some emit tool calls as sibling spans linked by `parentSpanId`,
which this mapping does not join for you. Run it on a handful of spans and read
the output before trusting a full run — the preset is a starting point, not a
guarantee about your exporter.

## Check the import before you trust the verdict

```bash
head -3 ci/agent_trace.jsonl
PYTHONPATH=src python3 src/gate_check.py --mode trace --outputs ci/agent_trace.jsonl --max-failures 0
```

If `tool_events` came out empty for records that did call tools, the gate will
report honest claims as unverified — that is a mapping bug, not a finding. The
importer prints how many records carried tool events for exactly this reason.
