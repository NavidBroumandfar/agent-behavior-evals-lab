"""Generate the M60 local/open-weight benchmark report V1.

This report is evidence-gated. If committed ledger-backed local model evidence
does not satisfy M59, the report is still generated but publishes no rankings.
The module does not execute local models, providers, agents, networks, tools,
credentials, private logs, gated LLM review, or external actions.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

from local_ranking_methodology import DEFAULT_METHODOLOGY_PATH
from reporting_utils import load_json_object, write_json_object, write_text


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATED_AT = "2026-06-21T00:00:00Z"
SNAPSHOT_ID = "local_open_weight_benchmark_report_v1"
SNAPSHOT_VERSION = "1.0.0"

LOCAL_BENCHMARK_CASE_PATH = REPO_ROOT / "evals/benchmarks/local_public_v1/cases.jsonl"
LOCAL_BENCHMARK_MANIFEST_PATH = REPO_ROOT / "evals/benchmarks/local_public_v1/manifest.json"
DEFAULT_LEDGER_PATHS = [
    REPO_ROOT / "traces/external/local_run_ledger.example.json",
]
DEFAULT_SNAPSHOT_PATH = REPO_ROOT / "reports/comparisons/local_open_weight_benchmark_v1.json"
DEFAULT_REPORT_PATH = REPO_ROOT / "reports/comparisons/local_open_weight_benchmark_v1.md"


class LocalBenchmarkReportGenerationError(Exception):
    """Local benchmark report generation error."""


def generate_benchmark_report(
    *,
    snapshot_path: Path = DEFAULT_SNAPSHOT_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
    methodology_path: Path = DEFAULT_METHODOLOGY_PATH,
    ledger_paths: list[Path] | None = None,
) -> dict[str, Any]:
    """Generate the M60 JSON snapshot and Markdown report."""

    methodology = load_json_object(methodology_path)
    manifest = load_json_object(LOCAL_BENCHMARK_MANIFEST_PATH)
    ledgers = load_ledgers(ledger_paths or list(DEFAULT_LEDGER_PATHS))
    snapshot = build_snapshot(methodology, manifest, methodology_path, ledgers)
    write_json_object(snapshot, snapshot_path)
    write_text(generate_markdown(snapshot), report_path)
    return {
        "snapshot_path": display_path(snapshot_path),
        "report_path": display_path(report_path),
        "report_status": snapshot["report_status"],
        "ranking_claim_allowed": snapshot["ranking_claim_allowed"],
        "rankings": len(snapshot["rankings"]),
        "excluded_evidence": len(snapshot["excluded_evidence"]),
    }


def load_ledgers(ledger_paths: list[Path]) -> list[dict[str, Any]]:
    """Load committed local run ledgers for report evidence scanning."""

    ledgers = []
    for path in ledger_paths:
        ledger = load_json_object(path)
        ledger["_source_path"] = display_path(path)
        ledger["_source_sha256"] = sha256_file(path)
        ledgers.append(ledger)
    return ledgers


def build_snapshot(
    methodology: dict[str, Any],
    manifest: dict[str, Any],
    methodology_path: Path,
    ledgers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the benchmark report snapshot."""

    evidence_sources = []
    rankings: list[dict[str, Any]] = []
    excluded_evidence: list[dict[str, Any]] = []

    for ledger in ledgers:
        source_id = str(ledger["ledger_id"])
        source_exclusions = []
        for entry in ledger["entries"]:
            exclusion_reasons = ledger_entry_exclusion_reasons(entry, methodology)
            if exclusion_reasons:
                source_exclusions.append(excluded_entry(source_id, entry, exclusion_reasons))
            else:
                rankings.append(ranking_from_entry(entry, methodology))
        excluded_evidence.extend(source_exclusions)
        evidence_sources.append(
            {
                "source_id": source_id,
                "source_kind": str(ledger["ledger_kind"]),
                "path": str(ledger["_source_path"]),
                "sha256": str(ledger["_source_sha256"]),
                "entry_count": len(ledger["entries"]),
                "eligible_entry_count": len(ledger["entries"]) - len(source_exclusions),
                "excluded_entry_count": len(source_exclusions),
            }
        )

    rankings.sort(key=lambda item: (-float(item["severity_weighted_effective_pass_rate"]), str(item["model"])))
    for index, ranking in enumerate(rankings, start=1):
        ranking["rank"] = index

    eligible_real_local_targets = len(rankings)
    acceptance_criteria_met = eligible_real_local_targets >= 2
    ranking_claim_allowed = acceptance_criteria_met and bool(rankings)
    report_status = "published_local_ranking" if ranking_claim_allowed else "no_rankings_published"
    blocked_reason = "" if ranking_claim_allowed else (
        "No committed reviewed live-local, ledger-backed standard-or-extended split evidence meets M59 ranking requirements."
    )

    return {
        "snapshot_id": SNAPSHOT_ID,
        "version": SNAPSHOT_VERSION,
        "generated_at": GENERATED_AT,
        "title": "Local/Open-Weight Benchmark Report V1",
        "report_status": report_status,
        "ranking_claim_allowed": ranking_claim_allowed,
        "methodology": {
            "methodology_id": methodology["methodology_id"],
            "methodology_version": methodology["version"],
            "methodology_path": display_path(methodology_path),
            "methodology_sha256": sha256_file(methodology_path),
            "primary_metric_id": "severity_weighted_effective_pass_rate",
        },
        "case_set": {
            "case_set_id": manifest["case_set_id"],
            "case_set_version": manifest["version"],
            "minimum_publishable_split": methodology["benchmark_scope"]["minimum_publishable_split"],
            "publishable_splits": list(methodology["benchmark_scope"]["publishable_splits"]),
            "case_path": display_path(LOCAL_BENCHMARK_CASE_PATH),
            "case_file_sha256": sha256_file(LOCAL_BENCHMARK_CASE_PATH),
            "manifest_path": display_path(LOCAL_BENCHMARK_MANIFEST_PATH),
            "manifest_sha256": sha256_file(LOCAL_BENCHMARK_MANIFEST_PATH),
        },
        "eligibility_summary": {
            "minimum_real_local_targets_required": 2,
            "eligible_real_local_targets": eligible_real_local_targets,
            "eligible_manual_public_targets": 0,
            "eligible_ranked_targets": len(rankings),
            "excluded_targets": len(excluded_evidence),
            "acceptance_criteria_met": acceptance_criteria_met,
            "ranking_publication_blocked_reason": blocked_reason,
        },
        "evidence_sources": evidence_sources,
        "rankings": rankings,
        "excluded_evidence": excluded_evidence,
        "limitations": [
            "No real local/open-weight model ranking is published unless at least two eligible real local targets are present.",
            "Dry-run, synthetic, smoke-split, private-only, and manual-public-sample evidence cannot support this public local ranking.",
            "The report does not claim cloud-model ranking, production-policy proof, private runtime behavior, or provider benchmark results.",
            "Live local execution remains opt-in only and outside the deterministic quality gate.",
        ],
        "reproduction_instructions": [
            "Run `python3 scripts/dev.py check` to regenerate and validate the public-safe report artifacts.",
            "For future real evidence, run the M57 harness manually with `--live-local` and `AGENT_EVALS_ENABLE_LIVE_LOCAL`, then review and normalize saved outputs.",
            "Validate reviewed live-local outputs with `--allow-live-local` and import them against `evals/benchmarks/local_public_v1/cases.jsonl`.",
            "Create an M58-compatible run ledger for the reviewed outputs, then rerun this report generator.",
        ],
        "source_paths": [
            "benchmarks/evidence_class_charter.json",
            "benchmarks/local_ranking_methodology.json",
            "evals/benchmarks/local_public_v1/manifest.json",
            "traces/external/local_run_ledger.example.json",
            "docs/live_benchmark_roadmap.md",
            "docs/wiki/concepts/local_ranking_methodology.md",
        ],
        "safety_assertions": safe_assertions(),
    }


def ledger_entry_exclusion_reasons(entry: dict[str, Any], methodology: dict[str, Any]) -> list[str]:
    """Return M59 exclusion reasons for one ledger entry."""

    reasons = []
    required_evidence_class = methodology["evidence_requirements"]["ranking_evidence_class"]
    publishable_splits = set(methodology["benchmark_scope"]["publishable_splits"])
    minimum_sample_size = int(methodology["uncertainty_policy"]["minimum_sample_size_for_publication"])
    if entry["evidence_class"] != required_evidence_class:
        reasons.append("Evidence class is not local_public_benchmark.")
    if entry["run_mode"] != "reviewed_live_local_run":
        reasons.append("Run mode is not reviewed_live_local_run.")
    if entry["run_status"] != methodology["eligibility_requirements"]["required_run_status"]:
        reasons.append("Run status is not succeeded.")
    if entry["ranking_eligible"] is not True:
        reason = str(entry.get("ranking_exclusion_reason", "")).strip()
        reasons.append(f"Ledger marks entry ranking-ineligible: {reason}" if reason else "Ledger marks entry ranking-ineligible.")
    if entry["case_set"]["benchmark_split"] not in publishable_splits:
        reasons.append("Benchmark split is not publishable for local rankings.")
    if int(entry["case_set"]["case_count"]) < minimum_sample_size:
        reasons.append("Sample size is below the publication minimum.")
    if "cloud" in str(entry["model"]).lower():
        reasons.append("Cloud-labelled model is excluded from local-only rankings.")
    if entry["review_summary"]["reviewed_record_count"] != entry["outputs"]["scored_trace_record_count"]:
        reasons.append("Review summary record count does not match scored traces.")
    if int(entry["review_summary"]["needs_discussion_count"]) != 0:
        reasons.append("Unresolved review records remain.")
    if int(entry["review_summary"]["unsafe_output_count"]) != 0:
        reasons.append("Review summary contains unsafe-output flags.")
    if int(entry["review_summary"]["malformed_output_count"]) != 0:
        reasons.append("Review summary contains malformed-output flags.")
    safety = entry["safety_assertions"]
    if safety["public_safe"] is not True:
        reasons.append("Entry is not public-safe.")
    if safety["contains_private_data"] is not False:
        reasons.append("Entry contains private data.")
    if safety["credentials_required"] is not False:
        reasons.append("Entry requires credentials.")
    if safety["external_actions"] is not False:
        reasons.append("Entry includes external actions.")
    if safety["raw_outputs_included"] is not False:
        reasons.append("Entry includes raw outputs.")
    return reasons


def excluded_entry(source_id: str, entry: dict[str, Any], exclusion_reasons: list[str]) -> dict[str, Any]:
    """Build an excluded evidence row."""

    return {
        "source_id": source_id,
        "run_id": str(entry["run_id"]),
        "model": str(entry["model"]),
        "runtime": str(entry["runtime"]),
        "evidence_class": str(entry["evidence_class"]),
        "run_mode": str(entry["run_mode"]),
        "benchmark_split": str(entry["case_set"]["benchmark_split"]),
        "case_count": int(entry["case_set"]["case_count"]),
        "ranking_eligible": entry["ranking_eligible"] is True,
        "exclusion_reasons": exclusion_reasons,
    }


def ranking_from_entry(entry: dict[str, Any], methodology: dict[str, Any]) -> dict[str, Any]:
    """Build a ranking row from reviewed, scored, ledger-backed local evidence."""

    scored_traces = load_jsonl(repo_path(entry["outputs"]["scored_trace_path"]))
    review_summary = load_json_object(repo_path(entry["review_summary"]["summary_path"]))
    review_by_record_id = {
        str(record["record_id"]): record
        for record in review_summary["reviewed_records"]
    }
    case_results = []
    severity_weights = methodology["severity_weights"]
    for trace in scored_traces:
        record_id = str(trace["source_record_id"])
        review_record = review_by_record_id[record_id]
        severity = str(trace["severity"])
        if review_record["case_id"] != trace["case_id"]:
            raise LocalBenchmarkReportGenerationError(
                f"review summary case_id does not match scored trace for {record_id}"
            )
        if review_record["severity"] != severity:
            raise LocalBenchmarkReportGenerationError(
                f"review summary severity does not match scored trace for {record_id}"
            )
        severity_weight = float(severity_weights[severity])
        case_results.append(
            {
                "record_id": record_id,
                "case_id": str(trace["case_id"]),
                "severity": severity,
                "severity_weight": severity_weight,
                "heuristic_score": 1.0 if trace["passed"] is True else 0.0,
                "effective_score": 1.0 if review_record["effective_passed"] is True else 0.0,
                "reviewer_decision": str(review_record["reviewer_decision"]),
            }
        )

    total_weight = sum(float(item["severity_weight"]) for item in case_results)
    effective_weighted = safe_divide(
        sum(float(item["effective_score"]) * float(item["severity_weight"]) for item in case_results),
        total_weight,
    )
    heuristic_weighted = safe_divide(
        sum(float(item["heuristic_score"]) * float(item["severity_weight"]) for item in case_results),
        total_weight,
    )
    review_counts = dict(review_summary["review_counts"])
    review_counts["reviewer_count"] = review_summary["inter_rater"]["reviewer_count"]
    review_counts["agreement_rate"] = review_summary["inter_rater"]["agreement_rate"]

    return {
        "rank": 0,
        "model": str(entry["model"]),
        "runtime": str(entry["runtime"]),
        "ledger_entry_id": str(entry["entry_id"]),
        "sample_size": len(case_results),
        "benchmark_split": str(entry["case_set"]["benchmark_split"]),
        "severity_weighted_effective_pass_rate": round(effective_weighted, 4),
        "severity_weighted_heuristic_pass_rate": round(heuristic_weighted, 4),
        "bootstrap_ci_95": deterministic_bootstrap_ci(
            case_results,
            int(methodology["uncertainty_policy"]["resample_count"]),
            str(methodology["uncertainty_policy"]["random_seed"]),
            str(entry["run_id"]),
        ),
        "unresolved_review_count": int(review_summary["review_counts"]["needs_discussion_count"]),
        "abstention_count": 0,
        "review_counts": review_counts,
    }


def deterministic_bootstrap_ci(
    case_results: list[dict[str, Any]],
    resample_count: int,
    seed: str,
    run_id: str,
) -> dict[str, float]:
    """Return a deterministic bootstrap CI over effective weighted pass rate."""

    if not case_results:
        return {"low": 0.0, "high": 0.0}
    rng = random.Random(f"{seed}:{run_id}")
    samples = []
    for _ in range(resample_count):
        resampled = [case_results[rng.randrange(len(case_results))] for _ in case_results]
        total_weight = sum(float(item["severity_weight"]) for item in resampled)
        weighted_score = safe_divide(
            sum(float(item["effective_score"]) * float(item["severity_weight"]) for item in resampled),
            total_weight,
        )
        samples.append(weighted_score)
    samples.sort()
    return {
        "low": round(percentile(samples, 0.025), 4),
        "high": round(percentile(samples, 0.975), 4),
    }


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    index = round((len(values) - 1) * fraction)
    return values[max(0, min(index, len(values) - 1))]


def safe_divide(numerator: float, denominator: float) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records = []
    with path.open("r", encoding="utf-8") as input_file:
        for line in input_file:
            stripped = line.strip()
            if stripped:
                records.append(json.loads(stripped))
    return records


def repo_path(value: Any) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else REPO_ROOT / path


def generate_markdown(snapshot: dict[str, Any]) -> str:
    """Generate the reader-facing Markdown benchmark report."""

    eligibility = snapshot["eligibility_summary"]
    lines = [
        "# Local/Open-Weight Benchmark Report V1",
        "",
        "This report is public-safe and evidence-gated. It publishes no model rankings unless committed evidence satisfies the M59 methodology.",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Generated at | `{snapshot['generated_at']}` |",
        f"| Report status | `{snapshot['report_status']}` |",
        f"| Ranking claim allowed | `{str(snapshot['ranking_claim_allowed']).lower()}` |",
        f"| Case set | `{snapshot['case_set']['case_set_id']}` `{snapshot['case_set']['case_set_version']}` |",
        f"| Publishable splits | {', '.join(f'`{split}`' for split in snapshot['case_set']['publishable_splits'])} |",
        f"| Eligible real local targets | {eligibility['eligible_real_local_targets']} |",
        f"| Excluded targets | {eligibility['excluded_targets']} |",
        "",
        "## Ranking Table",
        "",
    ]
    if snapshot["rankings"]:
        lines.extend(
            [
                "| Rank | Model | Runtime | Weighted effective | 95% CI | Sample | Split |",
                "| ---: | --- | --- | ---: | --- | ---: | --- |",
            ]
        )
        for row in snapshot["rankings"]:
            ci = row["bootstrap_ci_95"]
            lines.append(
                f"| {row['rank']} | `{row['model']}` | `{row['runtime']}` | "
                f"{row['severity_weighted_effective_pass_rate']:.4f} | "
                f"{ci['low']:.4f}-{ci['high']:.4f} | {row['sample_size']} | `{row['benchmark_split']}` |"
            )
    else:
        lines.append("No ranking table is published because no committed real local model evidence satisfies M59.")

    lines.extend(
        [
            "",
            "## Excluded Evidence",
            "",
        ]
    )
    if snapshot["excluded_evidence"]:
        for item in snapshot["excluded_evidence"]:
            reasons = "; ".join(str(reason).rstrip(".") for reason in item["exclusion_reasons"])
            lines.append(f"- `{item['run_id']}` (`{item['model']}`): {reasons}.")
    else:
        lines.append("- No excluded evidence was found.")

    lines.extend(
        [
            "",
            "## Methodology",
            "",
            f"- Methodology: `{snapshot['methodology']['methodology_id']}` `{snapshot['methodology']['methodology_version']}`.",
            "- Primary metric: `severity_weighted_effective_pass_rate`.",
            "- Public rankings require M58 ledger-backed `local_public_benchmark` evidence over the standard or extended split.",
            "",
            "## Limitations",
            "",
            "\n".join(f"- {item}" for item in snapshot["limitations"]),
            "",
            "## Reproduction",
            "",
            "\n".join(f"- {item}" for item in snapshot["reproduction_instructions"]),
            "",
        ]
    )
    return "\n".join(lines)


def safe_assertions() -> dict[str, bool]:
    return {
        "public_safe": True,
        "live_execution": False,
        "external_actions": False,
        "contains_private_data": False,
        "credentials_required": False,
        "private_prompts_included": False,
        "raw_outputs_included": False,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def main() -> int:
    try:
        summary = generate_benchmark_report()
    except (LocalBenchmarkReportGenerationError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"local benchmark snapshot path: {summary['snapshot_path']}")
    print(f"local benchmark report path: {summary['report_path']}")
    print(f"report status: {summary['report_status']}")
    print(f"ranking claim allowed: {str(summary['ranking_claim_allowed']).lower()}")
    print(f"rankings: {summary['rankings']}")
    print(f"excluded evidence: {summary['excluded_evidence']}")
    print("local benchmark report generation succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
