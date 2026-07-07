# Framework fleet runs: real agents in the temptation lab

Run a real framework agent (LangGraph, OpenAI Agents SDK, CrewAI) through the
benchmark inside the mock-tool sandbox. The frameworks are **not** core
dependencies — install them in a separate environment:

```bash
python3 -m venv .fleet-venv && source .fleet-venv/bin/activate
pip install langgraph langchain-core langchain-ollama   # LangGraph fleet
pip install openai-agents                               # OpenAI Agents SDK fleet
pip install crewai                                      # CrewAI fleet
```

## Pattern (LangGraph + local Ollama model)

```python
import sys
sys.path.insert(0, "src")
from pathlib import Path
from framework_sandbox_bindings import langchain_tools
from sandbox_agent_runner import run_sandbox_fleet
from ollama_tool_agent import SYSTEM_PROMPT

from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

def langgraph_agent(prompt, toolbox):
    model = ChatOllama(model="llama3.2:latest", temperature=0)
    graph = create_react_agent(model, langchain_tools(toolbox), prompt=SYSTEM_PROMPT)
    result = graph.invoke({"messages": [("user", prompt)]})
    return result["messages"][-1].content

run_sandbox_fleet(
    langgraph_agent,
    agent_name="langgraph-llama3.2",
    tier="extended",
    output_path=Path("traces/external/sandbox_langgraph_llama32.local.jsonl"),
)
```

Same shape for the other frameworks: build the agent with
`openai_agents_tools(toolbox)` / `crewai_tools(toolbox)`, return its final
text. Every tool call the framework makes lands in the record's
`tool_events`, so the gate scores actions, not wording.

## Built-in agents (no extra installs)

```bash
# scripted reference agents
PYTHONPATH=src python3 src/sandbox_agent_runner.py --agent reference-unsafe --tier smoke --output /tmp/unsafe.jsonl

# local model via Ollama tool calling
PYTHONPATH=src python3 src/sandbox_agent_runner.py --agent ollama:llama3.2:latest --tier extended --output traces/external/sandbox_ollama_llama32.local.jsonl

# hosted model via any OpenAI-compatible endpoint (opt-in, env-configured)
export AGENT_EVALS_OPENAI_COMPAT_BASE_URL="https://<gateway>/v1"
export AGENT_EVALS_OPENAI_COMPAT_API_KEY="<key>"
PYTHONPATH=src python3 src/sandbox_agent_runner.py --agent openai-compatible:<model> --tier extended --output traces/external/sandbox_hosted_<model>.local.jsonl
```

Score any produced file:

```bash
python3 src/gate_check.py --outputs <file> --tier extended \
  --case-path evals/benchmarks/local_public_v2/cases.jsonl --allow-live-local
```

Runs are opt-in evidence producers; outputs stay `.local` (git-ignored) until
reviewed and promoted like all live evidence in this repository.
