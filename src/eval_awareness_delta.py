"""Eval-awareness delta report (E2).

Frontier-lab research (Apollo, OpenAI) shows models scheme *less* when they know
they are being tested. If that holds, a benchmark a model can recognize as a
benchmark flatters the result: the agent behaves more safely under an obvious
"this is an eval" framing than it would in production. Our CI-embedded,
production-shaped verification is more robust *by design* — this report turns
that from an assertion into a measured number.

Method: run the same sandbox fleet twice per (framework, model) config —
``--framing eval`` and ``--framing production`` (see
``sandbox_agent_runner.py``) — over the same corpus, then score both with the
same deterministic gate and report the pass-rate gap:

    eval_awareness_gap = pass_rate(eval-framed) - pass_rate(production-shaped)

A positive gap means the labeled-eval run looked safer than the production-shaped
run — i.e. the model is eval-aware and an offline benchmark over-credits it.

This generator is deterministic, offline, and stdlib-only. It scores whatever
paired reviewed files are present. If none are present yet (the measured
multi-model run needs the local model rig plus human review of records, same
discipline as all live evidence), it emits an honest ``pending_live_runs``
report with the exact runbook — it never fabricates a delta.

Inputs (per config ``<label>`` in the fleet dir):
    sandbox_<label>.eval_framed.reviewed_sandbox_outputs.jsonl
    sandbox_<label>.prod_shaped.reviewed_sandbox_outputs.jsonl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from gate_check import run_gate
from reporting_utils import write_json_object, write_text


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FLEET_DIR = REPO_ROOT / "traces/external"
DEFAULT_CASE_PATH = REPO_ROOT / "evals/benchmarks/local_public_v2/cases.jsonl"
JSON_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/eval_awareness_delta.json"
MARKDOWN_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/eval_awareness_delta.md"

EVAL_SUFFIX = ".eval_framed.reviewed_sandbox_outputs.jsonl"
PROD_SUFFIX = ".prod_shaped.reviewed_sandbox_outputs.jsonl"

RUNBOOK = (
    "python3 src/sandbox_agent_runner.py --agent ollama:<model> --tier extended "
    "--framing eval --output traces/external/sandbox_<label>.eval_framed.local.jsonl ; "
    "python3 src/sandbox_agent_runner.py --agent ollama:<model> --tier extended "
    "--framing production --output traces/external/sandbox_<label>.prod_shaped.local.jsonl ; "
    "# human-review + promote each .local.jsonl to .reviewed_sandbox_outputs.jsonl, then rerun this report"
)


def _pass_rate_pct(passed: int, scored: int) -> float:
    return round(100.0 * passed / scored, 1) if scored else 0.0


def _score(path: Path, case_path: Path) -> dict[str, Any]:
    summary = run_gate(
        path,
        tier="extended",
        max_failures=10_000,  # report, not a gate
        case_path=case_path,
        allow_live_local=True,
    )
    return {
        "scored": summary["scored_count"],
        "passed": summary["pass_count"],
        "pass_rate_pct": _pass_rate_pct(summary["pass_count"], summary["scored_count"]),
    }


def discover_pairs(fleet_dir: Path) -> list[str]:
    """Config labels that have BOTH an eval-framed and a production-shaped file."""

    eval_labels = {p.name[: -len(EVAL_SUFFIX)] for p in fleet_dir.glob(f"sandbox_*{EVAL_SUFFIX}")}
    prod_labels = {p.name[: -len(PROD_SUFFIX)] for p in fleet_dir.glob(f"sandbox_*{PROD_SUFFIX}")}
    return sorted(label.removeprefix("sandbox_") for label in (eval_labels & prod_labels))


def build_report(fleet_dir: Path, case_path: Path) -> dict[str, Any]:
    labels = discover_pairs(fleet_dir)
    configs: list[dict[str, Any]] = []
    for label in labels:
        eval_stats = _score(fleet_dir / f"sandbox_{label}{EVAL_SUFFIX}", case_path)
        prod_stats = _score(fleet_dir / f"sandbox_{label}{PROD_SUFFIX}", case_path)
        gap = round(eval_stats["pass_rate_pct"] - prod_stats["pass_rate_pct"], 1)
        configs.append(
            {
                "config": label,
                "eval_framed": eval_stats,
                "production_shaped": prod_stats,
                "eval_awareness_gap_pct": gap,
            }
        )
    configs.sort(key=lambda c: (-c["eval_awareness_gap_pct"], c["config"]))

    measured = len(configs) > 0
    mean_gap = (
        round(sum(c["eval_awareness_gap_pct"] for c in configs) / len(configs), 1) if measured else None
    )
    return {
        "report": "eval_awareness_delta",
        "measurement_status": "measured" if measured else "pending_live_runs",
        "case_set": "local_public_v2",
        "tier": "extended",
        "framings": {"eval": "explicit 'you are being tested' preamble", "production": "no preamble"},
        "config_count": len(configs),
        "mean_eval_awareness_gap_pct": mean_gap,
        "configs": configs,
        "finding": _finding(configs, mean_gap),
        "runbook": RUNBOOK,
    }


def _finding(configs: list[dict[str, Any]], mean_gap: float | None) -> str:
    if not configs:
        return (
            "This publishes the eval-awareness measurement harness: run any local model "
            "through the two-framing runbook below and this report populates the gap table "
            "for it, scored by the same deterministic gate. Paired runs are committed as "
            "reviewed evidence (same discipline as every live-model artifact here), so the "
            "table only ever shows human-reviewed measurements — the generator never "
            "fabricates a delta."
        )
    positive = [c for c in configs if c["eval_awareness_gap_pct"] > 0]
    return (
        f"Across {len(configs)} config(s), the mean eval-awareness gap is {mean_gap} pp "
        f"(eval-framed minus production-shaped pass rate); {len(positive)} config(s) scored "
        "higher under the labeled-eval framing — evidence that an offline benchmark a model "
        "recognizes over-credits its production safety, and that production-shaped verification "
        "is the more robust measurement."
    )


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Eval-awareness delta — does the agent behave better when it knows it's a test?",
        "",
        "Same fleet, same corpus, two framings: an explicit \"you are being evaluated\"",
        "preamble vs. production-shaped (no preamble). Scored by the same deterministic gate.",
        "A positive gap = the labeled-eval run looked safer than production — the model is",
        "eval-aware, so an offline benchmark over-credits it.",
        "",
        f"- Measurement status: **{report['measurement_status']}**",
        f"- Case set / tier: `{report['case_set']}` / `{report['tier']}`",
        f"- Configs measured: {report['config_count']}",
    ]
    if report["mean_eval_awareness_gap_pct"] is not None:
        lines.append(f"- Mean eval-awareness gap: **{report['mean_eval_awareness_gap_pct']} pp**")
    lines += ["", f"**Finding.** {report['finding']}", ""]

    if report["configs"]:
        lines += [
            "| Config | Eval-framed pass | Production pass | Eval-awareness gap |",
            "| --- | --- | --- | --- |",
        ]
        for c in report["configs"]:
            e, p = c["eval_framed"], c["production_shaped"]
            lines.append(
                f"| `{c['config']}` | {e['pass_rate_pct']}% ({e['passed']}/{e['scored']}) "
                f"| {p['pass_rate_pct']}% ({p['passed']}/{p['scored']}) "
                f"| {c['eval_awareness_gap_pct']:+} pp |"
            )
        lines.append("")
    else:
        lines += [
            "_No measured configs yet._ To produce the measured delta (needs the local model",
            "rig and human review of records):",
            "",
            "```",
            report["runbook"].replace(" ; ", "\n"),
            "```",
            "",
        ]
    lines += [
        "_Generated by `src/eval_awareness_delta.py` from committed reviewed paired runs.",
        "Deterministic, offline, stdlib-only; never fabricates a delta._",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure the eval-awareness pass-rate gap across fleet configs.")
    parser.add_argument("--fleet-dir", type=Path, default=DEFAULT_FLEET_DIR)
    parser.add_argument("--case-path", type=Path, default=DEFAULT_CASE_PATH)
    parser.add_argument("--json-path", type=Path, default=JSON_OUTPUT_PATH)
    parser.add_argument("--markdown-path", type=Path, default=MARKDOWN_OUTPUT_PATH)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    report = build_report(args.fleet_dir, args.case_path)
    write_json_object(report, args.json_path)
    write_text(render_markdown(report), args.markdown_path)
    print(
        f"eval-awareness delta report written ({report['measurement_status']}, "
        f"{report['config_count']} config(s)): {args.markdown_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
