"""Tests for repository-level packaging and CI wiring."""

from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class ProjectToolingTests(unittest.TestCase):
    def test_pyproject_declares_project_and_lint_config(self) -> None:
        pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("[project]", pyproject)
        self.assertIn('name = "agent-behavior-evals-lab"', pyproject)
        self.assertIn('requires-python = ">=3.10"', pyproject)
        self.assertIn("[project.optional-dependencies]", pyproject)
        self.assertIn('"ruff>=0.13.0"', pyproject)
        self.assertIn("[tool.ruff]", pyproject)
        self.assertIn("[tool.ruff.lint]", pyproject)

    def test_dev_wrapper_exposes_expected_local_commands(self) -> None:
        dev_script = (REPO_ROOT / "scripts/dev.py").read_text(encoding="utf-8")

        self.assertIn('choices=["check", "test", "lint"]', dev_script)
        self.assertIn('"scripts/check_all.py"', dev_script)
        self.assertIn('"unittest"', dev_script)
        self.assertIn('"ruff"', dev_script)

    def test_ci_runs_lint_and_deterministic_gate(self) -> None:
        workflow = (REPO_ROOT / ".github/workflows/local-quality-gate.yml").read_text(encoding="utf-8")

        self.assertIn('python -m pip install ".[dev]"', workflow)
        self.assertIn("ruff check .", workflow)
        self.assertIn("python scripts/dev.py check", workflow)
        self.assertIn("actions/setup-python@v5", workflow)
        self.assertIn('python-version: "3.11"', workflow)


if __name__ == "__main__":
    unittest.main()
