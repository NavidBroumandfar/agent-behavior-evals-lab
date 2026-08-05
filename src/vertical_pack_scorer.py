"""Generic two-axis scorer for any vertical red-team pack.

This module adds *nothing* to the scoring logic — it reuses
``src/finance_redteam_scorer.py`` verbatim, because that scorer is already
vertical-neutral: ``score_case`` reads only ``case['kind']`` and
``case['scoring']``, never anything finance-specific. All this module does is
resolve a pack directory and label the report by pack name.

It never touches ``src/scorers.py`` (no ledger cascade). Deterministic, offline,
stdlib-only.

    python3 -m vertical_pack_scorer --pack evals/benchmarks/healthcare_admin
    python3 -m vertical_pack_scorer --pack devops_sre --logs run.jsonl --md-out report.md
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from repo_config import REPO_ROOT
from reporting_utils import write_json_object, write_text

import finance_redteam_scorer as frs  # reuse score_suite / load_cases / load_logs


def _resolve_pack_dir(pack: str) -> Path:
    """Accept a bare slug, a benchmarks-relative path, or a repo-relative path."""

    candidate = Path(pack)
    if candidate.is_absolute():
        return candidate
    for base in (REPO_ROOT / "evals/benchmarks" / pack, REPO_ROOT / pack):
        if (base / "cases.jsonl").exists():
            return base
    # Fall back to the benchmarks location even if absent, for a clear error.
    return REPO_ROOT / "evals/benchmarks" / pack


def score_pack(pack_dir: Path, logs_path: Path | None) -> dict[str, Any]:
    """Score one pack's corpus against a per-case tool log (or the inert baseline).

    A missing/empty log is the inert-agent condition: ~100% safety but low
    appropriateness and 0% control-pass — the property that proves a pack cannot
    be aced by doing nothing.
    """

    cases = frs.load_cases(pack_dir / "cases.jsonl")
    logs = frs.load_logs(logs_path)
    report = frs.score_suite(cases, logs)
    report["report"] = f"{pack_dir.name}_score"
    report["pack"] = pack_dir.name
    return report


def _render(report: dict[str, Any]) -> str:
    ax = report["axes"]
    return "\n".join(
        [
            f"# {report['pack']} red-team score",
            "",
            f"- Cases: {report['cases_scored']} "
            f"({report['temptations']} temptation, {report['controls']} control)",
            f"- **Safety:** {ax['safety_rate']}%  (no executed violation)",
            f"- **Appropriateness:** {ax['appropriateness_rate']}%  "
            f"({ax['failed_to_act']} failed_to_act)",
            f"- **Control pass:** {ax['control_pass_rate']}%  "
            f"({ax['over_refusals']} over-refusals)",
            "",
            report["reading"],
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", required=True, help="pack slug or path under evals/benchmarks/")
    parser.add_argument("--logs", default=None, help="JSONL of {case_id, tool_events}; omitted = inert baseline")
    parser.add_argument("--json-out", default=None)
    parser.add_argument("--md-out", default=None)
    args = parser.parse_args(argv)

    pack_dir = _resolve_pack_dir(args.pack)
    report = score_pack(pack_dir, Path(args.logs) if args.logs else None)

    if args.json_out:
        write_json_object(report, Path(args.json_out))
    text = _render(report)
    if args.md_out:
        write_text(text + "\n", Path(args.md_out))
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
