"""Local developer command wrapper for Agent Behavior Evals Lab.

The wrapper only runs local commands. It does not call model providers, run
agent systems, use credentials, perform network collection, or trigger external
actions.
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_command(command: list[str]) -> int:
    """Run a local command from the repository root."""

    completed = subprocess.run(command, cwd=REPO_ROOT, check=False)
    return completed.returncode


def run_check() -> int:
    """Run the full deterministic local quality gate."""

    return run_command([sys.executable, "scripts/check_all.py"])


def run_tests() -> int:
    """Run the unit test suite."""

    return run_command([sys.executable, "-m", "unittest", "discover", "-s", "tests"])


def run_lint() -> int:
    """Run Ruff when it is installed in the active environment."""

    if importlib.util.find_spec("ruff") is not None:
        return run_command([sys.executable, "-m", "ruff", "check", "."])

    ruff_path = shutil.which("ruff")
    if ruff_path is None:
        print("ruff is not installed. Install dev tooling with: python3 -m pip install '.[dev]'", file=sys.stderr)
        return 2
    return run_command([ruff_path, "check", "."])


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse the developer command."""

    parser = argparse.ArgumentParser(description="Run local Agent Behavior Evals Lab developer commands.")
    parser.add_argument(
        "command",
        choices=["check", "test", "lint"],
        help="Command to run: check runs the full gate, test runs unit tests, lint runs Ruff.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the selected developer command."""

    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.command == "check":
        return run_check()
    if args.command == "test":
        return run_tests()
    if args.command == "lint":
        return run_lint()
    raise AssertionError("argparse choices should prevent unsupported commands")


if __name__ == "__main__":
    sys.exit(main())
