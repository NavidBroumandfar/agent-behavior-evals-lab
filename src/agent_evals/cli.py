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

    for name in ["check", "test", "lint", "run-baseline", "report", "version"]:
        subparsers.add_parser(name)

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
        return run_command([sys.executable, "src/comparison_report.py"])
    if args.command == "version":
        print(__version__)
        return 0

    raise AssertionError("argparse choices should prevent unsupported commands")


if __name__ == "__main__":
    sys.exit(main())
