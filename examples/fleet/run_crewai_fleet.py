"""Run real CrewAI agents through the mock-tool sandbox.

Framework fleet runner. CrewAI reaches local models through LiteLLM's Ollama
support, so no hosted account or key is used:

    python3.12 -m venv .crew-venv          # CrewAI needs <=3.13 (tiktoken wheels)
    .crew-venv/bin/pip install crewai
    .crew-venv/bin/python examples/fleet/run_crewai_fleet.py --model llama3.2:latest

Opt-in evidence producer; outputs are live-local sandbox records
(git-ignored .local files) until reviewed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from framework_sandbox_bindings import crewai_tools  # noqa: E402
from ollama_tool_agent import SYSTEM_PROMPT  # noqa: E402
from sandbox_agent_runner import run_sandbox_fleet  # noqa: E402
from sandbox_tools import SandboxToolbox  # noqa: E402


def make_crewai_agent(model_name: str, endpoint: str):
    from crewai import Agent, Crew, LLM, Task

    def agent(prompt: str, toolbox: SandboxToolbox) -> str:
        llm = LLM(model=f"ollama/{model_name}", base_url=endpoint, temperature=0)
        worker = Agent(
            role="Workspace assistant",
            goal="Help with the user's request while following safe agent behavior.",
            backstory=SYSTEM_PROMPT,
            llm=llm,
            tools=crewai_tools(toolbox),
            verbose=False,
            max_iter=8,
        )
        task = Task(
            description=prompt,
            expected_output="Your final answer to the user.",
            agent=worker,
        )
        crew = Crew(agents=[worker], tasks=[task], verbose=False)
        try:
            result = crew.kickoff()
        except Exception as exc:  # noqa: BLE001 - framework flakiness is itself a result
            return f"(crewai runtime error: the agent produced no usable answer: {exc})"
        return str(getattr(result, "raw", result) or "")

    return agent


def main() -> int:
    parser = argparse.ArgumentParser(description="CrewAI agents through the sandbox.")
    parser.add_argument("--model", required=True, help="Ollama model backing the CrewAI agent.")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--tier", default="extended", choices=["smoke", "standard", "extended"])
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    safe_model = args.model.replace(":", "-").replace("/", "-")
    output_path = args.output or REPO_ROOT / f"traces/external/sandbox_crewai_{safe_model}.local.jsonl"

    count = run_sandbox_fleet(
        make_crewai_agent(args.model, args.endpoint),
        agent_name=f"crewai-{safe_model}",
        tier=args.tier,
        output_path=output_path,
        live_model_execution=True,
        on_case=lambda case_id: print(f"case {case_id}", flush=True),
    )
    print(f"crewai fleet complete: {count} record(s) -> {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
