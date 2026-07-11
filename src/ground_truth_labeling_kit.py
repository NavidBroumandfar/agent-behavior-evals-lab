"""Ground-truth labeling kit for structural-vs-judge disagreements.

The calibration studies report how often the structural ``tool_events`` check
and the text-only LLM judge disagree. That number is only credible if a human
says which side is right on the contested records. This kit packages exactly
those records for human labeling and then measures agreement of each automated
signal against the human ground truth.

Deliberately honest: the committed sample includes a counter-example where the
human sides with the JUDGE against the structural check (a destructive call the
user explicitly authorized in-turn, which the blunt "any destructive = fail"
rule over-fires on). A kit that only ever vindicates the structural check would
not be evidence.

Workflow:
1. ``worksheet`` — emit the contested records with blank ``human_label`` /
   ``human_rationale`` slots for a reviewer to fill.
2. reviewer fills each row (``pass`` / ``fail`` + a rationale).
3. ``validate`` — check every row is completed and well-formed.
4. ``summarize`` — report structural-vs-human and judge-vs-human agreement.

Deterministic, offline, standard-library only. No models, no trace mutation,
no external actions. The decision vocabulary matches the existing adjudication
workflow (a completed label is the human's pass/fail verdict on the record).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PATH = REPO_ROOT / "evals/labeling/disagreement_sample.jsonl"
LABELED_EXAMPLE_PATH = REPO_ROOT / "evals/labeling/disagreement_sample.labeled.example.jsonl"
VALID_LABELS = {"pass", "fail"}


class LabelingKitError(Exception):
    """Ground-truth labeling kit validation error."""


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _verdict_label(verdict: dict[str, Any]) -> str:
    return "pass" if verdict.get("passed") else "fail"


def validate_sample(records: list[dict[str, Any]]) -> None:
    """Every sample record must be a genuine structural-vs-judge disagreement."""

    seen: set[str] = set()
    for index, record in enumerate(records):
        context = f"disagreement_sample[{index}]"
        sample_id = str(record.get("sample_id", ""))
        if not sample_id:
            raise LabelingKitError(f"{context}.sample_id is required")
        if sample_id in seen:
            raise LabelingKitError(f"{context}.sample_id duplicate: {sample_id}")
        seen.add(sample_id)
        for field in ("prompt", "output_text", "structural_verdict", "judge_verdict"):
            if field not in record:
                raise LabelingKitError(f"{context}.{field} is required")
        if _verdict_label(record["structural_verdict"]) == _verdict_label(record["judge_verdict"]):
            raise LabelingKitError(
                f"{context} ({sample_id}) is not a disagreement: structural and judge agree; "
                "the sample must contain only contested records"
            )


def build_worksheet(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add blank human-label slots; carry the evidence a reviewer needs."""

    worksheet = []
    for record in records:
        row = dict(record)
        row["human_label"] = None
        row["labeled_by"] = ""
        row["human_rationale"] = ""
        worksheet.append(row)
    return worksheet


def validate_labels(records: list[dict[str, Any]]) -> None:
    for index, record in enumerate(records):
        context = f"labeled[{index}] ({record.get('sample_id', '?')})"
        label = record.get("human_label")
        if label not in VALID_LABELS:
            raise LabelingKitError(f"{context}.human_label must be one of {sorted(VALID_LABELS)}, got {label!r}")
        if not str(record.get("human_rationale", "")).strip():
            raise LabelingKitError(f"{context}.human_rationale must be non-empty")
        if not str(record.get("labeled_by", "")).strip():
            raise LabelingKitError(f"{context}.labeled_by must be non-empty")


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Agreement of each automated signal with the human ground truth."""

    validate_labels(records)
    total = len(records)
    structural_agree = 0
    judge_agree = 0
    per_record = []
    for record in records:
        human = str(record["human_label"])
        structural = _verdict_label(record["structural_verdict"])
        judge = _verdict_label(record["judge_verdict"])
        s_ok = structural == human
        j_ok = judge == human
        structural_agree += s_ok
        judge_agree += j_ok
        per_record.append(
            {
                "sample_id": record["sample_id"],
                "human_label": human,
                "structural": structural,
                "judge": judge,
                "structural_agrees_with_human": s_ok,
                "judge_agrees_with_human": j_ok,
            }
        )
    return {
        "records": total,
        "structural_vs_human_agreement": round(structural_agree / total, 4) if total else 0.0,
        "judge_vs_human_agreement": round(judge_agree / total, 4) if total else 0.0,
        "structural_agree_count": structural_agree,
        "judge_agree_count": judge_agree,
        "human_sided_with_judge_over_structural": [
            r["sample_id"] for r in per_record if r["judge_agrees_with_human"] and not r["structural_agrees_with_human"]
        ],
        "per_record": per_record,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Ground-truth labeling: structural vs. judge on contested records",
        "",
        "_Human-labeled sample of records where the structural check and the text judge disagree._",
        "",
        f"- Records: {summary['records']}",
        f"- Structural agrees with human: {summary['structural_agree_count']}/{summary['records']} "
        f"({summary['structural_vs_human_agreement']:.1%})",
        f"- Judge agrees with human: {summary['judge_agree_count']}/{summary['records']} "
        f"({summary['judge_vs_human_agreement']:.1%})",
        f"- Human sided with the judge over structural on: "
        f"{', '.join(summary['human_sided_with_judge_over_structural']) or 'none'}",
        "",
        "| record | human | structural | judge | structural ✓ | judge ✓ |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in summary["per_record"]:
        lines.append(
            f"| {row['sample_id']} | {row['human_label']} | {row['structural']} | {row['judge']} | "
            f"{'yes' if row['structural_agrees_with_human'] else 'no'} | "
            f"{'yes' if row['judge_agrees_with_human'] else 'no'} |"
        )
    return "\n".join(lines) + "\n"


def _self_check() -> None:
    sample = load_jsonl(SAMPLE_PATH)
    validate_sample(sample)
    assert len(sample) >= 5, "expected the committed contested sample"

    # A blank worksheet must not validate as labeled.
    worksheet = build_worksheet(sample)
    try:
        validate_labels(worksheet)
    except LabelingKitError:
        pass
    else:
        raise AssertionError("a blank worksheet must fail label validation")

    labeled = load_jsonl(LABELED_EXAMPLE_PATH)
    validate_labels(labeled)
    summary = summarize(labeled)
    # The kit must be capable of siding with the judge — an all-structural
    # sample would not be credible evidence.
    assert summary["human_sided_with_judge_over_structural"], summary
    assert 0.0 <= summary["structural_vs_human_agreement"] <= 1.0
    assert summary["structural_agree_count"] + len(summary["human_sided_with_judge_over_structural"]) <= summary["records"]
    print(
        "ground_truth_labeling_kit self-check passed "
        f"(structural {summary['structural_vs_human_agreement']:.0%}, judge {summary['judge_vs_human_agreement']:.0%} vs human)"
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ground-truth labeling kit for structural-vs-judge disagreements.")
    sub = parser.add_subparsers(dest="command")
    ws = sub.add_parser("worksheet", help="Emit a blank labeling worksheet from the contested sample.")
    ws.add_argument("--sample", type=Path, default=SAMPLE_PATH)
    ws.add_argument("--out", type=Path, required=True)
    va = sub.add_parser("validate", help="Validate a completed labeling file.")
    va.add_argument("labeled", type=Path)
    su = sub.add_parser("summarize", help="Summarize agreement from a completed labeling file.")
    su.add_argument("labeled", type=Path, nargs="?", default=LABELED_EXAMPLE_PATH)
    su.add_argument("--md-out", type=Path)
    su.add_argument("--json-out", type=Path)
    parser.add_argument("--self-check", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.self_check or args.command is None:
        _self_check()
        return 0
    try:
        if args.command == "worksheet":
            sample = load_jsonl(args.sample)
            validate_sample(sample)
            worksheet = build_worksheet(sample)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("w", encoding="utf-8") as handle:
                for row in worksheet:
                    handle.write(json.dumps(row, sort_keys=True) + "\n")
            print(f"wrote {len(worksheet)} blank rows to {args.out}")
        elif args.command == "validate":
            validate_labels(load_jsonl(args.labeled))
            print(f"labels valid: {args.labeled}")
        elif args.command == "summarize":
            summary = summarize(load_jsonl(args.labeled))
            if args.md_out:
                args.md_out.parent.mkdir(parents=True, exist_ok=True)
                args.md_out.write_text(render_markdown(summary), encoding="utf-8")
            if args.json_out:
                args.json_out.parent.mkdir(parents=True, exist_ok=True)
                args.json_out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(render_markdown(summary))
    except LabelingKitError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
