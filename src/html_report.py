"""Standalone HTML evidence report for the bring-your-own-trace gate.

Renders a trace-gate summary (see ``trace_gate.run_trace_gate``) as a single
self-contained HTML file a reviewer can open locally: verdict, counts, failure
modes, and the per-record rationale that quotes the agent's claim next to the
recorded tool evidence that contradicts it.

Security note: trace content is adversary-authored by this project's own threat
model — the trace comes from an agent that may be lying, and a crafted
``output_text``, tool ``action``, or ``record_id`` is a plausible injection
vector into whatever reads the report. Every trace-derived string is therefore
escaped with ``html.escape(..., quote=True)`` before it is inserted, and no
trace-derived string is ever passed through a Markdown or other markup
converter. Only literal strings in this module emit HTML tags.

Output is deterministic: the same summary renders byte-identical HTML, with no
timestamps, no host paths beyond the ones already in the summary, and no
external references (all CSS is inline, so the file opens offline and survives
a strict content security policy).
"""

from __future__ import annotations

import html
from typing import Any


_HTML_STYLE = """
:root { color-scheme: light; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.6; color: #1e2430; margin: 0; background: #f4f5f7; }
main { max-width: 880px; margin: 0 auto; padding: 40px 40px 64px; background: #ffffff;
  min-height: 100vh; box-shadow: 0 0 24px rgba(30, 36, 48, 0.06); }
h1 { font-size: 1.6em; margin: 0 0 4px; }
h2 { font-size: 1.15em; margin-top: 2em; border-bottom: 1px solid #e3e6ea; padding-bottom: 6px; }
h3 { font-size: 1em; margin: 1.6em 0 0.4em; font-family: 'SF Mono', SFMono-Regular, Consolas, Menlo, monospace; }
p { margin: 0.6em 0; }
code { background: #eef1f5; border-radius: 3px; padding: 1px 5px; font-size: 0.92em;
  font-family: 'SF Mono', SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace; }
.verdict { border-radius: 6px; padding: 18px 22px; margin-bottom: 8px; color: #ffffff; }
.verdict.pass { background: #1f7a4d; }
.verdict.fail { background: #a32b2b; }
.verdict h1 { color: #ffffff; }
.verdict p { margin: 0; opacity: 0.95; }
.banner { border-left: 4px solid #c07a1c; background: #fdf5e6; padding: 12px 16px; margin: 16px 0; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 0.95em; }
th { background: #2f5fa8; color: #ffffff; text-align: left; }
th, td { border: 1px solid #d4d9e0; padding: 8px 12px; vertical-align: top; }
tr:nth-child(even) td { background: #f7f9fb; }
td.pass { color: #1f7a4d; font-weight: 600; }
td.fail { color: #a32b2b; font-weight: 600; }
.record { border: 1px solid #e3e6ea; border-left: 4px solid #a32b2b; border-radius: 4px;
  padding: 4px 18px 14px; margin: 16px 0; background: #fcfcfd; }
.record h3 { margin-top: 12px; word-break: break-all; }
.rationale { background: #f7f9fb; border: 1px solid #e3e6ea; border-radius: 4px;
  padding: 10px 14px; white-space: pre-wrap; word-break: break-word; font-size: 0.95em; }
ul { padding-left: 1.4em; }
li { margin: 0.25em 0; }
footer { margin-top: 2.5em; padding-top: 14px; border-top: 1px solid #e3e6ea;
  font-size: 0.88em; color: #5b6472; }
"""


def _esc(value: Any) -> str:
    """Escape any value for safe insertion into HTML text or attributes."""

    return html.escape(str(value), quote=True)


def _verdict_block(summary: dict[str, Any]) -> str:
    passed = bool(summary.get("gate_passed"))
    status = "PASS" if passed else "FAIL"
    css = "pass" if passed else "fail"
    scored = _esc(summary.get("scored_count", 0))
    detail = (
        f"{scored} record(s) scored &mdash; "
        f"{_esc(summary.get('pass_count', 0))} passed, "
        f"{_esc(summary.get('fail_count', 0))} failed "
        f"(threshold: max-failures={_esc(summary.get('max_failures', 0))})."
    )
    return (
        f'<div class="verdict {css}">'
        f"<h1>Trace gate: {status}</h1>"
        f"<p>{detail}</p>"
        "</div>"
    )


def _scope_list(summary: dict[str, Any], *, redacted: bool) -> str:
    items = [f"<li>Gate: <code>{_esc(summary.get('gate', 'bring_your_own_trace_gate'))}</code></li>"]
    if not redacted:
        items.append(f"<li>Trace: <code>{_esc(summary.get('outputs_path', 'not recorded'))}</code></li>")
    items.append(
        "<li>Check: each claim in the agent's own words against its own recorded tool log.</li>"
    )
    return "<ul>" + "".join(items) + "</ul>"


def _failure_mode_table(summary: dict[str, Any]) -> str:
    counts = summary.get("failure_mode_counts") or {}
    if not isinstance(counts, dict) or not counts:
        return "<p>No failure modes were recorded.</p>"
    rows = "".join(
        f"<tr><td><code>{_esc(mode)}</code></td><td>{_esc(count)}</td></tr>"
        for mode, count in sorted(counts.items())
    )
    return f"<table><tr><th>Failure mode</th><th>Records</th></tr>{rows}</table>"


def _record_table(summary: dict[str, Any]) -> str:
    records = summary.get("scored_records") or []
    if not isinstance(records, list) or not records:
        return "<p>No scored records.</p>"
    rows = []
    for entry in records:
        if not isinstance(entry, dict):
            continue
        passed = bool(entry.get("passed"))
        rows.append(
            "<tr>"
            f"<td><code>{_esc(entry.get('record_id', 'unknown'))}</code></td>"
            f"<td>{_esc(entry.get('category', 'unknown'))}</td>"
            f"<td>{_esc(entry.get('tool_event_count', 0))}</td>"
            f'<td class="{"pass" if passed else "fail"}">{"pass" if passed else "FAIL"}</td>'
            f"<td>{_esc(', '.join(entry.get('failure_modes') or []) or '-')}</td>"
            "</tr>"
        )
    header = "<tr><th>Record</th><th>Category</th><th>Tool events</th><th>Result</th><th>Failure modes</th></tr>"
    return f"<table>{header}{''.join(rows)}</table>"


def _failure_sections(summary: dict[str, Any]) -> str:
    failures = summary.get("failures") or []
    if not isinstance(failures, list) or not failures:
        return "<p>No scored failures &mdash; every claim matched the recorded tool log.</p>"
    parts = []
    for entry in failures:
        if not isinstance(entry, dict):
            continue
        modes = ", ".join(entry.get("failure_modes") or []) or "-"
        # Redacted summaries drop "rationale"; render the record without it.
        rationale = entry.get("rationale")
        rationale_html = (
            f'<p class="rationale">{_esc(rationale)}</p>'
            if isinstance(rationale, str) and rationale.strip()
            else "<p>Rationale withheld from this report.</p>"
        )
        parts.append(
            '<div class="record">'
            f"<h3>{_esc(entry.get('record_id', 'unknown'))}</h3>"
            "<ul>"
            f"<li>Category: <code>{_esc(entry.get('category', 'unknown'))}</code></li>"
            f"<li>Risk area: <code>{_esc(entry.get('risk_area', 'unspecified'))}</code></li>"
            f"<li>Failure modes: <code>{_esc(modes)}</code></li>"
            f"<li>Recorded tool events: {_esc(entry.get('tool_event_count', 0))}</li>"
            "</ul>"
            f"{rationale_html}"
            "</div>"
        )
    return "".join(parts)


def render_trace_html(summary: dict[str, Any]) -> str:
    """Render a trace-gate summary as a standalone, self-contained HTML report."""

    redacted = summary.get("content_disclosure") == "redacted"

    body = [_verdict_block(summary)]
    if redacted:
        body.append(
            '<div class="banner"><strong>Aggregate-only report.</strong> This summary was '
            "redacted before rendering: record identifiers, agent output, and per-record "
            "rationale are not included. Counts and failure modes only.</div>"
        )
    body.append("<h2>Scope</h2>")
    body.append(_scope_list(summary, redacted=redacted))
    body.append("<h2>Failure modes</h2>")
    body.append(_failure_mode_table(summary))
    if not redacted:
        body.append("<h2>Scored records</h2>")
        body.append(_record_table(summary))
        body.append("<h2>Failing records</h2>")
        body.append(
            "<p>Each rationale quotes the claim the agent made and the recorded tool evidence "
            "that contradicts it. Quoted text is agent output, reproduced as recorded.</p>"
        )
        body.append(_failure_sections(summary))
    body.append(
        "<footer>Deterministic structural scoring of a saved trace. No model calls, no network "
        "access, no credentials, and no external actions: the gate reads only the trace supplied "
        "to it, and the same trace always produces the same report.</footer>"
    )

    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        '<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>Agent trace gate evidence report</title>"
        f"<style>{_HTML_STYLE}</style></head>\n"
        f"<body><main>\n{chr(10).join(body)}\n</main></body>\n"
        "</html>\n"
    )
