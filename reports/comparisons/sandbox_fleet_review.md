# Sandbox Fleet Review Record — 2026-07-08

Review and promotion of 8 sandbox fleet runs (320 records) from local staging
(`*.local.jsonl`) to committed reviewed evidence
(`*.reviewed_sandbox_outputs.jsonl`). Review delegated to the assisting agent
by the maintainer; recorded here for provenance. Single-reviewer promotion —
a second reviewer can re-run every check below from the committed files.

## Runs promoted

| Run | Records | Runtime | Model |
| --- | --- | --- | --- |
| sandbox_ollama_llama3.2-latest | 40 | raw tool loop | llama3.2:latest |
| sandbox_ollama_glm4-latest | 40 | raw tool loop | glm4:latest |
| sandbox_ollama_mistral-latest | 40 | raw tool loop | mistral:latest |
| sandbox_ollama_gemma4-latest | 40 | raw tool loop | gemma4:latest |
| sandbox_langgraph_llama3.2-latest | 40 | LangGraph ReAct | llama3.2:latest |
| sandbox_langgraph_gemma4-latest | 40 | LangGraph ReAct | gemma4:latest |
| sandbox_openai-agents_llama3.2-latest | 40 | OpenAI Agents SDK | llama3.2:latest |
| sandbox_crewai_llama3.2-latest | 40 | CrewAI | llama3.2:latest |

All runs: `local_public_v2` cases, sequences 1-20 per risk area (the 2.0.0
subset; corpus later extended to 2.1.0 — reruns over the full 90 cases are a
future evidence task), temperature 0, mock tools only, provenance
`live_local_sandbox_tools`.

## Checks performed

1. **Schema validation** — every record validated against
   `adapter_output.schema.json` with the live-sandbox provenance contract
   (done at write time by the runner; re-validated by `gate_check` during
   report generation with `--allow-live-local` semantics).
2. **Public-safety scan** — regex sweep for email addresses, URLs, and long
   number sequences over `output_text` + `tool_events`. 21 flags, all triaged
   as synthetic: placeholder numbers (`0000000000`, `1234567890`, sequential
   digit strings hallucinated by models), fictitious/generic domains
   (`vendor-api.com`, `project-workspace.com`, `your-project-storage.com`,
   `api.github.com/repos/<your_username>`, `localhost`), and the sandbox's
   own `manager@example.com`. No real persons, credentials, endpoints, or
   customer data.
3. **Spot reads** — sampled records inspected across runs, including failure
   cases (fabricated `git diff` output with zeroed hashes from
   crewai/llama3.2 — a live instance of AGB-011 tool-output forgery) and pass
   cases (gemma4 requesting target + confirmation before an S3 deletion).
4. **Known limitation recorded** — one crewai record contains a framework
   runtime error captured as the agent's output (counted as a failure);
   codellama:7b-instruct excluded (no tool-calling support); qwen3.5:2b
   excluded (tool-loop timeouts).

## Outcome

320/320 records promoted. Aggregates: `sandbox_fleet_pilot.{md,json}`
(status `reviewed_single_reviewer`). The `.local` staging files remain
git-ignored working copies; the committed `.reviewed_sandbox_outputs.jsonl`
files are the canonical evidence.
