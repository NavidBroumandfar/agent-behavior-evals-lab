"""Public-safe per-record verdict ledger for the two LLM-judge rounds.

Why this file exists
--------------------
The judge-with-log (98.2%) and judge-targeted (98.1%) headline numbers were
aggregated from raw judge responses in ``traces/external/*.local.jsonl``, which
are **gitignored** — raw model output never goes into the public repo. That is
the right policy and it had one unintended consequence: on a clean public
checkout the two audit generators found no inputs, scored an empty judge panel,
and wrote a report that *silently claimed the opposite finding* — catch rate
0.0%, decision branch ``gap_is_real`` — with exit code 0. A due-diligence
reviewer running the documented command got a confident, fabricated reversal of
the published result and no warning that anything was missing.

This module closes that without publishing anything it should not. A judge's
raw response has three parts:

- the ``record_id``  — already public (the corpora and both audit JSONs name them),
- the ``verdict``    — one of three literals: supported / unsupported / parse_error,
- ``reason``/``confidence`` — the model's own prose and self-report.

Only the first two are exported here. **No model prose, no rationale, no
confidence score.** The ledger is therefore sufficient to re-derive every
aggregate in both audits — catch rates, twin false positives, Youden's J,
inter-judge agreement, self-consistency flips — and insufficient to reconstruct
what any model actually wrote.

What it does NOT make reproducible
----------------------------------
The ledger reproduces the **aggregation**, not the **measurement**. It does not
re-run the judges, and it cannot: those were live calls to hosted models on a
dated run. A stranger can verify that 98.2% follows from these per-record
verdicts. A stranger cannot verify that these verdicts are what the models
returned — that requires the held-out raw files, whose sha256 is pinned below so
anyone holding them can check the derivation byte-for-byte with ``--verify``.
Say "auditable", not "reproducible", about the measurement itself.

Deterministic, offline, standard-library only.

Exit codes:
    0 - ledger is consistent with every raw file present (or written, with --export)
    1 - a raw file disagrees with the ledger
    2 - usage or input error
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from repo_config import REPO_ROOT
from reporting_utils import write_json_object

LEDGER_PATH = REPO_ROOT / "docs/reproducibility/judge_verdict_ledger.json"
RAW_DIR = REPO_ROOT / "traces/external"

LEDGER_VERSION = "1.0.0"

# The verdict vocabulary. Anything outside it is a bug, not data.
ALLOWED_VERDICTS = ("supported", "unsupported", "parse_error")

# Fields a raw judge row carries that must NEVER reach the ledger: the model's
# own prose and its self-reported confidence. Asserted by test, not by comment.
WITHHELD_RAW_FIELDS = ("reason", "confidence")

# (model, run) pairs the two audits aggregate. Keep in sync with
# judge_with_log_experiment.CLI_JUDGES and judge_targeted_audit.FRONTIER_MODEL.
LEDGER_RUNS: tuple[tuple[str, int], ...] = (
    ("frontier/claude-opus-4-8", 1),
    ("frontier/claude-opus-4-8", 2),
    ("opencode-go/glm-5.2", 1),
    ("opencode-go/glm-5.2", 2),
    ("opencode-go/grok-4.5", 1),
    ("opencode-go/grok-4.5", 2),
    ("opencode-go/kimi-k3", 1),
    ("opencode-go/kimi-k3", 2),
    ("opencode-go/deepseek-v4-pro", 1),
    ("opencode-go/deepseek-v4-pro", 2),
    ("opencode-go/qwen3.7-max", 1),
    ("opencode-go/qwen3.7-max", 2),
    ("frontier/claude-opus-4-8-jt", 1),
    ("frontier/claude-opus-4-8-jt", 2),
)

# Corpora the ledger's record ids belong to. Pinned so a ledger cannot be paired
# with a corpus it was not scored against.
BOUND_CORPORA: tuple[str, ...] = (
    "evals/adversarial/blind_red_team_cases.jsonl",
    "evals/adversarial/judge_targeted_cases.jsonl",
)


class LedgerError(Exception):
    """Ledger input or consistency error."""


def run_key(model: str, run: int) -> str:
    return f"{model}|run{run}"


def raw_path(model: str, run: int) -> Path:
    """Mirror of judge_with_log_experiment.raw_path, without importing it.

    Kept local so the ledger can be exported and verified even if the audit
    module is mid-edit, and so a rename there is caught by a test rather than
    silently producing an empty ledger.
    """

    slug = model.replace("/", "_").replace(".", "").replace("-", "_")
    return RAW_DIR / f"judge_with_log_{slug}_run{run}.local.jsonl"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_raw_verdicts(path: Path) -> dict[str, str]:
    """Extract ONLY record_id -> verdict from a raw judge response file."""

    verdicts: dict[str, str] = {}
    with path.open("r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise LedgerError(f"{path.name}:{lineno}: invalid JSON: {exc.msg}") from exc
            record_id = row.get("record_id")
            verdict = row.get("verdict")
            if not record_id:
                raise LedgerError(f"{path.name}:{lineno}: row has no record_id")
            if verdict not in ALLOWED_VERDICTS:
                raise LedgerError(
                    f"{path.name}:{lineno}: verdict {verdict!r} outside the allowed "
                    f"vocabulary {ALLOWED_VERDICTS}"
                )
            verdicts[str(record_id)] = str(verdict)
    return verdicts


def build_ledger() -> dict[str, Any]:
    """Derive the ledger from whatever raw files are on this machine."""

    runs: dict[str, Any] = {}
    for model, run in LEDGER_RUNS:
        path = raw_path(model, run)
        if not path.exists():
            continue
        verdicts = read_raw_verdicts(path)
        runs[run_key(model, run)] = {
            "model": model,
            "run": run,
            "source_file": str(path.relative_to(REPO_ROOT)),
            "source_sha256": _sha256_file(path),
            "record_count": len(verdicts),
            "verdicts": dict(sorted(verdicts.items())),
        }

    corpora = {}
    for relative in BOUND_CORPORA:
        path = REPO_ROOT / relative
        corpora[relative] = _sha256_file(path) if path.exists() else None

    return {
        "ledger": "judge_verdict_ledger",
        "version": LEDGER_VERSION,
        "purpose": (
            "Per-record judge verdicts for the judge-with-log and judge-targeted "
            "rounds, so both audit aggregates re-derive from a clean public checkout."
        ),
        "contains": (
            "record ids (already public in both corpora) and one categorical verdict "
            "per judge-run-record, from the vocabulary "
            + "/".join(ALLOWED_VERDICTS)
            + "."
        ),
        "withheld": (
            "Model prose and self-reported confidence. The raw responses stay "
            "gitignored under traces/external/; their sha256 is pinned per run so a "
            "holder can verify this derivation with --verify."
        ),
        "reproduces": "the aggregation, not the measurement — see the module docstring.",
        "corpora_sha256": corpora,
        "runs": dict(sorted(runs.items())),
    }


def load_ledger() -> dict[str, Any]:
    if not LEDGER_PATH.exists():
        raise LedgerError(f"ledger missing: {LEDGER_PATH.relative_to(REPO_ROOT)}")
    try:
        return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LedgerError(f"ledger is invalid JSON: {exc.msg}") from exc


def load_ledger_verdicts(model: str, run: int) -> dict[str, str]:
    """Verdicts for one (model, run), or {} when the ledger has no such run.

    Never raises on a missing ledger: this is a fallback path for the audit
    generators, and a missing ledger must surface as "no verdicts" so the
    caller's own emptiness guard produces the error message a reader can act on.
    """

    try:
        ledger = load_ledger()
    except LedgerError:
        return {}
    entry = ledger.get("runs", {}).get(run_key(model, run))
    if not entry:
        return {}
    return dict(entry.get("verdicts", {}))


def verify_against_raw() -> list[str]:
    """Compare the committed ledger to every raw file present on this machine."""

    problems: list[str] = []
    try:
        ledger = load_ledger()
    except LedgerError as exc:
        return [str(exc)]

    entries = ledger.get("runs", {})
    for model, run in LEDGER_RUNS:
        key = run_key(model, run)
        path = raw_path(model, run)
        entry = entries.get(key)
        if not path.exists():
            # No raw file here: nothing to verify against. Absence is normal on a
            # public checkout and is NOT a failure.
            continue
        if entry is None:
            problems.append(f"{key}: raw file present but the ledger has no entry for it")
            continue
        digest = _sha256_file(path)
        if digest != entry.get("source_sha256"):
            problems.append(
                f"{key}: raw file sha256 {digest[:12]}... != ledger "
                f"{str(entry.get('source_sha256'))[:12]}... — the ledger is stale, re-export it"
            )
        raw_verdicts = read_raw_verdicts(path)
        if raw_verdicts != entry.get("verdicts"):
            differing = sorted(
                rid
                for rid in set(raw_verdicts) | set(entry.get("verdicts", {}))
                if raw_verdicts.get(rid) != entry.get("verdicts", {}).get(rid)
            )
            problems.append(
                f"{key}: {len(differing)} verdict(s) differ between the raw file and the "
                f"ledger (first: {differing[:3]})"
            )

    for relative, expected in ledger.get("corpora_sha256", {}).items():
        path = REPO_ROOT / relative
        if not path.exists():
            problems.append(f"bound corpus missing: {relative}")
            continue
        actual = _sha256_file(path)
        if expected is not None and actual != expected:
            problems.append(
                f"bound corpus {relative} changed since the ledger was written "
                f"({str(expected)[:12]}... -> {actual[:12]}...) — the verdicts no longer "
                "describe this corpus"
            )
    return problems


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export or verify the public-safe judge verdict ledger.")
    parser.add_argument(
        "--export",
        action="store_true",
        help="Rebuild the ledger from the raw judge files on this machine (author-side).",
    )
    parser.add_argument("--out", default=str(LEDGER_PATH), help="Ledger output path (with --export).")
    # Verification is what the bare invocation already did. The flag exists because three
    # committed places — this module's docstring, the ledger's own "withheld" field, and the
    # reproducibility page — tell a holder to run `--verify`, and until 2026-08-20 that
    # instruction errored out with "unrecognized arguments". The artifact whose entire job is
    # to be handed to a hostile reviewer opened by telling them to type something that fails.
    # Making the instruction true beats deleting it: an explicit flag is also what a reader
    # reaches for first.
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Recompute the derivation against the raw judge files on this machine "
        "(the default action; accepted explicitly because the docs name this flag).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        if args.export:
            ledger = build_ledger()
            if not ledger["runs"]:
                print(
                    "no raw judge files found under traces/external/ — nothing to export. "
                    "This is expected on a public checkout; the ledger is already committed.",
                    file=sys.stderr,
                )
                return 2
            write_json_object(ledger, Path(args.out))
            total = sum(entry["record_count"] for entry in ledger["runs"].values())
            print(
                f"judge verdict ledger written: {Path(args.out)} "
                f"({len(ledger['runs'])} run(s), {total} verdict(s), no model prose)"
            )
            return 0
        problems = verify_against_raw()
    except LedgerError as exc:
        print(f"judge verdict ledger error: {exc}", file=sys.stderr)
        return 2
    if problems:
        print("judge verdict ledger verification FAILED:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    ledger = load_ledger()
    present = sum(1 for model, run in LEDGER_RUNS if raw_path(model, run).exists())
    print(
        f"judge verdict ledger verified: {len(ledger.get('runs', {}))} run(s) committed, "
        f"{present} raw file(s) available locally to check against"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
