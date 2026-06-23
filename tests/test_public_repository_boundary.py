from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PRO_ONLY_TRACKED_PATHS = [
    "sales-demos/",
    "customer-audit-templates/",
    "customer-evidence/",
    "private-evidence/",
    "raw-evidence/",
    "customer-reports/",
    "buyer-notes/",
    "call-notes/",
    "crm/",
    "signed-commitments/",
    "case-study-approvals/",
    "pilot-feedback/",
    "docs/production-readiness-roadmap.md",
    "docs/commercial-use-cases.md",
    "docs/product-positioning.md",
]
REMOVED_PUBLIC_LINKS = [
    "docs/commercial-use-cases.md",
    "docs/product-positioning.md",
    "OPEN_CORE_BOUNDARY.md",
]
PUBLIC_GUARDRAIL_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "PUBLIC_REPO_BOUNDARY.md",
    REPO_ROOT / "docs/public-release-checklist.md",
]


def tracked_files() -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return [
        path
        for path in completed.stdout.splitlines()
        if (REPO_ROOT / path).exists()
    ]


class PublicRepositoryBoundaryTests(unittest.TestCase):
    def test_pro_only_paths_are_not_tracked_in_public_repo(self) -> None:
        files = tracked_files()

        for blocked in PRO_ONLY_TRACKED_PATHS:
            with self.subTest(blocked=blocked):
                self.assertFalse(
                    any(path == blocked.rstrip("/") or path.startswith(blocked) for path in files),
                    f"{blocked} should stay out of the public repository",
                )

    def test_readme_does_not_link_removed_strategy_docs(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        for removed_link in REMOVED_PUBLIC_LINKS:
            with self.subTest(removed_link=removed_link):
                self.assertNotIn(removed_link, readme)

    def test_public_guardrails_exclude_buyer_and_delivery_artifacts(self) -> None:
        combined = "\n".join(path.read_text(encoding="utf-8") for path in PUBLIC_GUARDRAIL_FILES)

        for required in [
            "buyer lists",
            "pricing notes",
            "pilot trackers",
            "customer-delivery templates",
            "customer-specific findings",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, combined)


if __name__ == "__main__":
    unittest.main()
