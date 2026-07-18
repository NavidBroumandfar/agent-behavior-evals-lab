"""Assemble frontier strong-judge verdicts into the judge-with-log raw format.

The frontier judge (Claude Opus 4.8) runs as subagents rather than through the
``opencode`` CLI, so its verdicts arrive as subagent transcripts instead of a
harness-written JSONL. This module extracts the verdict lines and writes them
into the same ``traces/external/judge_with_log_*.local.jsonl`` shape the CLI
judges use, so a single aggregator scores every judge identically.

Blindness note, for the record: the frontier judge received rendered prompts
containing only the fields listed in the protocol's "Inputs" section, written
to a scratch directory outside the repository, and was instructed to read
nothing else. That is instruction-enforced blindness, the same standard (and
the same limitation) the blind red-team protocol already discloses.

Batching note: each frontier agent held ~14 records in one context, whereas
each CLI judge saw exactly one record per context. That is a mild information
advantage for the frontier judge and is disclosed in the report rather than
corrected for.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterator

from judge_with_log_experiment import raw_path
from repo_config import REPO_ROOT

FRONTIER_MODEL = "frontier/claude-opus-4-8"
RAW_DIR = REPO_ROOT / "traces/external"
VERDICT_RE = re.compile(r'\{\s*"record_id".*?\}', re.S)
VALID_VERDICTS = {"supported", "unsupported"}


def message_texts(path: Path) -> Iterator[str]:
    """Yield every assistant text block in a subagent transcript."""

    with path.open("r", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            content = (obj.get("message") or obj).get("content")
            if isinstance(content, str):
                yield content
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and isinstance(block.get("text"), str):
                        yield block["text"]


def extract_verdicts(path: Path) -> list[dict[str, Any]]:
    """First verdict wins per record; later restatements are ignored."""

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for text in message_texts(path):
        for candidate in VERDICT_RE.findall(text):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            record_id = parsed.get("record_id")
            verdict = parsed.get("verdict")
            if record_id and verdict in VALID_VERDICTS and record_id not in seen:
                seen.add(record_id)
                rows.append(
                    {
                        "record_id": record_id,
                        "model": FRONTIER_MODEL,
                        "verdict": verdict,
                        "confidence": parsed.get("confidence"),
                        "reason": str(parsed.get("reason", ""))[:400],
                    }
                )
    return rows


def assemble(transcripts: list[Path], run: int, model: str = FRONTIER_MODEL) -> Path:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in transcripts:
        for row in extract_verdicts(path):
            if row["record_id"] in seen:
                raise ValueError(f"duplicate record across slices: {row['record_id']}")
            seen.add(row["record_id"])
            rows.append({**row, "model": model, "run": run, "attempts": 1})

    rows.sort(key=lambda r: r["record_id"])
    # Single source of truth for the filename, so the aggregator always finds it.
    out_path = raw_path(model, run)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=int, required=True)
    parser.add_argument("--model", default=FRONTIER_MODEL,
                        help="logical judge id; picks the raw filename")
    parser.add_argument("--transcripts", nargs="+", required=True)
    args = parser.parse_args(argv)

    paths = [Path(p) for p in args.transcripts]
    out_path = assemble(paths, args.run, args.model)
    count = sum(1 for _ in out_path.open())
    print(f"wrote {out_path} ({count} verdicts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
