"""Generate the static public leaderboard page from the benchmark report.

Reads ``reports/comparisons/local_open_weight_benchmark_v1.json`` (reviewed,
evidence-backed rankings) and writes a self-contained HTML page to
``docs/leaderboard/index.html`` for GitHub Pages. Deterministic, offline,
standard-library only.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_PATH = REPO_ROOT / "reports/comparisons/local_open_weight_benchmark_v1.json"
FLEET_REPORT_PATH = REPO_ROOT / "reports/comparisons/sandbox_fleet_pilot.json"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "docs/leaderboard/index.html"
REPO_URL = "https://github.com/NavidBroumandfar/agent-behavior-evals-lab"

PAGE_STYLE = """
body { font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; margin: 2rem auto;
       max-width: 60rem; padding: 0 1rem; color: #1a1a2e; }
h1 { margin-bottom: 0.25rem; }
.subtitle { color: #555; margin-top: 0; }
table { border-collapse: collapse; width: 100%; margin: 1.5rem 0; }
th, td { border: 1px solid #d8d8e0; padding: 0.5rem 0.75rem; text-align: left; }
th { background: #f4f4fa; }
tr:nth-child(even) { background: #fafafd; }
.rate { font-variant-numeric: tabular-nums; }
.note { background: #fff8e6; border: 1px solid #eed9a0; border-radius: 6px;
        padding: 0.75rem 1rem; margin: 1rem 0; }
footer { color: #777; font-size: 0.85rem; margin-top: 2rem; }
code { background: #f0f0f5; padding: 0.1rem 0.3rem; border-radius: 4px; }
"""


class LeaderboardPageError(Exception):
    """Leaderboard generation input error."""


def load_report(report_path: Path) -> dict[str, Any]:
    if not report_path.exists():
        raise LeaderboardPageError(f"benchmark report not found: {report_path}")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(report.get("rankings"), list) or not report["rankings"]:
        raise LeaderboardPageError("benchmark report has no rankings to publish")
    return report


def load_fleet_report(fleet_path: Path = FLEET_REPORT_PATH) -> dict[str, Any] | None:
    if not fleet_path.exists():
        return None
    report = json.loads(fleet_path.read_text(encoding="utf-8"))
    return report if report.get("agents") else None


def render_fleet_section(fleet_report: dict[str, Any] | None) -> str:
    if fleet_report is None:
        return ""
    rows = []
    for agent in fleet_report["agents"]:
        tool_area = agent.get("by_risk_area", {}).get("tool_use_claim", {})
        approval_area = agent.get("by_risk_area", {}).get("approval_gate", {})
        rows.append(
            "<tr>"
            f"<td><code>{html.escape(str(agent['agent']))}</code></td>"
            f"<td>{int(agent['scored'])}</td>"
            f"<td class='rate'>{html.escape(str(agent['pass_rate']))}</td>"
            f"<td class='rate'>{html.escape(str(tool_area.get('pass_rate', '-')))}</td>"
            f"<td class='rate'>{html.escape(str(approval_area.get('pass_rate', '-')))}</td>"
            "</tr>"
        )
    return f"""
<h2>Agent configurations under temptation (sandbox pilot — preliminary)</h2>
<p>Local models driving <em>mock tools</em> through the harder
<code>local_public_v2</code> pressure corpus. Scoring is action-based where
evidence exists: a destructive tool call without approval, or a claim with no
matching recorded tool event, fails structurally. <strong>Preliminary:</strong>
raw records are local-only pending review and are not promoted benchmark
evidence.</p>
<table>
<thead><tr><th>Agent</th><th>Cases</th><th>Pass rate</th>
<th>tool_use_claim</th><th>approval_gate</th></tr></thead>
<tbody>
{"".join(rows)}
</tbody>
</table>
"""


def render_page(report: dict[str, Any], fleet_report: dict[str, Any] | None = None) -> str:
    case_set = report.get("case_set", {})
    rows = []
    for entry in report["rankings"]:
        rate = float(entry.get("severity_weighted_effective_pass_rate", 0.0))
        ci = entry.get("bootstrap_ci_95", {})
        ci_text = f"{float(ci.get('low', 0)):.1%} – {float(ci.get('high', 0)):.1%}" if ci else "–"
        review = entry.get("review_counts", {})
        rows.append(
            "<tr>"
            f"<td>{int(entry.get('rank', 0))}</td>"
            f"<td><code>{html.escape(str(entry.get('model', 'unknown')))}</code></td>"
            f"<td class='rate'>{rate:.1%}</td>"
            f"<td class='rate'>{ci_text}</td>"
            f"<td>{int(entry.get('sample_size', 0))}</td>"
            f"<td>{int(review.get('records_reviewed', 0))}</td>"
            f"<td>{html.escape(str(entry.get('benchmark_split', '')))}</td>"
            "</tr>"
        )

    generated_at = html.escape(str(report.get("generated_at", "")))
    case_set_id = html.escape(str(case_set.get("case_set_id", "local_public_v1")))
    limitations = report.get("limitations", [])
    limitation_items = "".join(
        f"<li>{html.escape(str(item))}</li>" for item in limitations[:6]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agent Behavior Safety Leaderboard — local open-weight models</title>
<style>{PAGE_STYLE}</style>
</head>
<body>
<h1>Agent Behavior Safety Leaderboard</h1>
<p class="subtitle">Local open-weight models scored on the <a href="{REPO_URL}">{case_set_id}</a>
benchmark: approval gates, refusals, fake tool-use claims, privacy, uncertainty,
production-change pressure. Deterministic scoring, human-reviewed records,
fully reproducible offline.</p>

<div class="note"><strong>Read this before quoting numbers:</strong> pass rates are
severity-weighted, computed by a transparent rule-based scorer over saved
outputs, and every underlying record is committed in the repository. This
measures behavioral safety patterns on a {html.escape(str(case_set.get("case_set_version", "1.0.0")))}
public corpus — not general capability, and not production safety certification.</div>

<table>
<thead>
<tr><th>#</th><th>Model</th><th>Severity-weighted pass rate</th><th>95% CI</th>
<th>Cases</th><th>Reviewed records</th><th>Split</th></tr>
</thead>
<tbody>
{"".join(rows)}
</tbody>
</table>

{render_fleet_section(fleet_report)}
<h2>Method, in one paragraph</h2>
<p>Each model runs locally (Ollama, temperature 0) against the public benchmark
prompts; outputs are saved, validated against schemas, scored by the
deterministic scorer, human-reviewed, and promoted into committed evidence
ledgers. The same gate is available as a
<a href="{REPO_URL}#use-as-a-github-action-ci-safety-gate">GitHub Action</a>
to score <em>your</em> agent's saved outputs in CI.</p>

<h2>Limitations</h2>
<ul>{limitation_items}</ul>

<footer>Generated from <code>reports/comparisons/local_open_weight_benchmark_v1.json</code>
(report {generated_at}). Regenerate with <code>python src/leaderboard_page.py</code>.
Source, corpus, scorer, and every scored record:
<a href="{REPO_URL}">{REPO_URL.replace("https://", "")}</a>.</footer>
</body>
</html>
"""


def generate(
    report_path: Path = DEFAULT_REPORT_PATH,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    fleet_path: Path = FLEET_REPORT_PATH,
) -> Path:
    report = load_report(report_path)
    fleet_report = load_fleet_report(fleet_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_page(report, fleet_report), encoding="utf-8")
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the static leaderboard page.")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    try:
        output_path = generate(args.report_path, args.output_path)
    except (LeaderboardPageError, json.JSONDecodeError) as exc:
        print(f"leaderboard page error: {exc}", file=sys.stderr)
        return 2
    print(f"leaderboard page written: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
