"""Structural scorer vs LLM judge calibration over the real-agent sandbox fleet.

The 700-record model study (``scorer_judge_calibration``) calibrates the
deterministic *keyword* scorer against an LLM judge on model outputs. This is its
real-*agent* analogue: it calibrates the *structural* tool-event verifier
(``structural_tool_verifier.score_response_with_evidence``) against the same
text-only judge on the sandbox fleet — real agents (``ollama``/``langgraph``/
``crewai``/``openai-agents`` x local models) driven through a mock-tool sandbox
(``sandbox_tools``) that records every tool call as a ``tool_events`` entry.

Why this is the credibility analogue, not a second keyword study: the baseline
being calibrated here is *structural* (claims checked against the recorded
tool-call log), which is exactly the agent-specific signal a model eval cannot
produce. And because the judge is text-only and never reads ``tool_events``, a
structural-FAIL / judge-PASS disagreement here is usually *not* a scorer error:
it is a fabricated-tool-use or unauthorized-action case the text-only judge is
structurally blind to. Counting those is the measured added value of structural
agent evaluation over text-only judging.

Judging stays double-gated (``--live-judge`` plus ``AGENT_EVALS_ENABLE_LLM_JUDGE``)
and scored/judged raw outputs stay git-ignored (``*.local.jsonl``). Only the
aggregated report
(``reports/comparisons/sandbox_fleet_scorer_judge_calibration.{json,md}``) is
committed. Aggregation is offline and deterministic.

Reuses (does not reimplement): ``gate_check.load_benchmark_cases``,
``structural_tool_verifier.score_response_with_evidence``, ``llm_judge.run_judge``,
and ``scorer_judge_calibration.aggregate_calibration`` / ``judged_path_for``.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from gate_check import GateCheckError, load_benchmark_cases
from llm_judge import (
    DEFAULT_OLLAMA_ENDPOINT,
    LLM_JUDGE_REQUIRED_ENV,
    LlmJudgeError,
    require_live_judge_enabled,
    run_judge,
    transport_for_provider,
)
from reporting_utils import percent, write_json_object, write_text
from scorer_judge_calibration import (
    SCORER_FALSE_ALARM,
    SCORER_MISS,
    aggregate_calibration,
    judged_path_for,
    load_jsonl,
)
from structural_tool_verifier import destructive_events, score_response_with_evidence
from trace_writer import write_jsonl

REPO_ROOT = Path(__file__).resolve().parents[1]
FLEET_DIR = REPO_ROOT / "traces/external"
FLEET_GLOB = "*reviewed_sandbox_outputs.jsonl"
CASE_PATH = REPO_ROOT / "evals/benchmarks/local_public_v2/cases.jsonl"
DEFAULT_TIER = "extended"
SCORED_DIR = REPO_ROOT / "traces/scored"
SCORED_SUFFIX = ".fleet_scored.local.jsonl"
SCORED_GLOB = "*" + SCORED_SUFFIX
JSON_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/sandbox_fleet_scorer_judge_calibration.json"
MARKDOWN_OUTPUT_PATH = REPO_ROOT / "reports/comparisons/sandbox_fleet_scorer_judge_calibration.md"

# Failure modes that can ONLY come from tool-event evidence. A text-only judge
# never reads tool_events, so these are always invisible to it.
EVIDENCE_ONLY_MODES = ("unverified_tool_claim", "unsupported_tool_claim")
# ``missing_approval_gate`` is ambiguous: the keyword scorer emits it when the
# output lacks an approval phrase (text-visible, the judge CAN see it), while the
# structural layer emits it when a destructive tool call actually executed
# (evidence-only). So it counts as an evidence-only catch only when a destructive
# event is present — decided per record in ``_is_evidence_only``, not by mode name.


class FleetCalibrationError(Exception):
    """Fleet calibration configuration or input error."""


def agent_label(fleet_path: Path) -> str:
    return (
        fleet_path.name.removesuffix(".reviewed_sandbox_outputs.jsonl")
        .removesuffix(".local.jsonl")
        .removeprefix("sandbox_")
    )


def scored_path_for(fleet_path: Path) -> Path:
    # Label matches sandbox_fleet_pilot.md (framework_model), so the two reports line up.
    return SCORED_DIR / f"{agent_label(fleet_path)}{SCORED_SUFFIX}"


def emit_scored_fleet(fleet_dir: Path, case_path: Path, tier: str) -> list[Path]:
    """Score each fleet output file with the structural verifier; write judge-ready scored JSONL.

    Each scored record carries both the structural verdict (``passed`` +
    ``failure_modes``, from tool-event evidence) and the text fields the judge
    reads (``model_output`` + ``category`` + ``user_prompt`` + rubric context),
    so the existing judge and aggregation run over it unchanged.
    """

    fleet_paths = sorted(fleet_dir.glob(FLEET_GLOB))
    if not fleet_paths:
        raise FleetCalibrationError(f"no fleet output files matching {FLEET_GLOB} in {fleet_dir}")
    _all_cases, tier_cases = load_benchmark_cases(case_path, tier)

    written: list[Path] = []
    for fleet_path in fleet_paths:
        label = agent_label(fleet_path)
        scored: list[dict[str, Any]] = []
        for record in load_jsonl(fleet_path):
            case_id = str(record["case_id"])
            case = tier_cases.get(case_id)
            if case is None:
                continue  # out of tier; matches gate_check's tier filter
            output_text = str(record["output_text"])
            response = {
                "case_id": case_id,
                "profile_name": str(record.get("target_profile", "unknown")),
                "category": str(case.get("category", "unknown")),
                "output_text": output_text,
            }
            score = score_response_with_evidence(case, response, record.get("tool_events"))
            scored.append(
                {
                    "run_id": label,
                    "case_id": case_id,
                    "profile_name": str(record.get("target_profile", "unknown")),
                    "category": str(case.get("category", "unknown")),
                    "risk_area": str(case.get("risk_area", "unknown")),
                    "severity": str(case.get("severity", "unknown")),
                    "policy_refs": list(case.get("policy_refs", [])),
                    "user_prompt": str(case.get("user_prompt", "")),
                    "expected_behavior": str(case.get("expected_behavior", "")),
                    "scoring_notes": str(case.get("scoring_notes", "")),
                    # model_output is what the judge reads; keep output_text too.
                    "model_output": output_text,
                    "output_text": output_text,
                    "passed": bool(score["passed"]),
                    "score": float(score["score"]),
                    "failure_modes": list(score["failure_modes"]),
                    "rationale": str(score["rationale"]),
                    "tool_claim_verification": score.get("tool_claim_verification", {}),
                    "tool_events": list(record.get("tool_events", [])),
                }
            )
        if not scored:
            raise FleetCalibrationError(f"{fleet_path.name}: no in-tier records to score for tier {tier!r}")
        out_path = scored_path_for(fleet_path)
        write_jsonl(scored, out_path)
        written.append(out_path)
        print(f"scored {len(scored)} records from {fleet_path.name} -> {out_path.name}")
    return written


def judge_fleet(
    scored_paths: list[Path],
    *,
    provider: str,
    model: str,
    endpoint: str | None,
    env: dict[str, str],
    max_failures: int,
    max_cases: int | None,
) -> None:
    """Run the text-only LLM judge over every scored fleet file.

    The double-gate (``--live-judge`` flag + ``AGENT_EVALS_ENABLE_LLM_JUDGE``) is
    enforced by the caller before this runs.
    """

    for scored_path in scored_paths:
        transport = transport_for_provider(provider, model=model, env=env, endpoint=endpoint)
        summary = run_judge(
            input_path=scored_path,
            output_path=judged_path_for(scored_path),
            provider=provider,
            model=model,
            transport=transport,
            max_failures=max_failures,
            max_cases=max_cases,
        )
        print(
            f"judged {summary['records_judged']} records from {scored_path.name} "
            f"({summary['disagreements_with_baseline']} disagreements)"
        )


def _is_evidence_only(scored_record: dict[str, Any]) -> bool:
    """True if the structural FAIL was driven by tool-event evidence a text-only judge cannot see.

    That means an unverified/unsupported tool claim, or an approval-gated
    ``missing_approval_gate`` where a destructive tool call actually executed. A
    ``missing_approval_gate`` with no destructive event is the keyword scorer's
    text-visible finding (no approval phrase) and does not count.
    """

    modes = set(scored_record.get("failure_modes", []))
    if modes.intersection(EVIDENCE_ONLY_MODES):
        return True
    if "missing_approval_gate" in modes and destructive_events(scored_record.get("tool_events", [])):
        return True
    return False


def analyze_structural_catches(scored_dir: Path, glob: str) -> dict[str, Any]:
    """Break the two disagreement directions down across all judged fleet files.

    The headline is ``evidence_only_catches``: structural-FAIL/judge-PASS records
    the structural layer failed on tool-event evidence the text-only judge cannot
    see (fabricated tool use, unsupported success, or a destructive call executed
    in an approval-gated case). That count is the measured value of structural
    agent evaluation over text-only judging. Classification is per record via the
    recorded ``tool_events`` (joined from the scored file), not by mode name,
    because ``missing_approval_gate`` is ambiguous.
    """

    fa_modes: Counter = Counter()  # structural FAIL, judge PASS -> structural failure modes
    miss_modes: Counter = Counter()  # structural PASS, judge FAIL -> judge failure modes
    fa_total = 0
    miss_total = 0
    evidence_only_catches = 0
    approval_gate_with_destructive = 0  # subset of missing_approval_gate that is evidence-only

    for scored_path in sorted(scored_dir.glob(glob)):
        judged_path = judged_path_for(scored_path)
        if not judged_path.exists():
            raise FleetCalibrationError(
                f"missing judge output {judged_path.name}; run with --live-judge first"
            )
        scored_by_id = {str(rec.get("case_id")): rec for rec in load_jsonl(scored_path)}
        for entry in load_jsonl(judged_path):
            structural_passed = entry.get("baseline_passed")
            judge_passed = entry.get("passed")
            if structural_passed is None:
                continue
            if not structural_passed and judge_passed:
                fa_total += 1
                modes = list(entry.get("baseline_failure_modes", []))
                fa_modes.update(modes)
                scored_record = scored_by_id.get(str(entry.get("case_id")), {})
                if _is_evidence_only(scored_record):
                    evidence_only_catches += 1
                if "missing_approval_gate" in modes and destructive_events(
                    scored_record.get("tool_events", [])
                ):
                    approval_gate_with_destructive += 1
            elif structural_passed and not judge_passed:
                miss_total += 1
                miss_modes.update(entry.get("failure_modes", []))

    return {
        "scorer_failed_judge_passed_total": fa_total,
        "evidence_only_catches": evidence_only_catches,
        "evidence_only_catch_rate": percent(evidence_only_catches, fa_total),
        "approval_gate_with_executed_destructive_call": approval_gate_with_destructive,
        "scorer_failed_judge_passed_by_mode": dict(sorted(fa_modes.items())),
        "scorer_passed_judge_failed_total": miss_total,
        "scorer_passed_judge_failed_by_mode": dict(sorted(miss_modes.items())),
    }


def panel_judged_paths(scored_path: Path) -> list[Path]:
    """Per-judge output variants for one scored file: <stem>.judge.<tag>.local.jsonl.

    Excludes the canonical single-judge path (<stem>.judge.local.jsonl) so the
    panel only reads explicitly tagged judge outputs.
    """

    stem = scored_path.name.replace(".jsonl", "")
    canonical = judged_path_for(scored_path).name
    return sorted(
        path
        for path in scored_path.parent.glob(f"{stem}.judge.*.local.jsonl")
        if path.name != canonical
    )


def analyze_judge_panel(scored_dir: Path, glob: str) -> dict[str, Any] | None:
    """Aggregate every tagged judge's verdicts against the structural baseline.

    Returns None when no tagged judge outputs exist (single-judge mode). The
    headline is whether the evidence-only catches survive a panel: records the
    structural layer failed on tool_events where EVERY text-only judge passed
    the output text are the strongest form of the added-value claim.
    """

    per_judge: dict[str, Counter] = {}
    majority = Counter()
    catch_votes: list[dict[str, Any]] = []

    for scored_path in sorted(scored_dir.glob(glob)):
        variants = panel_judged_paths(scored_path)
        if not variants:
            continue
        scored_by_id = {str(rec.get("case_id")): rec for rec in load_jsonl(scored_path)}
        votes_by_case: dict[str, dict[str, bool]] = {}
        for judged_path in variants:
            entries = load_jsonl(judged_path)
            if not entries:
                continue
            judge_model = str(entries[0].get("judge_model", "unknown"))
            counts = per_judge.setdefault(judge_model, Counter())
            for entry in entries:
                structural_passed = entry.get("baseline_passed")
                judge_passed = entry.get("passed")
                if structural_passed is None:
                    continue
                counts["judged"] += 1
                if structural_passed == judge_passed:
                    counts["agree"] += 1
                elif judge_passed and not structural_passed:
                    counts[SCORER_FALSE_ALARM] += 1
                else:
                    counts[SCORER_MISS] += 1
                votes_by_case.setdefault(str(entry.get("case_id")), {})[judge_model] = bool(judge_passed)

        for case_id, votes in votes_by_case.items():
            scored_record = scored_by_id.get(case_id, {})
            structural_passed = scored_record.get("passed")
            if structural_passed is None or len(votes) < 2:
                continue
            pass_votes = sum(1 for verdict in votes.values() if verdict)
            fail_votes = len(votes) - pass_votes
            if pass_votes == fail_votes:
                majority["split"] += 1
                continue
            majority["decided"] += 1
            majority_passed = pass_votes > fail_votes
            if majority_passed == structural_passed:
                majority["agree"] += 1
            if not structural_passed and majority_passed and _is_evidence_only(scored_record):
                catch_votes.append(
                    {
                        "run_id": scored_path.name.replace(SCORED_SUFFIX, ""),
                        "case_id": case_id,
                        "judges_passing": pass_votes,
                        "judges_total": len(votes),
                        "unanimous_pass": pass_votes == len(votes),
                        "structural_failure_modes": list(scored_record.get("failure_modes", [])),
                    }
                )

    if not per_judge:
        return None

    return {
        "judges": {
            model: {
                "judged": counts["judged"],
                "agree": counts["agree"],
                "agreement": percent(counts["agree"], counts["judged"]),
                SCORER_FALSE_ALARM: counts[SCORER_FALSE_ALARM],
                SCORER_MISS: counts[SCORER_MISS],
            }
            for model, counts in sorted(per_judge.items())
        },
        "majority_decided": majority["decided"],
        "majority_agree": majority["agree"],
        "majority_agreement": percent(majority["agree"], majority["decided"]),
        "majority_split": majority["split"],
        "evidence_only_catches_passed_by_majority": len(catch_votes),
        "evidence_only_catches_passed_unanimously": sum(1 for c in catch_votes if c["unanimous_pass"]),
        "evidence_only_catch_votes": catch_votes,
    }


def render_panel_section(panel: dict[str, Any]) -> list[str]:
    lines = [
        "",
        "## Judge panel — do the catches survive more judges?",
        "",
        "Independent text-only judges over the same records (each judge reads output",
        "text only, never `tool_events`). Per-judge agreement with the structural",
        "baseline, then a per-record majority vote:",
        "",
        "| Judge model | Judged | Agreement | Structural FAIL / judge PASS | Structural PASS / judge FAIL |",
        "| --- | --- | --- | --- | --- |",
    ]
    for model, row in panel["judges"].items():
        lines.append(
            f"| `{model}` | {row['judged']} | {row['agreement']} "
            f"| {row[SCORER_FALSE_ALARM]} | {row[SCORER_MISS]} |"
        )
    lines.extend(
        [
            "",
            f"- Majority verdicts: {panel['majority_decided']} decided, {panel['majority_split']} split; "
            f"majority-vs-structural agreement {panel['majority_agreement']}",
            f"- **Evidence-only catches passed by the judge majority: "
            f"{panel['evidence_only_catches_passed_by_majority']}"
            f" (unanimously passed by every judge: {panel['evidence_only_catches_passed_unanimously']})** — "
            "records where multiple independent text-only readers see nothing wrong and the recorded",
            "  tool log shows a violation. Text review cannot catch these; action-level evidence does.",
            "- Caveat: some panel judges also appear as fleet *target* models (each affects only its own",
            "  40 records); majority voting across judges mitigates self-judging bias.",
        ]
    )
    return lines


def render_markdown(summary: dict[str, Any]) -> str:
    catches = summary["structural_catch_analysis"]
    judge_models = sorted({model for run in summary["runs"] for model in run["judge_models"]})
    lines = [
        "# Structural Scorer vs LLM Judge: Real-Agent Fleet Calibration",
        "",
        "The real-agent analogue of the 700-record model calibration study",
        "([`scorer_judge_calibration.md`](scorer_judge_calibration.md)). Here the baseline",
        "being calibrated is the **structural tool-event verifier**, not the keyword scorer:",
        "each record is a real agent (framework x local model) driven through a mock-tool",
        "sandbox that records every tool call, scored by checking the agent's claims against",
        "that recorded `tool_events` log.",
        "",
        "The judge is **text-only** — it reads the agent's output text and never sees",
        "`tool_events`. So the two disagreement directions do not mean the same thing they do",
        "in the keyword study:",
        "",
        "- **Structural FAIL, judge PASS** is often *not* a scorer false alarm. When the",
        "  structural failure mode is evidence-based (`unverified_tool_claim`,",
        "  `unsupported_tool_claim`, or a `missing_approval_gate` from an executed destructive",
        "  call), the structural scorer caught a fabricated tool use / unauthorized action the",
        "  text-only judge is structurally blind to. That is the added value of agent-level",
        "  evaluation, quantified below as *evidence-only catches*.",
        "- **Structural PASS, judge FAIL** localizes records where the judge is stricter on the",
        "  visible text (e.g. tone, disclosure) than the structural rule — review-worthy for",
        "  scorer coverage, exactly as in the keyword study.",
        "",
        f"- Fleet agents (runs): {summary['scored_runs']}",
        f"- Case set / tier: {summary.get('case_set', 'unknown')} / {summary.get('tier', 'unknown')}",
        f"- Judge model(s): {', '.join(judge_models)} "
        "(a local judge is itself imperfect; disagreement localizes review-worthy records, "
        "it does not adjudicate them)",
        f"- Judged records: {summary['judged_records']}",
        f"- Agreement: {summary['agreement_count']} ({summary['agreement_rate']})",
        f"- Structural FAIL, judge PASS: {summary[SCORER_FALSE_ALARM]} "
        f"(of which {catches['evidence_only_catches']} = {catches['evidence_only_catch_rate']} are "
        "evidence-only catches the text-only judge cannot see)",
        f"- Structural PASS, judge FAIL: {summary[SCORER_MISS]}",
        "",
        "## Per agent",
        "",
        "| Agent (framework_model) | Judged | Agreement | Structural FAIL / judge PASS | Structural PASS / judge FAIL |",
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
            "## Evidence-only catches — what a text-only judge cannot see",
            "",
            f"**{catches['evidence_only_catches']} of {catches['scorer_failed_judge_passed_total']} "
            f"({catches['evidence_only_catch_rate']}) structural-FAIL / judge-PASS records are "
            "evidence-only catches**: the structural layer failed them on the recorded `tool_events`",
            "log, which the text-only judge never sees — a fabricated tool use, a success claim with",
            "all tool calls failed, or an approval-gated case where a destructive tool call actually",
            f"executed ({catches['approval_gate_with_executed_destructive_call']} of the",
            "`missing_approval_gate` disagreements). These are the cases a model eval (text-only)",
            "would pass and an agent eval catches — the measured added value.",
            "",
            "The remaining structural-FAIL / judge-PASS records are text-visible keyword-rule",
            "over-fires (the same brittleness the 700-record study localizes), where the judge is the",
            "more lenient reader. Per structural failure mode (mode occurrences; a record can carry",
            "more than one):",
            "",
            "| Structural failure mode | Occurrences | Evidence-only |",
            "| --- | --- | --- |",
        ]
    )
    for mode, count in catches["scorer_failed_judge_passed_by_mode"].items():
        if mode in EVIDENCE_ONLY_MODES:
            mark = "yes (from tool_events)"
        elif mode == "missing_approval_gate":
            mark = f"{catches['approval_gate_with_executed_destructive_call']} of {count} (destructive call executed)"
        else:
            mark = "no (text-visible)"
        lines.append(f"| `{mode}` | {count} | {mark} |")

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
            structural_verdict = "PASS" if example["keyword_passed"] else "FAIL"
            judge_verdict = "PASS" if example["judge_passed"] else "FAIL"
            structural_modes = ", ".join(example.get("keyword_failure_modes", [])) or "none"
            lines.append(
                f"- `{example['run_id']}` / `{example['case_id']}` ({example['category']}): "
                f"structural {structural_verdict} vs judge {judge_verdict}. "
                f"Structural modes: {structural_modes}. Judge: {example['judge_rationale']}"
            )

    if summary.get("judge_panel"):
        lines.extend(render_panel_section(summary["judge_panel"]))

    lines.extend(
        [
            "",
            "## Reproduce this",
            "",
            "The 8 raw fleet output files are committed at",
            "`traces/external/sandbox_*.reviewed_sandbox_outputs.jsonl` and carry the recorded",
            "`tool_events`, so the structural half of this study — every structural verdict and",
            "every evidence-only catch — is deterministic and auditable offline from this",
            "checkout alone:",
            "",
            "```bash",
            "python3 src/sandbox_fleet_calibration.py --emit-only",
            "```",
            "",
            "The judge half needs a local ollama with the judge model pulled",
            "(`ollama pull gemma4`), is double-gated, and its agreement numbers vary",
            "run-to-run (an LLM judge is not deterministic):",
            "",
            "```bash",
            "AGENT_EVALS_ENABLE_LLM_JUDGE=1 python3 src/sandbox_fleet_calibration.py \\",
            "  --live-judge --provider ollama --model gemma4:latest",
            "```",
            "",
            "Scored and judged intermediates stay git-ignored (`*.local.jsonl`); only this",
            "aggregated report is committed.",
            "",
            "## Evidence class and boundary",
            "",
            "- Real agent outputs, produced by local open-weight models under four agent",
            "  frameworks, driven through a **mock-tool sandbox** — no production side effects.",
            "- Structural scoring compares claims against a **recorded tool-call log**; the judge",
            "  sees only text. Neither is ground truth. Disagreement localizes review, it does not",
            "  adjudicate.",
            "- Single judge model; local and imperfect. A stronger or multi-judge panel would",
            "  tighten the estimate. Scored and judged raw outputs are git-ignored",
            "  (`*.local.jsonl`); this report aggregates them deterministically.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Structural-scorer vs LLM-judge calibration over the real-agent sandbox fleet."
    )
    parser.add_argument("--live-judge", action="store_true", help="Actually call the judge (double-gated).")
    parser.add_argument("--emit-only", action="store_true", help="Write structural-scored fleet files, then stop.")
    parser.add_argument("--aggregate-only", action="store_true", help="Skip emit + judge; aggregate existing outputs.")
    parser.add_argument("--provider", default="ollama", choices=["anthropic", "openai", "ollama"], help="Judge provider.")
    parser.add_argument("--model", default="gemma4:latest", help="Judge model (default matches the 700-record study).")
    parser.add_argument("--endpoint", default=DEFAULT_OLLAMA_ENDPOINT, help="Ollama endpoint (ollama provider only).")
    parser.add_argument("--fleet-dir", type=Path, default=FLEET_DIR, help="Directory of fleet output JSONL files.")
    parser.add_argument("--case-path", type=Path, default=CASE_PATH, help="Benchmark case corpus (local_public_v2).")
    parser.add_argument("--tier", default=DEFAULT_TIER, help="Benchmark tier used to select cases.")
    parser.add_argument("--max-failures", type=int, default=10_000, help="Judge failure tolerance (report, not a gate).")
    parser.add_argument("--max-cases", type=int, default=None, help="Judge at most N records per agent (smoke use).")
    parser.add_argument("--json-out", type=Path, default=JSON_OUTPUT_PATH, help="Aggregate report JSON output path.")
    parser.add_argument("--md-out", type=Path, default=MARKDOWN_OUTPUT_PATH, help="Aggregate report Markdown output path.")
    parser.add_argument(
        "--panel",
        action="store_true",
        help="Also aggregate tagged multi-judge outputs (<stem>.judge.<model>.local.jsonl) into a panel section.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    try:
        if not args.aggregate_only:
            scored_paths = emit_scored_fleet(args.fleet_dir, args.case_path, args.tier)
            if args.emit_only:
                print(f"emitted {len(scored_paths)} structural-scored fleet files")
                return 0
            require_live_judge_enabled(live_flag_present=args.live_judge, env=dict(os.environ))
            judge_fleet(
                scored_paths,
                provider=args.provider,
                model=args.model,
                endpoint=args.endpoint,
                env=dict(os.environ),
                max_failures=args.max_failures,
                max_cases=args.max_cases,
            )

        summary = aggregate_calibration(SCORED_DIR, SCORED_GLOB)
        summary["report"] = "sandbox_fleet_scorer_judge_calibration"
        summary["baseline"] = "structural_tool_verifier"
        summary["case_set"] = "local_public_v2"
        summary["tier"] = args.tier
        summary["structural_catch_analysis"] = analyze_structural_catches(SCORED_DIR, SCORED_GLOB)
        if args.panel:
            summary["judge_panel"] = analyze_judge_panel(SCORED_DIR, SCORED_GLOB)

        write_json_object(summary, args.json_out)
        write_text(render_markdown(summary), args.md_out)
        print(
            f"fleet calibration report written: {args.md_out} "
            f"(agreement {summary['agreement_rate']} over {summary['judged_records']} records; "
            f"{summary['structural_catch_analysis']['evidence_only_catches']} evidence-only catches)"
        )
    except (FleetCalibrationError, GateCheckError, LlmJudgeError) as exc:
        print(f"fleet calibration error: {exc}", file=sys.stderr)
        if isinstance(exc, LlmJudgeError):
            print(f"hint: live judging needs --live-judge and {LLM_JUDGE_REQUIRED_ENV}=1", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
