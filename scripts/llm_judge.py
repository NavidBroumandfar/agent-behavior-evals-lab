"""Command wrapper for the opt-in LLM-as-judge scorer."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from llm_judge import (  # noqa: E402
    DEFAULT_OLLAMA_ENDPOINT,
    SUPPORTED_PROVIDERS,
    LlmJudgeError,
    build_judge_prompt,
    load_jsonl_records,
    require_live_judge_enabled,
    run_judge,
    transport_for_provider,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Judge normalized trace records with an LLM rubric judge.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--plan-only",
        action="store_true",
        help="Print the judge prompts that would be sent without contacting any provider.",
    )
    mode.add_argument(
        "--live-judge",
        action="store_true",
        help="Execute live judging. Also requires AGENT_EVALS_ENABLE_LLM_JUDGE.",
    )
    parser.add_argument("--provider", required=True, choices=sorted(SUPPORTED_PROVIDERS))
    parser.add_argument("--model", required=True, help="Judge model name for the selected provider.")
    parser.add_argument("--input", type=Path, required=True, help="Normalized/scored trace JSONL to judge.")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "traces/raw/llm_judge_outputs.local.jsonl",
        help="Ignored judge output JSONL path ending in .local.jsonl.",
    )
    parser.add_argument("--endpoint", help="Loopback endpoint override for the ollama provider.")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--max-failures", type=int, default=1, help="Abort after this many failed judgments.")
    parser.add_argument("--max-cases", type=int, help="Optional cap for ad hoc runs.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        if args.plan_only:
            records = load_jsonl_records(args.input)
            if args.max_cases is not None:
                records = records[: args.max_cases]
            print(f"provider: {args.provider}")
            print(f"model: {args.model}")
            print(f"records to judge: {len(records)}")
            if records:
                print("first prompt preview:")
                print(build_judge_prompt(records[0]))
            return 0

        require_live_judge_enabled(live_flag_present=args.live_judge, env=dict(os.environ))
        transport = transport_for_provider(
            args.provider,
            model=args.model,
            env=dict(os.environ),
            endpoint=args.endpoint or DEFAULT_OLLAMA_ENDPOINT,
            timeout_seconds=args.timeout_seconds,
        )
        summary = run_judge(
            input_path=args.input,
            output_path=args.output,
            provider=args.provider,
            model=args.model,
            transport=transport,
            max_failures=args.max_failures,
            max_cases=args.max_cases,
        )
    except (LlmJudgeError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    for key, value in summary.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
