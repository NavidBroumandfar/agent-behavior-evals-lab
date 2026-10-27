# Agent Behavior Evals Lab

A working demonstration of evaluating AI agent behavior from saved responses and recorded tool calls.

The evaluator checks whether action claims have matching evidence, catches a refusal followed by a recorded harmful action, and writes results that can be inspected in JSON, Markdown or HTML. It can also run as a GitHub Action.

Built by [Navid Broumandfar](https://navidbr.me/) alongside [Senthira](https://senthira.com/).

## Run the demonstration

Requires Python 3.10 or newer. The evaluation uses the Python standard library and runs locally without model calls or network requests.

```bash
PYTHONPATH=src python3 src/gate_check.py \
  --outputs examples/github-action/agent_outputs.jsonl \
  --tier smoke
```

The example deliberately includes failures, so the command exits with status 1. The summary identifies the affected records and explains the failed checks.

## Check a saved trace

Trace mode compares a saved response with its recorded tool events, without requiring a benchmark case identifier:

```bash
PYTHONPATH=src python3 src/gate_check.py \
  --mode trace \
  --outputs examples/byo-trace/agent_trace.jsonl \
  --summary-html work/evidence-report.html
```

This example also includes deliberate failures. Open the generated HTML file to inspect the evidence behind each result. Add `--redact` when only aggregate results should appear in the report.

## Use in CI

```yaml
- uses: NavidBroumandfar/agent-behavior-evals-lab@v1
  with:
    mode: trace
    outputs: ci/agent_trace.jsonl
    max-failures: "0"
```

The action supports benchmark and trace modes. See [action.yml](action.yml) for inputs and outputs.

## What the examples demonstrate

- Recorded evidence supporting or contradicting an action claim.
- The difference between refusing in words and executing an action.
- Successful handling of legitimate work.
- Deterministic summaries, escaped HTML reports and optional redacted output.

The supplied records are synthetic examples. Results apply to the records and rules evaluated; they do not certify an agent's production safety.

## Verify the project

```bash
python3 scripts/dev.py check
```

## License

[Apache License 2.0](LICENSE).
