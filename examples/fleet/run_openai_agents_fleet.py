"""Run real OpenAI Agents SDK agents through the mock-tool sandbox.

Framework fleet runner. Local models are served through Ollama's
OpenAI-compatible endpoint, so no OpenAI account or key is used:

    .fleet-venv/bin/pip install openai-agents
    .fleet-venv/bin/python examples/fleet/run_openai_agents_fleet.py --model llama3.2:latest

Opt-in evidence producer; outputs are live-local sandbox records
(git-ignored .local files) until reviewed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from framework_sandbox_bindings import openai_agents_tools  # noqa: E402
from ollama_tool_agent import SYSTEM_PROMPT  # noqa: E402
from sandbox_agent_runner import run_sandbox_fleet  # noqa: E402
from sandbox_tools import SandboxToolbox  # noqa: E402


def make_openai_agents_agent(model_name: str, endpoint: str):
    from agents import Agent, OpenAIChatCompletionsModel, Runner, set_tracing_disabled
    from openai import AsyncOpenAI

    set_tracing_disabled(True)  # no telemetry; local-only run

    def agent(prompt: str, toolbox: SandboxToolbox) -> str:
        client = AsyncOpenAI(base_url=f"{endpoint}/v1", api_key="ollama-local")
        sdk_agent = Agent(
            name="sandbox-agent",
            instructions=SYSTEM_PROMPT,
            model=OpenAIChatCompletionsModel(model=model_name, openai_client=client),
            tools=openai_agents_tools(toolbox),
        )
        result = Runner.run_sync(sdk_agent, prompt, max_turns=8)
        return str(result.final_output or "")

    return agent


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenAI Agents SDK agents through the sandbox.")
    parser.add_argument("--model", required=True, help="Ollama model behind the OpenAI-compatible endpoint.")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--tier", default="extended", choices=["smoke", "standard", "extended"])
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    safe_model = args.model.replace(":", "-").replace("/", "-")
    output_path = args.output or REPO_ROOT / f"traces/external/sandbox_openai-agents_{safe_model}.local.jsonl"

    count = run_sandbox_fleet(
        make_openai_agents_agent(args.model, args.endpoint),
        agent_name=f"openai-agents-{safe_model}",
        tier=args.tier,
        output_path=output_path,
        live_model_execution=True,
        on_case=lambda case_id: print(f"case {case_id}", flush=True),
    )
    print(f"openai-agents fleet complete: {count} record(s) -> {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
