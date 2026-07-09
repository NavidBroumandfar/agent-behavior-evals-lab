"""Keyword-scorer vs LLM-judge calibration study over reviewed model runs.

Judges every scored record in ``traces/scored/*reviewed_live_local_eval.jsonl``
with the opt-in LLM judge, then aggregates where the deterministic keyword
scorer and the judge disagree. The disagreement table is the scorer's
credibility number: low disagreement supports the deterministic gate; high
disagreement localizes exactly which categories need better rules.

Live judging stays double-gated (``--live-judge`` flag plus
``AGENT_EVALS_ENABLE_LLM_JUDGE=1``) and judge outputs stay git-ignored
(``*.judge.local.jsonl``). Aggregation (``--aggregate-only``) is offline and
deterministic; it reads previously judged files and writes the calibration
report to ``reports/comparisons/``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from llm_judge import (
    DEFAULT_OLLAMA_ENDPOINT,
    LLM_JUDGE_REQUIRED_ENV,
    LlmJudgeError,
    require_live_judge_enabled,
    run_judge,
    transport_for_provider,
)
from reporting_utils import percent, write_json_object, write_text


REPO_ROOT = Path(__file__).resolve().parents[1]
SCORED_GLOB = "*reviewed_live_local_eval.jsonl"
DEFAULT_SCORED_DIR = REPO_ROOT / "traces/scored"
JSON_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/scorer_judge_calibration.json"
MARKDOWN_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/scorer_judge_calibration.md"

# Disagreement labels are from the deterministic scorer's point of view.
SCORER_FALSE_ALARM = "scorer_failed_judge_passed"
SCORER_MISS = "scorer_passed_judge_failed"


class CalibrationStudyError(Exception):
    """Calibration study configuration or input error."""


def judged_path_for(scored_path: Path) -> Path:
    """Return the git-ignored judge output path for one scored run file."""

    stem = scored_path.name.replace(".jsonl", "")
    return scored_path.with_name(f"{stem}.judge.local.jsonl")


def discover_scored_runs(scored_dir: Path, glob: str = SCORED_GLOB) -> list[Path]:
    runs = sorted(scored_dir.glob(glob))
    if not runs:
        raise CalibrationStudyError(f"no scored runs matching {glob} in {scored_dir}")
    return runs


def judge_all_runs(
    scored_dir: Path,
    *,
    provider: str,
    model: str,
    endpoint: str | None,
    env: dict[str, str],
    max_cases: int | None = None,
    max_failures: int = 50,
    transport: Any = None,
    glob: str = SCORED_GLOB,
) -> list[dict[str, Any]]:
    """Run the LLM judge over every scored run; returns per-run judge summaries."""

    summaries = []
    for scored_path in discover_scored_runs(scored_dir, glob):
        run_transport = transport or transport_for_provider(
            provider, model=model, env=env, endpoint=endpoint
        )
        summary = run_judge(
            input_path=scored_path,
            output_path=judged_path_for(scored_path),
            provider=provider,
            model=model,
            transport=run_transport,
            max_failures=max_failures,
            max_cases=max_cases,
        )
        summary["scored_path"] = str(scored_path)
        summaries.append(summary)
        print(
            f"judged {summary['records_judged']} records from {scored_path.name} "
            f"({summary['disagreements_with_baseline']} disagreements)"
        )
    return summaries


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return records


def aggregate_calibration(scored_dir: Path, glob: str = SCORED_GLOB) -> dict[str, Any]:
    """Aggregate keyword-vs-judge agreement from judged .local.jsonl files."""

    runs: list[dict[str, Any]] = []
    total = Counter()
    category_disagreements: Counter = Counter()
    disagreement_examples: list[dict[str, Any]] = []

    for scored_path in discover_scored_runs(scored_dir, glob):
        judged_path = judged_path_for(scored_path)
        if not judged_path.exists():
            raise CalibrationStudyError(
                f"missing judge output {judged_path.name}; run the study with --live-judge first"
            )
        judged = load_jsonl(judged_path)
        if not judged:
            raise CalibrationStudyError(f"{judged_path.name} contains no judged records")

        run_counts = Counter()
        run_id = scored_path.name
        for suffix in (".reviewed_live_local_eval.jsonl", ".fleet_scored.local.jsonl", ".jsonl"):
            if run_id.endswith(suffix):
                run_id = run_id[: -len(suffix)]
                break
        judge_models = {str(entry.get("judge_model", "unknown")) for entry in judged}
        for entry in judged:
            keyword_passed = entry.get("baseline_passed")
            judge_passed = entry.get("passed")
            if keyword_passed is None:
                continue
            run_counts["judged"] += 1
            if keyword_passed == judge_passed:
                run_counts["agree"] += 1
            elif judge_passed and not keyword_passed:
                run_counts[SCORER_FALSE_ALARM] += 1
            else:
                run_counts[SCORER_MISS] += 1
            if keyword_passed != judge_passed:
                category_disagreements[str(entry.get("category", "unknown"))] += 1
                if len(disagreement_examples) < 25:
                    disagreement_examples.append(
                        {
                            "run_id": run_id,
                            "case_id": str(entry.get("case_id", "")),
                            "category": str(entry.get("category", "")),
                            "keyword_passed": keyword_passed,
                            "judge_passed": judge_passed,
                            "keyword_failure_modes": list(entry.get("baseline_failure_modes", [])),
                            "judge_failure_modes": list(entry.get("failure_modes", [])),
                            "judge_rationale": str(entry.get("rationale", ""))[:280],
                        }
                    )

        total.update(run_counts)
        runs.append(
            {
                "run_id": run_id,
                "judged": run_counts["judged"],
                "agree": run_counts["agree"],
                "agreement": percent(run_counts["agree"], run_counts["judged"]),
                SCORER_FALSE_ALARM: run_counts[SCORER_FALSE_ALARM],
                SCORER_MISS: run_counts[SCORER_MISS],
                "judge_models": sorted(judge_models),
            }
        )

    return {
        "report": "scorer_judge_calibration",
        "scored_runs": len(runs),
        "judged_records": total["judged"],
        "agreement_count": total["agree"],
        "agreement_rate": percent(total["agree"], total["judged"]),
        SCORER_FALSE_ALARM: total[SCORER_FALSE_ALARM],
        SCORER_MISS: total[SCORER_MISS],
        "category_disagreements": dict(sorted(category_disagreements.items())),
        "runs": runs,
        "disagreement_examples": disagreement_examples,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Keyword Scorer vs LLM Judge: Calibration Study",
        "",
        "Where the deterministic keyword scorer and an LLM judge disagree on the",
        "same reviewed model outputs. Disagreement labels are from the scorer's",
        "point of view: a *false alarm* means the scorer failed a record the judge",
        "passed; a *miss* means the scorer passed a record the judge failed.",
        "",
        f"- Scored runs: {summary['scored_runs']}",
        f"- Judge model(s): {', '.join(sorted({model for run in summary['runs'] for model in run['judge_models']}))} "
        "(a local judge is itself imperfect; disagreement localizes review-worthy records, it does not adjudicate them)",
        f"- Judged records: {summary['judged_records']}",
        f"- Agreement: {summary['agreement_count']} ({summary['agreement_rate']})",
        f"- Scorer false alarms (scorer FAIL, judge PASS): {summary[SCORER_FALSE_ALARM]}",
        f"- Scorer misses (scorer PASS, judge FAIL): {summary[SCORER_MISS]}",
        "",
        "## Per run",
        "",
        "| Run | Judged | Agreement | Scorer false alarms | Scorer misses |",
        "| --- | --- | --- | --- | --- |",
    ]
    for run in summary["runs"]:
        lines.append(
            f"| `{run['run_id']}` | {run['judged']} | {run['agreement']} "
            f"| {run[SCORER_FALSE_ALARM]} | {run[SCORER_MISS]} |"
        )
    lines.extend(
        [
            "",
            "## Disagreements by category",
            "",
            "| Category | Disagreements |",
            "| --- | --- |",
        ]
    )
    for category, count in summary["category_disagreements"].items():
        lines.append(f"| {category} | {count} |")
    if summary["disagreement_examples"]:
        lines.extend(["", "## Example disagreements (first 25)", ""])
        for example in summary["disagreement_examples"]:
            keyword_verdict = "PASS" if example["keyword_passed"] else "FAIL"
            judge_verdict = "PASS" if example["judge_passed"] else "FAIL"
            lines.append(
                f"- `{example['run_id']}` / `{example['case_id']}` ({example['category']}): "
                f"scorer {keyword_verdict} vs judge {judge_verdict}. "
                f"Judge: {example['judge_rationale']}"
            )
    lines.extend(
        [
            "",
            "_Judge outputs are opt-in, local-only artifacts (`*.judge.local.jsonl`,",
            "git-ignored). This report aggregates them deterministically._",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Keyword-scorer vs LLM-judge calibration study.")
    parser.add_argument("--live-judge", action="store_true", help="Actually call the judge (double-gated).")
    parser.add_argument("--aggregate-only", action="store_true", help="Skip judging; aggregate existing judge outputs.")
    parser.add_argument("--provider", default="ollama", choices=["anthropic", "openai", "ollama"], help="Judge provider.")
    parser.add_argument("--model", default="llama3.2:latest", help="Judge model name.")
    parser.add_argument("--endpoint", default=DEFAULT_OLLAMA_ENDPOINT, help="Ollama endpoint (ollama provider only).")
    parser.add_argument("--scored-dir", type=Path, default=DEFAULT_SCORED_DIR, help="Directory of scored run JSONL files.")
    parser.add_argument("--scored-glob", default=SCORED_GLOB, help="Glob selecting scored run files inside --scored-dir.")
    parser.add_argument("--json-out", type=Path, default=JSON_OUTPUT_PATH, help="Aggregate report JSON output path.")
    parser.add_argument("--md-out", type=Path, default=MARKDOWN_OUTPUT_PATH, help="Aggregate report Markdown output path.")
    parser.add_argument("--max-cases", type=int, default=None, help="Judge at most N records per run (smoke use).")
    parser.add_argument("--skip-report", action="store_true", help="Judge only; do not write the aggregate report.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        if not args.aggregate_only:
            require_live_judge_enabled(live_flag_present=args.live_judge, env=dict(os.environ))
            judge_all_runs(
                args.scored_dir,
                provider=args.provider,
                model=args.model,
                endpoint=args.endpoint,
                env=dict(os.environ),
                max_cases=args.max_cases,
                glob=args.scored_glob,
            )
        if not args.skip_report:
            summary = aggregate_calibration(args.scored_dir, args.scored_glob)
            write_json_object(summary, args.json_out)
            write_text(render_markdown(summary), args.md_out)
            print(
                f"calibration report written: {args.md_out} "
                f"(agreement {summary['agreement_rate']} over {summary['judged_records']} records)"
            )
    except (CalibrationStudyError, LlmJudgeError) as exc:
        print(f"calibration study error: {exc}", file=sys.stderr)
        if isinstance(exc, LlmJudgeError):
            print(
                f"hint: live judging needs --live-judge and {LLM_JUDGE_REQUIRED_ENV}=1",
                file=sys.stderr,
            )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
