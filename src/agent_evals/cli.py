"""Small command wrapper for the local Agent Behavior Evals Lab workflow."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from agent_evals import __version__


def find_repo_root() -> Path:
    """Find the repository root from the current checkout."""

    candidates = [Path.cwd(), *Path(__file__).resolve().parents]
    for candidate in candidates:
        if (candidate / "scripts/dev.py").exists() and (candidate / "pyproject.toml").exists():
            return candidate
    raise RuntimeError("agent-evals must be run from an Agent Behavior Evals Lab checkout")


def run_command(args: list[str]) -> int:
    """Run a local command from the repository root."""

    repo_root = find_repo_root()
    completed = subprocess.run(args, cwd=repo_root, check=False)
    return completed.returncode


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse CLI arguments."""

    parser = argparse.ArgumentParser(
        prog="agent-evals",
        description="Local-first safety audit commands for Agent Behavior Evals Lab.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in [
        "check",
        "test",
        "lint",
        "run-baseline",
        "report",
        "scorer-reliability",
        "review-coverage-priority",
        "review-coverage-completion",
        "version",
    ]:
        subparsers.add_parser(name)

    review_contract = subparsers.add_parser("scorer-review-contract")
    review_contract.add_argument("--input", type=Path)
    review_contract.add_argument("--output-json", type=Path)
    review_contract.add_argument("--output-markdown", type=Path)
    review_contract.add_argument("--acknowledge-non-gated", action="store_true")

    gate = subparsers.add_parser(
        "gate",
        help="Score saved agent outputs against the public benchmark and fail over threshold.",
    )
    gate.add_argument("--outputs", type=Path, required=True)
    gate.add_argument("--tier", choices=["smoke", "standard", "extended"], default="smoke")
    gate.add_argument("--max-failures", type=int, default=0)
    gate.add_argument("--allow-live-local", action="store_true")
    gate.add_argument("--summary-json", type=Path)
    gate.add_argument("--summary-markdown", type=Path)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the selected command."""

    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.command == "check":
        return run_command([sys.executable, "scripts/dev.py", "check"])
    if args.command == "test":
        return run_command([sys.executable, "scripts/dev.py", "test"])
    if args.command == "lint":
        return run_command([sys.executable, "scripts/dev.py", "lint"])
    if args.command == "run-baseline":
        return run_command([sys.executable, "src/run_eval.py"])
    if args.command == "report":
        report_status = run_command([sys.executable, "src/report_generator.py"])
        if report_status != 0:
            return report_status
        comparison_status = run_command([sys.executable, "src/comparison_report.py"])
        if comparison_status != 0:
            return comparison_status
        reliability_status = run_command([sys.executable, "src/scorer_reliability_report.py"])
        if reliability_status != 0:
            return reliability_status
        priority_status = run_command([sys.executable, "src/review_coverage_priority_plan.py"])
        if priority_status != 0:
            return priority_status
        return run_command([sys.executable, "src/review_coverage_completion_gate.py"])
    if args.command == "scorer-reliability":
        return run_command([sys.executable, "src/scorer_reliability_report.py"])
    if args.command == "review-coverage-priority":
        return run_command([sys.executable, "src/review_coverage_priority_plan.py"])
    if args.command == "review-coverage-completion":
        return run_command([sys.executable, "src/review_coverage_completion_gate.py"])
    if args.command == "scorer-review-contract":
        command = [sys.executable, "src/scorer_review_contract.py"]
        if args.input is not None:
            command.extend(["--input", str(args.input)])
        if args.output_json is not None:
            command.extend(["--output-json", str(args.output_json)])
        if args.output_markdown is not None:
            command.extend(["--output-markdown", str(args.output_markdown)])
        if args.acknowledge_non_gated:
            command.append("--acknowledge-non-gated")
        return run_command(command)
    if args.command == "gate":
        command = [
            sys.executable,
            "src/gate_check.py",
            "--outputs",
            str(args.outputs.resolve()),
            "--tier",
            args.tier,
            "--max-failures",
            str(args.max_failures),
        ]
        if args.allow_live_local:
            command.append("--allow-live-local")
        if args.summary_json is not None:
            command.extend(["--summary-json", str(args.summary_json.resolve())])
        if args.summary_markdown is not None:
            command.extend(["--summary-markdown", str(args.summary_markdown.resolve())])
        return run_command(command)
    if args.command == "version":
        print(__version__)
        return 0

    raise AssertionError("argparse choices should prevent unsupported commands")


if __name__ == "__main__":
    sys.exit(main())
