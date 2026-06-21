"""Command wrapper for the opt-in M57 local text-only model harness."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from live_local_harness import (  # noqa: E402
    DEFAULT_ADAPTER_ID,
    DEFAULT_SPLIT,
    LIVE_LOCAL_REQUIRED_ENV,
    LiveLocalHarnessError,
    build_run_plan,
    display_path,
    env_value_enabled,
    run_live_local_plan,
    write_json_object,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run or plan an opt-in local text-only benchmark.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--plan-only",
        action="store_true",
        help="Build and optionally write a dry-run plan without contacting a local model.",
    )
    mode.add_argument(
        "--live-local",
        action="store_true",
        help="Execute the local model run. Also requires AGENT_EVALS_ENABLE_LIVE_LOCAL.",
    )
    parser.add_argument("--adapter", default=DEFAULT_ADAPTER_ID, help="Local adapter id from the M56 registry.")
    parser.add_argument("--model", required=True, help="Local model name to request from the runtime.")
    parser.add_argument("--split", default=DEFAULT_SPLIT, choices=["smoke", "standard", "extended"])
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "traces/raw/m57_live_local_outputs.local.jsonl",
        help="Ignored raw output JSONL path ending in .local.jsonl.",
    )
    parser.add_argument("--metadata-output", type=Path, help="Ignored run metadata JSON path ending in .local.json.")
    parser.add_argument("--plan-output", type=Path, help="Optional dry-run plan JSON path.")
    parser.add_argument("--endpoint", help="Loopback endpoint override for the selected adapter.")
    parser.add_argument("--timeout-seconds", type=int, help="Per-request timeout override.")
    parser.add_argument("--max-attempts", type=int, default=1, help="Generation attempts per case.")
    parser.add_argument("--max-failures", type=int, default=1, help="Abort after this many failed cases.")
    parser.add_argument("--max-cases", type=int, help="Optional local cap for ad hoc runs.")
    parser.add_argument("--run-id", help="Optional stable run id.")
    parser.add_argument("--created-at", help="Optional UTC timestamp for deterministic plan metadata.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    live_env_present = env_value_enabled(os.environ.get(LIVE_LOCAL_REQUIRED_ENV, ""))

    try:
        plan = build_run_plan(
            adapter_id=args.adapter,
            model=args.model,
            split=args.split,
            output_path=args.output,
            metadata_output_path=args.metadata_output,
            endpoint=args.endpoint,
            run_id=args.run_id,
            created_at=args.created_at,
            timeout_seconds=args.timeout_seconds,
            max_attempts=args.max_attempts,
            max_failures=args.max_failures,
            max_cases=args.max_cases,
            mode="live_local" if args.live_local else "plan_only",
            live_local_flag_present=args.live_local,
            live_local_env_present=live_env_present,
        )
        if args.plan_output:
            write_json_object(plan, args.plan_output)
        if args.plan_only:
            print_plan_summary(plan, args.plan_output)
            return 0

        summary = run_live_local_plan(plan)
    except (LiveLocalHarnessError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"run id: {summary['run_id']}")
    print(f"run status: {summary['run_status']}")
    print(f"raw output path: {summary['raw_output_path']}")
    print(f"run metadata path: {summary['run_metadata_path']}")
    print(f"records written: {summary['records_written']}")
    print(f"succeeded: {summary['succeeded']}")
    print(f"failed: {summary['failed']}")
    print(f"skipped: {summary['skipped']}")
    return 0


def print_plan_summary(plan: dict[str, object], plan_output: Path | None) -> None:
    adapter = plan["adapter"]
    case_set = plan["case_set"]
    outputs = plan["outputs"]
    controls = plan["execution_controls"]
    assert isinstance(adapter, dict)
    assert isinstance(case_set, dict)
    assert isinstance(outputs, dict)
    assert isinstance(controls, dict)

    print(f"run id: {plan['run_id']}")
    print("mode: plan_only")
    print(f"adapter: {adapter['adapter_id']}")
    print(f"runtime: {adapter['runtime']}")
    print(f"model: {adapter['model']}")
    print(f"split: {case_set['benchmark_split']}")
    print(f"planned cases: {case_set['case_count']}")
    print(f"raw output path: {outputs['raw_output_path']}")
    print(f"run metadata path: {outputs['run_metadata_path']}")
    print(f"live-local required flag: {controls['live_local_required_flag']}")
    print(f"live-local required env: {controls['live_local_required_env']}")
    if plan_output:
        print(f"plan output path: {display_path(plan_output)}")
    else:
        print("plan JSON:")
        print(json.dumps(plan, sort_keys=True, indent=2))


if __name__ == "__main__":
    sys.exit(main())
