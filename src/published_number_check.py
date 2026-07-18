"""Verify every number this repo publishes still matches its committed artifact.

Numbers drift. A figure gets corrected in a report and survives in the README,
or a generator is re-run and the prose is not — and the first person to notice
is a skeptical evaluator reproducing the claim, which is the worst possible
moment. That has already happened here twice.

This check closes it structurally. Each published claim below names:

- the artifact that PRODUCES the number (a committed generator output),
- the field in that artifact,
- the documents that QUOTE it,
- ``quotes``: regexes with ONE capture group, matching every place the doc
  states this number, and
- ``retired``: values the claim used to have, which must no longer appear.

**Every capture must equal the artifact's current value** — presence-checking
alone is not enough, because a doc that states the number twice can drift in
one place and still contain the right value in the other. Wired into the repo
gate, so a number cannot silently drift again.

Deterministic and standard-library only.

Exit codes:
    0 - every published number matches its artifact
    1 - a number is stale, missing, or a retired value survives
    2 - usage or input error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

# Published claims. Add a row when a number reaches a public document; move the
# old value into `retired` when it changes.
PUBLISHED_CLAIMS: tuple[dict[str, Any], ...] = (
    {
        "id": "self_authored_catch_rate",
        "artifact": "reports/comparisons/verifier_evasion_audit.json",
        "field": "catch_rate",
        "docs": ("README.md",),
        "quotes": (r"(\d+\.\d)% catch on the \*\*self-authored\*\*", r"\((\d+\.\d)% on the corpus its own author wrote"),
        "retired": ("91.7%", "92.9%", "93.2%", "93.5%", "97.8%"),
    },
    {
        "id": "blind_catch_rate",
        "artifact": "reports/comparisons/blind_red_team_audit.json",
        "field": "catch_rate",
        "docs": ("README.md",),
        "quotes": (r"\*\*(\d+\.\d)% catch \(\d+/\d+\)", r"it catches \*\*(\d+\.\d)%\*\*"),
        "retired": (),
    },
    {
        "id": "blind_lying_records",
        "artifact": "reports/comparisons/blind_red_team_audit.json",
        "field": "lying_records",
        "docs": ("README.md",),
        "quotes": (r"catch \(\d+/(\d+)\)",),
        "retired": (),
    },
    {
        "id": "keyword_judge_agreement",
        "artifact": "reports/comparisons/scorer_judge_calibration.json",
        "field": "agreement_rate",
        "docs": ("README.md",),
        "quotes": (r"(\d+\.\d)% agreement across 6 local models", r"(\d+\.\d)% judge agreement over 700"),
        "retired": ("55.1%",),
    },
    {
        "id": "keyword_false_alarms",
        "artifact": "reports/comparisons/scorer_judge_calibration.json",
        "field": "scorer_failed_judge_passed",
        "docs": ("README.md",),
        "quotes": (r"over-strict by (\d+) false alarms",),
        "retired": ("290",),
    },
    {
        "id": "fleet_structural_agreement",
        "artifact": "reports/comparisons/sandbox_fleet_scorer_judge_calibration.json",
        "field": "agreement_rate",
        "docs": ("README.md",),
        "quotes": (r"(\d+\.\d)% agreement across 8 framework",),
        "retired": ("69.7%",),
    },
)

# The blind corpus is frozen: its hash must match the manifest recorded before
# any fix, or the pre/post-fix comparison is meaningless.
FROZEN_CORPORA: tuple[dict[str, str], ...] = (
    {
        "corpus": "evals/adversarial/blind_red_team_cases.jsonl",
        "manifest": "evals/adversarial/blind_red_team_manifest.json",
        "manifest_field": "corpus_sha256",
    },
)


class PublishedNumberError(Exception):
    """A published number no longer matches its artifact."""


def _load_artifact(relative: str) -> dict[str, Any]:
    path = REPO_ROOT / relative
    if not path.exists():
        raise PublishedNumberError(f"artifact missing: {relative}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PublishedNumberError(f"{relative}: invalid JSON: {exc.msg}") from exc


def _corpus_sha256(relative: str) -> str:
    import hashlib

    path = REPO_ROOT / relative
    if not path.exists():
        raise PublishedNumberError(f"corpus missing: {relative}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_published_numbers() -> list[str]:
    """Return a list of problems; empty means every published number is current."""

    problems: list[str] = []
    doc_cache: dict[str, str] = {}

    def doc_text(name: str) -> str:
        if name not in doc_cache:
            path = REPO_ROOT / name
            doc_cache[name] = path.read_text(encoding="utf-8") if path.exists() else ""
            if not doc_cache[name]:
                problems.append(f"document missing or empty: {name}")
        return doc_cache[name]

    for claim in PUBLISHED_CLAIMS:
        try:
            artifact = _load_artifact(claim["artifact"])
        except PublishedNumberError as exc:
            problems.append(str(exc))
            continue
        if claim["field"] not in artifact:
            problems.append(f"{claim['id']}: field {claim['field']!r} not in {claim['artifact']}")
            continue
        current = str(artifact[claim["field"]])
        for doc in claim["docs"]:
            text = doc_text(doc)
            if not text:
                continue
            quotes = claim.get("quotes", ())
            if not quotes:
                if current not in text:
                    problems.append(
                        f"{claim['id']}: {doc} does not quote the current value {current!r} "
                        f"from {claim['artifact']}:{claim['field']}"
                    )
            else:
                found_any = False
                for pattern in quotes:
                    for match in re.finditer(pattern, text):
                        found_any = True
                        stated = match.group(1)
                        if stated.rstrip("%") != current.rstrip("%"):
                            problems.append(
                                f"{claim['id']}: {doc} states {stated!r} but "
                                f"{claim['artifact']}:{claim['field']} is {current!r} "
                                f"(context: {match.group(0)[:60]!r})"
                            )
                if not found_any:
                    problems.append(
                        f"{claim['id']}: {doc} contains no recognizable statement of this number "
                        f"(expected one of {quotes}) — prose changed shape, update the claim registry"
                    )
            for stale in claim["retired"]:
                if stale in text:
                    problems.append(
                        f"{claim['id']}: {doc} still contains the retired value {stale!r} "
                        f"(current is {current!r})"
                    )

    for frozen in FROZEN_CORPORA:
        try:
            manifest = _load_artifact(frozen["manifest"])
            actual = _corpus_sha256(frozen["corpus"])
        except PublishedNumberError as exc:
            problems.append(str(exc))
            continue
        expected = str(manifest.get(frozen["manifest_field"], ""))
        if actual != expected:
            problems.append(
                f"frozen corpus {frozen['corpus']} changed after freeze "
                f"(manifest {expected[:12]}..., actual {actual[:12]}...) — "
                "pre/post-fix comparisons against it are no longer valid"
            )

    return problems


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify published numbers match their committed artifacts.")
    parser.add_argument("--self-check", action="store_true", help="Run the check (default).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    parse_args(sys.argv[1:] if argv is None else argv)
    try:
        problems = check_published_numbers()
    except PublishedNumberError as exc:
        print(f"published number check error: {exc}", file=sys.stderr)
        return 2
    if problems:
        print("published number check FAILED:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print(f"published number check passed: {len(PUBLISHED_CLAIMS)} claims match their artifacts; frozen corpora intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
