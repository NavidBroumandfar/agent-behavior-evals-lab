"""Run real LangGraph ReAct agents through the mock-tool sandbox.

Framework fleet runner (roadmap Build 7 framework track). Requires the
optional fleet environment — see examples/fleet/README.md:

    python3 -m venv .fleet-venv
    .fleet-venv/bin/pip install langgraph langchain-core langchain-ollama
    .fleet-venv/bin/python examples/fleet/run_langgraph_fleet.py --model llama3.2:latest

Opt-in evidence producer: a real LangGraph agent (planner loop, framework
tool dispatch) drives the sandbox tools; outputs are live-local sandbox
records (git-ignored .local files) until reviewed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from framework_sandbox_bindings import langchain_tools  # noqa: E402
from ollama_tool_agent import SYSTEM_PROMPT  # noqa: E402
from sandbox_agent_runner import run_sandbox_fleet  # noqa: E402
from sandbox_tools import SandboxToolbox  # noqa: E402


def make_langgraph_agent(model_name: str, endpoint: str):
    from langchain_ollama import ChatOllama
    from langgraph.prebuilt import create_react_agent

    def agent(prompt: str, toolbox: SandboxToolbox) -> str:
        model = ChatOllama(model=model_name, base_url=endpoint, temperature=0)
        graph = create_react_agent(model, langchain_tools(toolbox), prompt=SYSTEM_PROMPT)
        result = graph.invoke(
            {"messages": [("user", prompt)]},
            config={"recursion_limit": 12},
        )
        final = result["messages"][-1]
        content = final.content
        if isinstance(content, list):
            content = " ".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )
        return str(content)

    return agent


def main() -> int:
    parser = argparse.ArgumentParser(description="LangGraph agents through the sandbox.")
    parser.add_argument("--model", required=True, help="Ollama model backing the LangGraph agent.")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--tier", default="extended", choices=["smoke", "standard", "extended"])
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    safe_model = args.model.replace(":", "-").replace("/", "-")
    output_path = args.output or REPO_ROOT / f"traces/external/sandbox_langgraph_{safe_model}.local.jsonl"

    count = run_sandbox_fleet(
        make_langgraph_agent(args.model, args.endpoint),
        agent_name=f"langgraph-{safe_model}",
        tier=args.tier,
        output_path=output_path,
        live_model_execution=True,
        on_case=lambda case_id: print(f"case {case_id}", flush=True),
    )
    print(f"langgraph fleet complete: {count} record(s) -> {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
